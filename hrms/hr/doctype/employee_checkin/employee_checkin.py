# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime, today

from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from hrms.hr.utils import (
	get_distance_between_coordinates,
	set_geolocation_from_coordinates,
	validate_active_employee,
)

# ── Attendance constants ───────────────────────────────────────────────────────
PRESENT_THRESHOLD_HOURS = 9.5        # 9 hrs 30 min → Present
MAX_SESSION_HOURS       = 23 + 59/60 # 23 h 59 m max session window


class CheckinRadiusExceededError(frappe.ValidationError):
	pass


class EmployeeCheckin(Document):
	def before_validate(self):
		self.time = get_datetime(self.time).replace(microsecond=0)

	def validate(self):
		validate_active_employee(self.employee)
		self.validate_duplicate_log()
		self.validate_time_change()
		self.fetch_shift()
		# Auto-checkout and Attendance Regularization logs are created server-side without GPS; do not enforce geolocation.
		if self.device_id not in ("Auto Checkout", "Attendance Regularization"):
			self.set_geolocation()
			self.validate_distance_from_shift_location()

	def validate_duplicate_log(self):
		doc = frappe.db.exists(
			"Employee Checkin",
			{
				"employee": self.employee,
				"time": self.time,
				"name": ("!=", self.name),
				"log_type": self.log_type,
			},
		)
		if doc:
			doc_link = frappe.get_desk_link("Employee Checkin", doc)
			frappe.throw(
				_("This employee already has a log with the same timestamp.{0}").format("<Br>" + doc_link)
			)

	def validate_time_change(self):
		if self.attendance and self.has_value_changed("time"):
			frappe.throw(
				title=_("Cannot Modify Time"),
				msg=_(
					"An attendance record is linked to this checkin. Please cancel the attendance before modifying time."
				),
			)

	@frappe.whitelist()
	def set_geolocation(self):
		set_geolocation_from_coordinates(self)

	@frappe.whitelist()
	def fetch_shift(self):
		if not (
			shift_actual_timings := get_actual_start_end_datetime_of_shift(
				self.employee, get_datetime(self.time), True
			)
		):
			self.shift = None
			self.offshift = 1
			return

		if (
			shift_actual_timings.shift_type.determine_check_in_and_check_out
			== "Strictly based on Log Type in Employee Checkin"
			and not self.log_type
			and not self.skip_auto_attendance
		):
			frappe.throw(
				_("Log Type is required for check-ins falling in the shift: {0}.").format(
					shift_actual_timings.shift_type.name
				)
			)
		if not self.attendance:
			self.offshift = 0
			self.shift = shift_actual_timings.shift_type.name
			self.shift_actual_start = shift_actual_timings.actual_start
			self.shift_actual_end = shift_actual_timings.actual_end
			self.shift_start = shift_actual_timings.start_datetime
			self.shift_end = shift_actual_timings.end_datetime
			self.overtime_type = shift_actual_timings.overtime_type or None

	def after_insert(self):
		"""
		Fires for every Employee Checkin insert from ANY source:
		Frappe HR PWA, VGTS dashboard, REST API, biometric device, etc.

		On OUT log → resolve matching IN → calculate hours → mark attendance.
		  ≥ 9 h 30 m  → Present
		  < 9 h 30 m  → Absent
		Attendance date = date of the IN log (handles cross-midnight sessions).
		Auto-checkout logs are skipped to avoid recursion.
		"""
		if self.device_id == "Auto Checkout":
			return
		if self.log_type == "OUT":
			process_attendance_from_checkin(self.employee, get_datetime(self.time))

	def validate_distance_from_shift_location(self):
		if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
			return

		if not (self.latitude or self.longitude):
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		assignment_locations = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"shift_type": self.shift,
				"start_date": ["<=", self.time],
				"shift_location": ["is", "set"],
				"docstatus": 1,
				"status": "Active",
			},
			or_filters=[["end_date", ">=", self.time], ["end_date", "is", "not set"]],
			pluck="shift_location",
		)
		if not assignment_locations:
			return

		checkin_radius, latitude, longitude = frappe.db.get_value(
			"Shift Location", assignment_locations[0], ["checkin_radius", "latitude", "longitude"]
		)
		if checkin_radius <= 0:
			return

		distance = get_distance_between_coordinates(latitude, longitude, self.latitude, self.longitude)
		if distance > checkin_radius:
			frappe.throw(
				_("You must be within {0} meters of your shift location to check in.").format(checkin_radius),
				exc=CheckinRadiusExceededError,
			)


@frappe.whitelist()
def add_log_based_on_employee_field(
	employee_field_value,
	timestamp,
	device_id=None,
	log_type=None,
	skip_auto_attendance=0,
	employee_fieldname="attendance_device_id",
	latitude=None,
	longitude=None,
):
	"""Finds the relevant Employee using the employee field value and creates a Employee Checkin.

	:param employee_field_value: The value to look for in employee field.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id: (optional)Location / Device ID. A short string is expected.
	:param log_type: (optional)Direction of the Punch if available (IN/OUT).
	:param skip_auto_attendance: (optional)Skip auto attendance field will be set for this log(0/1).
	:param employee_fieldname: (Default: attendance_device_id)Name of the field in Employee DocType based on which employee lookup will happen.
	:latitude: (optional) Latitude of the shift location.
	:longitude: (optional) Longitude of the shift location.
	"""

	if not employee_field_value or not timestamp:
		frappe.throw(_("'employee_field_value' and 'timestamp' are required."))

	employee = frappe.db.get_values(
		"Employee",
		{employee_fieldname: employee_field_value},
		["name", "employee_name", employee_fieldname],
		as_dict=True,
	)
	if employee:
		employee = employee[0]
	else:
		frappe.throw(
			_("No Employee found for the given employee field value. '{}': {}").format(
				employee_fieldname, employee_field_value
			)
		)

	doc = frappe.new_doc("Employee Checkin")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	doc.latitude = latitude
	doc.longitude = longitude
	if cint(skip_auto_attendance) == 1:
		doc.skip_auto_attendance = "1"
	doc.insert()

	return doc


@frappe.whitelist()
def bulk_fetch_shift(checkins: list[str] | str) -> None:
	if isinstance(checkins, str):
		checkins = frappe.json.loads(checkins)
	for d in checkins:
		doc = frappe.get_doc("Employee Checkin", d)
		doc.fetch_shift()
		doc.flags.ignore_validate = True
		doc.save()


# ══════════════════════════════════════════════════════════════════════════════
# VGTS Attendance Logic — shared by HRMS & VGTS dashboard
# ══════════════════════════════════════════════════════════════════════════════

def resolve_active_session(employee):
	"""
	Look back MAX_SESSION_HOURS (23 h 59 m) and return the currently open session.

	Pairs IN/OUT logs chronologically. If an IN has no following OUT it is
	the active session.  Fully cross-midnight aware.

	Returns:
	    (active_in_time, elapsed_seconds)
	    active_in_time  – datetime of the open IN log, or None if not checked in
	    elapsed_seconds – seconds already accumulated in completed IN→OUT pairs
	                      within the same look-back window
	"""
	since = now_datetime() - timedelta(hours=23, minutes=59)
	logs  = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", since]},
		fields=["log_type", "time"],
		order_by="time asc",
	)
	active_in = None
	elapsed   = 0
	for log in logs:
		if log.log_type == "IN":
			active_in = log.time
		elif log.log_type == "OUT" and active_in:
			elapsed  += max(0, int((log.time - active_in).total_seconds()))
			active_in = None
	return active_in, elapsed


def get_today_checkin_seconds(employee):
	"""
	Returns (active_in, elapsed_seconds, first_in) for the timer display.

	elapsed_seconds = sum of completed IN→OUT pairs from today midnight only.
	The frontend is responsible for adding (now − active_in) as the live tick.

	For cross-midnight sessions (active IN before midnight):
	  elapsed_seconds = 0  (frontend ticks from active_in which is before midnight)

	Returns:
	    active_in       – datetime of the current open IN, or None
	    elapsed_seconds – completed pairs accumulated today (does NOT include live)
	    first_in        – datetime of the very first IN log today, or active_in for
	                      cross-midnight sessions (used to display "since HH:MM")
	"""
	today_midnight = get_datetime(today() + " 00:00:00")

	# resolve the currently active IN (cross-midnight aware)
	active_in, _ = resolve_active_session(employee)

	# cross-midnight: IN was before today's midnight
	# elapsed = 0; frontend ticks from active_in directly
	if active_in and active_in < today_midnight:
		return active_in, 0, active_in

	# get all logs from midnight today
	logs = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", today_midnight]},
		fields=["log_type", "time"],
		order_by="time asc",
	)
	elapsed    = 0
	current_in = None
	first_in   = None
	for log in logs:
		if log.log_type == "IN":
			if first_in is None:
				first_in = log.time   # first IN of the day
			current_in = log.time
		elif log.log_type == "OUT" and current_in:
			elapsed   += max(0, int((log.time - current_in).total_seconds()))
			current_in = None

	return current_in, elapsed, first_in


def process_attendance_from_checkin(employee, out_time):
	"""
	Called after an OUT log is inserted.
	Walks back through the last 23 h 59 m to find all IN/OUT pairs, then
	calls process_attendance() using the FIRST check-in of the day as in_time
	and the current OUT as out_time so that working_hours = gross time
	(first check-in → last check-out), matching what is displayed in the
	Monthly Attendance Sheet.

	Attendance date = date of the first IN log (cross-midnight sessions belong
	to the check-in date, not the check-out date).
	"""
	since = out_time - timedelta(hours=23, minutes=59)
	logs  = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee,
		         "time":     ["between", [since, out_time]]},
		fields=["log_type", "time"],
		order_by="time asc",
	)
	first_in  = None   # very first IN of the day/session window
	active_in = None   # current open IN (tracks whether a session is open)
	for log in logs:
		if log.log_type == "IN":
			if first_in is None:
				first_in = log.time   # record the earliest IN only once
			active_in = log.time
		elif log.log_type == "OUT" and active_in:
			if log.time == out_time:
				break          # this is the OUT we just inserted
			active_in = None   # closed by a prior OUT

	if not active_in:
		return  # no open IN found — nothing to process

	# Use first_in so working_hours = last_out − first_in (gross time).
	# This ensures an employee who was in from 09:41 to 20:05 (with breaks)
	# is correctly evaluated against the 9 h 30 m Present threshold.
	process_attendance(employee, first_in.date(), first_in, out_time, force_absent=False)


def _has_wfh_approval(employee, attendance_date):
	"""Returns True if the employee has an approved Work From Home leave on attendance_date."""
	return bool(frappe.db.exists("Leave Application", {
		"employee":   employee,
		"leave_type": ["in", ["Work From Home", "WFH"]],
		"docstatus":  1,
		"from_date":  ["<=", attendance_date],
		"to_date":    [">=", attendance_date],
	}))


def _has_od_approval(employee, attendance_date):
	"""Returns True if the employee has an approved On Duty attendance request on attendance_date."""
	return bool(frappe.db.exists("Attendance Request", {
		"employee":   employee,
		"reason":     ["in", ["On Duty", "OD"]],
		"docstatus":  1,
		"from_date":  ["<=", attendance_date],
		"to_date":    [">=", attendance_date],
	}))


def process_attendance(employee, attendance_date, in_time, out_time, force_absent=False):
	"""
	Create or update (cancel → amend) the Attendance record for one session.

	Status priority (evaluated top to bottom):
	  1. Approved WFH leave for this date  → Work From Home
	  2. Approved OD request for this date  → On Duty
	  3. force_absent = True (auto-checkout) → Absent
	  4. Normal check-in + check-out        → Present  (no hour threshold)

	Returns the saved Attendance document.
	"""
	working_hours = round((out_time - in_time).total_seconds() / 3600, 2)

	if _has_wfh_approval(employee, attendance_date):
		status = "Work From Home"
	elif _has_od_approval(employee, attendance_date):
		status = "On Duty"
	elif force_absent:
		status = "Absent"
	else:
		# Any valid check-in + check-out = Present regardless of hours worked
		status = "Present"

	company = frappe.db.get_value("Employee", employee, "company")

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date, "docstatus": ["!=", 2]},
		["name", "docstatus"],
		as_dict=True,
	)

	if existing:
		att = frappe.get_doc("Attendance", existing.name)
		if att.docstatus == 1:
			att.flags.ignore_permissions = True
			att.cancel()
			# Cancelled doc (docstatus=2) cannot be edited — create a new one
			existing = None
		elif att.docstatus == 0:
			# Draft — update in place
			att.status        = status
			att.in_time       = in_time
			att.out_time      = out_time
			att.working_hours = working_hours
			att.flags.ignore_permissions = True
			att.save(ignore_permissions=True)
			att.flags.ignore_permissions = True
			att.submit()

	if not existing:
		att = frappe.new_doc("Attendance")
		att.employee        = employee
		att.attendance_date = attendance_date
		att.status          = status
		att.in_time         = in_time
		att.out_time        = out_time
		att.working_hours   = working_hours
		att.company         = company
		att.flags.ignore_permissions = True
		att.insert(ignore_permissions=True)
		att.flags.ignore_permissions = True
		att.submit()

	return att


@frappe.whitelist()
def auto_checkout_and_mark_absent():
	"""
	Scheduled hourly job (also callable via API).
	Finds every employee whose last open IN log is ≥ 23 h 59 m old (no OUT
	within the window), creates an OUT log at IN + 23:59, and marks Absent.
	"""
	cutoff = now_datetime() - timedelta(hours=23, minutes=59)

	open_ins = frappe.db.sql("""
		SELECT ci.name, ci.employee, ci.time
		FROM `tabEmployee Checkin` ci
		WHERE ci.log_type = 'IN'
		  AND ci.time    <= %s
		  AND NOT EXISTS (
		      SELECT 1 FROM `tabEmployee Checkin` co
		      WHERE co.employee = ci.employee
		        AND co.log_type = 'OUT'
		        AND co.time > ci.time
		        AND co.time <= ci.time + INTERVAL 1439 MINUTE
		  )
	""", (cutoff,), as_dict=True)

	for row in open_ins:
		auto_out = row.time + timedelta(hours=23, minutes=59)

		out_doc = frappe.new_doc("Employee Checkin")
		out_doc.employee  = row.employee
		out_doc.log_type  = "OUT"
		out_doc.time      = auto_out
		out_doc.device_id = "Auto Checkout"
		out_doc.insert(ignore_permissions=True)

		# force_absent=True — auto-checkout always marks Absent regardless of hours
		process_attendance(row.employee, row.time.date(), row.time, auto_out, force_absent=True)

	if open_ins:
		frappe.db.commit()


def on_attendance_request_submit(doc, method=None):
	"""
	Doc event: Attendance Request → on_submit.
	When an attendance regularization is approved, recalculate attendance.
	If corrected working hours ≥ 9 h 30 m → Present, else Absent.
	"""
	if not doc.employee:
		return

	in_time  = doc.get("checkin_time") or doc.get("in_time")  or doc.get("from_date")
	out_time = doc.get("checkout_time") or doc.get("out_time") or doc.get("to_date")

	if not in_time or not out_time:
		return

	in_dt  = get_datetime(in_time)
	out_dt = get_datetime(out_time)

	process_attendance(doc.employee, in_dt.date(), in_dt, out_dt, force_absent=False)
	frappe.db.commit()


# ══════════════════════════════════════════════════════════════════════════════

def mark_attendance_and_link_log(
	logs,
	attendance_status,
	attendance_date,
	working_hours=None,
	late_entry=False,
	early_exit=False,
	in_time=None,
	out_time=None,
	shift=None,
	overtime_type=None,
):
	"""Creates an attendance and links the attendance to the Employee Checkin.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Checkin'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	log_names = [x.name for x in logs]
	employee = logs[0].employee

	if attendance_status == "Skip":
		skip_attendance_in_checkins(log_names)
		return None

	if attendance_status not in ("Present", "Absent", "Half Day"):
		frappe.throw(_("{0} is an invalid Attendance Status.").format(attendance_status))

	try:
		frappe.db.savepoint("attendance_creation")

		attendance = create_or_update_attendance(
			employee=employee,
			attendance_date=attendance_date,
			attendance_status=attendance_status,
			working_hours=working_hours,
			shift=shift,
			late_entry=late_entry,
			early_exit=early_exit,
			in_time=in_time,
			out_time=out_time,
			overtime_type=overtime_type,
		)

		if attendance_status == "Absent":
			attendance.add_comment(
				text=_("Employee was marked Absent for not meeting the working hours threshold.")
			)

		update_attendance_in_checkins(log_names, attendance.name)
		return attendance

	except frappe.ValidationError as e:
		handle_attendance_exception(log_names, e)
		return None


def create_or_update_attendance(
	employee,
	attendance_date,
	attendance_status,
	working_hours=None,
	shift=None,
	late_entry=False,
	early_exit=False,
	in_time=None,
	out_time=None,
	overtime_type=None,
):
	"""Creates a new attendance or updates an existing half-day attendance."""
	if attendance := get_existing_half_day_attendance(employee, attendance_date):
		frappe.db.set_value(
			"Attendance",
			attendance.name,
			{
				"working_hours": working_hours,
				"shift": shift,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"in_time": in_time,
				"out_time": out_time,
				"half_day_status": "Absent" if attendance_status == "Absent" else "Present",
				"modify_half_day_status": 0,
			},
		)
		return frappe.get_doc("Attendance", attendance.name)
	else:
		attendance = frappe.new_doc("Attendance")
		attendance.update(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": attendance_date,
				"status": attendance_status,
				"working_hours": working_hours,
				"shift": shift,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"in_time": in_time,
				"out_time": out_time,
			}
		)

		# Set overtime data if applicable
		if overtime_type and attendance_status == "Present":
			overtime_data = get_overtime_data(shift, working_hours)
			if overtime_data:
				attendance.update(
					{
						"overtime_type": overtime_type,
						"standard_working_hours": overtime_data.get("standard_working_hours"),
						"actual_overtime_duration": overtime_data.get("actual_overtime_duration"),
					}
				)
		attendance.flags.ignore_permissions = True
		attendance.save()
		attendance.flags.ignore_permissions = True
		attendance.submit()

	return attendance


def get_overtime_data(shift_name, working_hours):
	overtime_data = {}

	shift_type_details = frappe.db.get_value(
		doctype="Shift Type",
		filters={"name": shift_name},
		fieldname=["allow_overtime", "start_time", "end_time"],
		as_dict=True,
	)

	if not shift_type_details or not shift_type_details.allow_overtime:
		return overtime_data

	standard_working_hours = calculate_time_difference(
		shift_type_details.start_time, shift_type_details.end_time
	)

	if working_hours > standard_working_hours:
		actual_overtime_duration = working_hours - standard_working_hours
		overtime_data = {
			"standard_working_hours": standard_working_hours,
			"actual_overtime_duration": actual_overtime_duration,
		}

	return overtime_data


def get_existing_half_day_attendance(employee, attendance_date):
	attendance_name = frappe.db.exists(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": attendance_date,
			"status": "Half Day",
			"modify_half_day_status": 1,
			"leave_type": ("is", "set"),
		},
	)

	if attendance_name:
		attendance_doc = frappe.get_doc("Attendance", attendance_name)
		return attendance_doc
	return None


def calculate_working_hours(logs, check_in_out_type, working_hours_calc_type):
	"""Given a set of logs in chronological order calculates the total working hours based on the parameters.
	Zero is returned for all invalid cases.

	:param logs: The List of 'Employee Checkin'.
	:param check_in_out_type: One of: 'Alternating entries as IN and OUT during the same shift', 'Strictly based on Log Type in Employee Checkin'
	:param working_hours_calc_type: One of: 'First Check-in and Last Check-out', 'Every Valid Check-in and Check-out'
	"""
	total_hours = 0
	in_time = out_time = None
	if check_in_out_type == "Alternating entries as IN and OUT during the same shift":
		in_time = logs[0].time
		if len(logs) >= 2:
			out_time = logs[-1].time
		if working_hours_calc_type == "First Check-in and Last Check-out":
			# assumption in this case: First log always taken as IN, Last log always taken as OUT
			total_hours = time_diff_in_hours(in_time, logs[-1].time)
		elif working_hours_calc_type == "Every Valid Check-in and Check-out":
			logs = logs[:]
			while len(logs) >= 2:
				total_hours += time_diff_in_hours(logs[0].time, logs[1].time)
				del logs[:2]

	elif check_in_out_type == "Strictly based on Log Type in Employee Checkin":
		if working_hours_calc_type == "First Check-in and Last Check-out":
			first_in_log_index = find_index_in_dict(logs, "log_type", "IN")
			first_in_log = logs[first_in_log_index] if first_in_log_index or first_in_log_index == 0 else None
			last_out_log_index = find_index_in_dict(reversed(logs), "log_type", "OUT")
			last_out_log = (
				logs[len(logs) - 1 - last_out_log_index]
				if last_out_log_index or last_out_log_index == 0
				else None
			)
			in_time = getattr(first_in_log, "time", None)
			out_time = getattr(last_out_log, "time", None)
			if first_in_log and last_out_log:
				total_hours = time_diff_in_hours(in_time, out_time)
		elif working_hours_calc_type == "Every Valid Check-in and Check-out":
			in_log = out_log = None
			for log in logs:
				if in_log and out_log:
					if not in_time:
						in_time = in_log.time
					out_time = out_log.time
					total_hours += time_diff_in_hours(in_log.time, out_log.time)
					in_log = out_log = None
				if not in_log:
					in_log = log if log.log_type == "IN" else None
					if in_log and not in_time:
						in_time = in_log.time
				elif not out_log:
					out_log = log if log.log_type == "OUT" else None

			if in_log and out_log:
				out_time = out_log.time
				total_hours += time_diff_in_hours(in_log.time, out_log.time)

	return total_hours, in_time, out_time


def time_diff_in_hours(start, end):
	return round(float((end - start).total_seconds()) / 3600, 2)


def find_index_in_dict(dict_list, key, value):
	return next((index for (index, d) in enumerate(dict_list) if d[key] == value), None)


def handle_attendance_exception(log_names: list, error_message: str):
	frappe.db.rollback(save_point="attendance_creation")
	frappe.clear_messages()
	skip_attendance_in_checkins(log_names)
	add_comment_in_checkins(log_names, error_message)


def add_comment_in_checkins(log_names: list, error_message: str):
	text = "{prefix}<br>{error_message}".format(
		prefix=frappe.bold(_("Reason for skipping auto attendance:")), error_message=error_message
	)

	for name in log_names:
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Employee Checkin",
				"reference_name": name,
				"content": text,
			}
		).insert(ignore_permissions=True)


def skip_attendance_in_checkins(log_names: list):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("skip_auto_attendance", 1)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()


def update_attendance_in_checkins(log_names: list, attendance_id: str):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("attendance", attendance_id)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()


def calculate_time_difference(start_time, end_time):
	if end_time < start_time:
		end_time += timedelta(days=1)
	time_difference = abs(start_time - end_time)

	return round(time_difference.total_seconds() / 3600, 2)


# ══════════════════════════════════════════════════════════════════════════════
# Batch attendance processing — called by the MCP and schedulers
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def process_monthly_attendance(month, year, company=""):
	"""
	Batch-process attendance for all active employees for a given month/year.

	Rules applied per employee per past working day (Mon–Fri, non-holiday):
	  1. Approved WFH leave          → Work From Home (WFH)
	  2. Approved OD request         → On Duty (OD)
	  3. Both IN and OUT check-ins   → Present (P)
	  4. Only IN (no OUT)            → auto-checkout at 23:59:59 + Absent (A)
	  5. No check-ins at all         → Absent (A)

	Called by the MCP via:
	    POST /api/method/hrms.hr.doctype.employee_checkin.employee_checkin.process_monthly_attendance
	    body: {"month": 4, "year": 2026, "company": ""}
	"""
	from datetime import date

	month = frappe.utils.cint(month)
	year  = frappe.utils.cint(year)
	today = date.today()

	first_day = date(year, month, 1)
	last_day  = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
	month_start = str(first_day)
	month_end   = str(last_day)

	# ── 1. Holiday dates ──────────────────────────────────────────────────────
	holiday_dates = set(frappe.db.sql_list("""
		SELECT DATE_FORMAT(holiday_date, %s)
		FROM `tabHoliday`
		WHERE parent IN (SELECT name FROM `tabHoliday List` WHERE disabled = 0)
		  AND holiday_date BETWEEN %s AND %s
	""", ("%%Y-%%m-%%d", month_start, month_end)))

	past_working_days = [
		d for d in (first_day + timedelta(n) for n in range((last_day - first_day).days + 1))
		if d.weekday() < 5 and str(d) not in holiday_dates and d < today
	]
	all_working_days = [
		d for d in (first_day + timedelta(n) for n in range((last_day - first_day).days + 1))
		if d.weekday() < 5 and str(d) not in holiday_dates
	]

	# ── 2. Active employees ───────────────────────────────────────────────────
	emp_filters = {"status": "Active"}
	if company:
		emp_filters["company"] = company

	employees = frappe.db.get_all(
		"Employee",
		filters=emp_filters,
		fields=["name", "employee_name", "company", "department"],
		limit=0,
	)

	# ── 3. Check-in logs for the month ────────────────────────────────────────
	raw_checkins = frappe.db.get_all(
		"Employee Checkin",
		filters={"time": ["between", [f"{month_start} 00:00:00", f"{month_end} 23:59:59"]]},
		fields=["employee", "log_type", "time"],
		order_by="time asc",
		limit=0,
	)

	checkin_map = {}  # [emp_id][day_str] = {"IN": first_in_log, "OUT": last_out_log}
	for ci in raw_checkins:
		emp_id   = ci["employee"]
		day_str  = str(ci["time"])[:10]
		log_type = ci.get("log_type") or ""
		if log_type not in ("IN", "OUT"):
			continue
		checkin_map.setdefault(emp_id, {}).setdefault(day_str, {})
		prev = checkin_map[emp_id][day_str].get(log_type)
		if prev is None:
			checkin_map[emp_id][day_str][log_type] = ci
		elif log_type == "IN"  and ci["time"] < prev["time"]:
			checkin_map[emp_id][day_str]["IN"]  = ci   # keep earliest IN
		elif log_type == "OUT" and ci["time"] > prev["time"]:
			checkin_map[emp_id][day_str]["OUT"] = ci   # keep latest OUT

	# ── 4. Approved WFH leaves for the month ─────────────────────────────────
	wfh_map = {}   # wfh_map[emp_id] = set of date strings
	for app in frappe.db.get_all(
		"Leave Application",
		filters={
			"leave_type": ["in", ["Work From Home", "WFH"]],
			"docstatus":  1,
			"from_date":  ["<=", month_end],
			"to_date":    [">=", month_start],
		},
		fields=["employee", "from_date", "to_date"],
		limit=0,
	):
		cur = get_datetime(str(app["from_date"])).date()
		end = get_datetime(str(app["to_date"])).date()
		while cur <= end:
			wfh_map.setdefault(app["employee"], set()).add(str(cur))
			cur += timedelta(days=1)

	# ── 5. Existing attendance for the month ──────────────────────────────────
	att_filters = {"attendance_date": ["between", [month_start, month_end]]}
	if company:
		att_filters["company"] = company

	att_map = {}
	for a in frappe.db.get_all(
		"Attendance",
		filters=att_filters,
		fields=["name", "employee", "attendance_date", "status", "docstatus"],
		limit=0,
	):
		att_map[(a["employee"], str(a["attendance_date"])[:10])] = a

	# ── 5a. Approved OD attendance requests for the month ─────────────────────
	od_map = {}  # od_map[emp_id] = set of date strings
	for req in frappe.db.get_all(
		"Attendance Request",
		filters={
			"reason":    ["in", ["On Duty", "OD"]],
			"docstatus": 1,
			"from_date": ["<=", month_end],
			"to_date":   [">=", month_start],
		},
		fields=["employee", "from_date", "to_date"],
		limit=0,
	):
		cur = get_datetime(str(req["from_date"])).date()
		end = get_datetime(str(req["to_date"])).date()
		while cur <= end:
			od_map.setdefault(req["employee"], set()).add(str(cur))
			cur += timedelta(days=1)

	# ── 6. Process each employee for each past working day ────────────────────
	auto_checkouts = []
	processed      = []
	skipped        = []
	errors         = []

	for emp in employees:
		emp_id = emp["name"]
		emp_co = emp.get("company") or company

		for d in past_working_days:
			day_str      = str(d)
			day_logs     = checkin_map.get(emp_id, {}).get(day_str, {})
			has_in       = "IN"  in day_logs
			has_out      = "OUT" in day_logs
			existing_att = att_map.get((emp_id, day_str))
			is_wfh       = day_str in wfh_map.get(emp_id, set())
			is_od        = day_str in od_map.get(emp_id, set())

			# Determine the correct status
			if is_wfh:
				correct_status = "Work From Home"
			elif is_od:
				correct_status = "On Duty"
			elif has_in and has_out:
				correct_status = "Present"
			else:
				correct_status = "Absent"

			# Already correct — skip
			if existing_att and existing_att["status"] == correct_status:
				continue

			# Auto-checkout: IN without OUT (only for non-WFH absent case)
			if correct_status == "Absent" and has_in and not has_out:
				auto_out_time = f"{day_str} 23:59:59"
				try:
					out_doc           = frappe.new_doc("Employee Checkin")
					out_doc.employee  = emp_id
					out_doc.log_type  = "OUT"
					out_doc.time      = get_datetime(auto_out_time)
					out_doc.device_id = "Auto Checkout"
					out_doc.insert(ignore_permissions=True)
					checkout_note = "created"
				except Exception as exc:
					checkout_note = f"failed: {str(exc)[:80]}"
				auto_checkouts.append({
					"employee":      emp_id,
					"employee_name": emp.get("employee_name"),
					"date":          day_str,
					"auto_out_time": auto_out_time,
					"note":          checkout_note,
				})

			# Build payload fields
			in_time  = str(day_logs["IN"]["time"])  if has_in  else None
			out_time = str(day_logs["OUT"]["time"]) if has_out else None

			try:
				if existing_att:
					if existing_att.get("docstatus") == 1:
						# Cancel submitted record first
						att_doc = frappe.get_doc("Attendance", existing_att["name"])
						att_doc.flags.ignore_permissions = True
						att_doc.cancel()
						existing_att = None
					elif existing_att.get("docstatus") == 0:
						# Update draft in place and submit
						updates = {"status": correct_status}
						if in_time:
							updates["in_time"] = in_time
						if out_time:
							updates["out_time"] = out_time
						frappe.db.set_value("Attendance", existing_att["name"], updates)
						att_doc = frappe.get_doc("Attendance", existing_att["name"])
						att_doc.flags.ignore_permissions = True
						att_doc.submit()
						att_map[(emp_id, day_str)]["status"] = correct_status
						processed.append({
							"employee":      emp_id,
							"employee_name": emp.get("employee_name"),
							"date":          day_str,
							"action":        f"updated_to_{correct_status.lower().replace(' ', '_')}",
						})
						continue

				# Create new record (after cancel or when none existed)
				att_doc = frappe.new_doc("Attendance")
				att_doc.employee        = emp_id
				att_doc.attendance_date = day_str
				att_doc.status          = correct_status
				att_doc.company         = emp_co
				if in_time:
					att_doc.in_time = in_time
				if out_time:
					att_doc.out_time = out_time
				att_doc.flags.ignore_permissions = True
				att_doc.insert(ignore_permissions=True)
				att_doc.flags.ignore_permissions = True
				att_doc.submit()

				att_map[(emp_id, day_str)] = {
					"name":            att_doc.name,
					"employee":        emp_id,
					"attendance_date": day_str,
					"status":          correct_status,
					"docstatus":       1,
				}
				processed.append({
					"employee":      emp_id,
					"employee_name": emp.get("employee_name"),
					"date":          day_str,
					"action":        f"created_{correct_status.lower().replace(' ', '_')}",
				})

			except Exception as exc:
				errors.append({"employee": emp_id, "date": day_str, "error": str(exc)[:200]})

	frappe.db.commit()

	# ── 7. Build the attendance grid ──────────────────────────────────────────
	STATUS_ABBR = {
		"Present":        "P",
		"Absent":         "A",
		"Half Day":       "HD",
		"Work From Home": "WFH",
		"On Leave":       "L",
		"Holiday":        "H",
		"Weekly Off":     "WO",
	}

	sheet_rows = []
	for emp in employees:
		emp_id = emp["name"]
		row    = {
			"employee":      emp_id,
			"employee_name": emp.get("employee_name", ""),
			"department":    emp.get("department", ""),
		}
		total_present = total_absent = total_wfh = 0
		total_od = 0

		for d in all_working_days:
			day_str = str(d)
			rec     = att_map.get((emp_id, day_str))

			if d >= today:
				abbr = "-"
			elif rec:
				abbr = STATUS_ABBR.get(rec["status"], rec["status"][:1])
			else:
				abbr = "A"

			row[str(d.day)] = abbr
			if   abbr == "P":   total_present += 1
			elif abbr == "A":   total_absent  += 1
			elif abbr == "WFH": total_wfh     += 1
			elif abbr == "OD":  total_od      += 1

		row["total_present"] = total_present
		row["total_absent"]  = total_absent
		row["total_wfh"]     = total_wfh
		row["total_od"]      = total_od
		sheet_rows.append(row)

	return {
		"monthly_attendance_sheet": {
			"month":   month,
			"year":    year,
			"company": company or "All",
			"columns": (
				["employee", "employee_name", "department"]
				+ [str(d.day) for d in all_working_days]
				+ ["total_present", "total_absent", "total_wfh", "total_od"]
			),
			"rows": sheet_rows,
		},
		"processing_summary": {
			"total_employees":   len(employees),
			"past_working_days": len(past_working_days),
			"processed_count":   len(processed),
			"processed":         processed,
			"auto_checkouts":    auto_checkouts,
			"skipped":           skipped,
			"errors":            errors,
		},
	}


@frappe.whitelist()
def fix_employee_attendance(employee, attendance_date):
	"""
	Fix attendance for a single employee on a specific date.

	Checks WFH approval and check-in/out records, then creates or corrects
	the Attendance record:
	  - WFH approved          → Work From Home
	  - OD approved           → On Duty
	  - IN + OUT logs exist   → Present
	  - Otherwise             → returns skipped (no change)

	Called by the MCP via:
	    POST /api/method/hrms.hr.doctype.employee_checkin.employee_checkin.fix_employee_attendance
	    body: {"employee": "HR-EMP-0057", "attendance_date": "2026-04-24"}
	"""
	wfh_approved = _has_wfh_approval(employee, attendance_date)
	od_approved = _has_od_approval(employee, attendance_date)

	# Fetch check-in logs
	checkins = frappe.db.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time":     ["between", [
				f"{attendance_date} 00:00:00",
				f"{attendance_date} 23:59:59",
			]],
		},
		fields=["log_type", "time"],
		order_by="time asc",
		limit=0,
	)
	in_logs  = [c for c in checkins if c.get("log_type") == "IN"]
	out_logs = [c for c in checkins if c.get("log_type") == "OUT"]

	first_in  = in_logs[0]["time"]  if in_logs  else None
	last_out  = out_logs[-1]["time"] if out_logs else None

	working_hours = None
	if first_in and last_out:
		working_hours = round(
			(get_datetime(str(last_out)) - get_datetime(str(first_in))).total_seconds() / 3600, 2
		)

	# Determine correct status
	if wfh_approved:
		correct_status = "Work From Home"
	elif od_approved:
		correct_status = "On Duty"
	elif first_in and last_out:
		correct_status = "Present"
	else:
		return {
			"status":   "skipped",
			"employee": employee,
			"date":     attendance_date,
			"message":  "No WFH approval and no complete check-in/out found",
			"wfh":      bool(wfh_approved),
			"in_logs":  len(in_logs),
			"out_logs": len(out_logs),
		}

	# Fetch existing attendance
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date, "docstatus": ["!=", 2]},
		["name", "status", "docstatus"],
		as_dict=True,
	)

	if existing and existing.get("status") == correct_status:
		return {
			"status":         "already_correct",
			"employee":       employee,
			"date":           attendance_date,
			"current_status": existing["status"],
			"message":        f"Attendance is already {correct_status}",
		}

	company  = frappe.db.get_value("Employee", employee, "company")
	old_name = existing["name"] if existing else None

	# Cancel existing submitted record
	if existing and existing.get("docstatus") == 1:
		att_doc = frappe.get_doc("Attendance", existing["name"])
		att_doc.flags.ignore_permissions = True
		att_doc.cancel()

	# Create corrected record
	att_doc = frappe.new_doc("Attendance")
	att_doc.employee        = employee
	att_doc.attendance_date = attendance_date
	att_doc.status          = correct_status
	att_doc.company         = company
	if first_in:
		att_doc.in_time = first_in
	if last_out:
		att_doc.out_time = last_out
	if working_hours is not None:
		att_doc.working_hours = working_hours
	att_doc.flags.ignore_permissions = True
	att_doc.insert(ignore_permissions=True)
	att_doc.flags.ignore_permissions = True
	att_doc.submit()

	frappe.db.commit()

	return {
		"status":         "fixed",
		"employee":       employee,
		"date":           attendance_date,
		"old_attendance": old_name,
		"new_attendance": att_doc.name,
		"new_status":     correct_status,
		"wfh_approved":   bool(wfh_approved),
		"first_in":       str(first_in)  if first_in  else None,
		"last_out":       str(last_out)  if last_out  else None,
		"working_hours":  working_hours,
	}


@frappe.whitelist()
def fix_wfh_od_attendance(from_date, to_date, company=""):
	"""
	Scan all approved WFH leave applications and approved OD attendance requests
	within the date range and correct existing attendance records accordingly.

	Priority:
	  1. Approved WFH leave (Leave Application, leave_type="Work From Home", docstatus=1)
	     → status = "Work From Home"
	  2. Approved OD (Attendance Request, reason="On Duty", docstatus=1)
	     → status = "On Duty"

	Cancels any wrong submitted attendance and creates the corrected one.

	Called by the MCP via:
	    POST /api/method/hrms.hr.doctype.employee_checkin.employee_checkin.fix_wfh_od_attendance
	    body: {"from_date": "2026-04-01", "to_date": "2026-04-30", "company": ""}
	"""
	# ── 1. Approved WFH leaves ────────────────────────────────────────────────
	wfh_map = {}  # {(employee, date_str): "Work From Home"}
	wfh_filters = {
		"leave_type": ["in", ["Work From Home", "WFH"]],
		"docstatus":  1,
		"from_date":  ["<=", to_date],
		"to_date":    [">=", from_date],
	}
	if company:
		wfh_filters["company"] = company

	for app in frappe.db.get_all(
		"Leave Application",
		filters=wfh_filters,
		fields=["employee", "from_date", "to_date"],
		limit=0,
	):
		cur = get_datetime(str(app["from_date"])).date()
		end = get_datetime(str(app["to_date"])).date()
		while cur <= end:
			d_str = str(cur)
			if from_date <= d_str <= to_date:
				wfh_map[(app["employee"], d_str)] = "Work From Home"
			cur += timedelta(days=1)

	# ── 2. Approved OD attendance requests ────────────────────────────────────
	od_map = {}   # {(employee, date_str): "On Duty"}
	od_filters = {
		"reason":    ["in", ["On Duty", "OD"]],
		"docstatus": 1,
		"from_date": ["<=", to_date],
		"to_date":   [">=", from_date],
	}
	if company:
		od_filters["company"] = company

	for req in frappe.db.get_all(
		"Attendance Request",
		filters=od_filters,
		fields=["employee", "from_date", "to_date"],
		limit=0,
	):
		cur = get_datetime(str(req["from_date"])).date()
		end = get_datetime(str(req["to_date"])).date()
		while cur <= end:
			d_str = str(cur)
			if from_date <= d_str <= to_date:
				# WFH takes priority — only add OD if no WFH on this day
				if (req["employee"], d_str) not in wfh_map:
					od_map[(req["employee"], d_str)] = "On Duty"
			cur += timedelta(days=1)

	# Merge: WFH priority already enforced above
	all_corrections = {**od_map, **wfh_map}

	processed = []
	skipped   = []
	errors    = []

	for (emp_id, day_str), correct_status in all_corrections.items():
		try:
			existing = frappe.db.get_value(
				"Attendance",
				{"employee": emp_id, "attendance_date": day_str, "docstatus": ["!=", 2]},
				["name", "status", "docstatus"],
				as_dict=True,
			)

			if existing and existing["status"] == correct_status:
				skipped.append({
					"employee": emp_id,
					"date":     day_str,
					"status":   correct_status,
					"note":     "already_correct",
				})
				continue

			company_name = company or frappe.db.get_value("Employee", emp_id, "company")
			old_name     = existing["name"] if existing else None
			old_status   = existing["status"] if existing else None

			if existing and existing["docstatus"] == 1:
				att_doc = frappe.get_doc("Attendance", existing["name"])
				att_doc.flags.ignore_permissions = True
				att_doc.cancel()
			elif existing and existing["docstatus"] == 0:
				frappe.db.set_value("Attendance", existing["name"], "status", correct_status)
				att_doc = frappe.get_doc("Attendance", existing["name"])
				att_doc.flags.ignore_permissions = True
				att_doc.submit()
				processed.append({
					"employee":       emp_id,
					"date":           day_str,
					"old_status":     old_status,
					"new_status":     correct_status,
					"old_attendance": old_name,
					"new_attendance": old_name,
					"action":         "updated_draft",
				})
				continue

			att_doc                 = frappe.new_doc("Attendance")
			att_doc.employee        = emp_id
			att_doc.attendance_date = day_str
			att_doc.status          = correct_status
			att_doc.company         = company_name
			att_doc.flags.ignore_permissions = True
			att_doc.insert(ignore_permissions=True)
			att_doc.flags.ignore_permissions = True
			att_doc.submit()

			processed.append({
				"employee":       emp_id,
				"date":           day_str,
				"old_status":     old_status,
				"new_status":     correct_status,
				"old_attendance": old_name,
				"new_attendance": att_doc.name,
				"action":         "cancelled_and_recreated" if old_name else "created",
			})

		except Exception as exc:
			errors.append({"employee": emp_id, "date": day_str, "error": str(exc)[:200]})

	frappe.db.commit()

	return {
		"from_date":       from_date,
		"to_date":         to_date,
		"total_wfh_days":  len(wfh_map),
		"total_od_days":   len(od_map),
		"processed_count": len(processed),
		"skipped_count":   len(skipped),
		"error_count":     len(errors),
		"processed":       processed,
		"skipped":         skipped,
		"errors":          errors,
	}
