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
	Returns (active_in, elapsed_seconds) for the timer display.

	elapsed_seconds = sum of completed IN→OUT pairs from today midnight only.
	The frontend is responsible for adding (now − active_in) as the live tick.

	For cross-midnight sessions (active IN before midnight):
	  elapsed_seconds = 0  (frontend ticks from active_in which is before midnight)

	Returns:
	    active_in       – datetime of the current open IN, or None
	    elapsed_seconds – completed pairs accumulated today (does NOT include live)
	"""
	today_midnight = get_datetime(today() + " 00:00:00")

	# resolve the currently active IN (cross-midnight aware)
	active_in, _ = resolve_active_session(employee)

	# cross-midnight: IN was before today's midnight
	# elapsed = 0; frontend ticks from active_in directly
	if active_in and active_in < today_midnight:
		return active_in, 0

	# get all logs from midnight today
	logs = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", today_midnight]},
		fields=["log_type", "time"],
		order_by="time asc",
	)
	elapsed    = 0
	current_in = None
	for log in logs:
		if log.log_type == "IN":
			current_in = log.time
		elif log.log_type == "OUT" and current_in:
			elapsed   += max(0, int((log.time - current_in).total_seconds()))
			current_in = None

	return current_in, elapsed


def process_attendance_from_checkin(employee, out_time):
	"""
	Called after an OUT log is inserted.
	Walks back through the last 23 h 59 m to find the matching open IN log,
	then calls process_attendance() with force_absent=False.

	Attendance date = date of the IN log (cross-midnight sessions belong to
	the check-in date, not the check-out date).
	"""
	since = out_time - timedelta(hours=23, minutes=59)
	logs  = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee,
		         "time":     [">=", since],
		         "time":     ["<=", out_time]},
		fields=["log_type", "time"],
		order_by="time asc",
	)
	active_in = None
	for log in logs:
		if log.log_type == "IN":
			active_in = log.time
		elif log.log_type == "OUT" and active_in:
			if log.time == out_time:
				break          # this is the OUT we just inserted
			active_in = None   # closed by a prior OUT

	if not active_in:
		return  # no open IN found — nothing to process

	process_attendance(employee, active_in.date(), active_in, out_time, force_absent=False)


def process_attendance(employee, attendance_date, in_time, out_time, force_absent=False):
	"""
	Create or update (cancel → amend) the Attendance record for one session.

	Rules:
	  force_absent=True  → always Absent  (used for auto-checkout sessions)
	  working_hours >= PRESENT_THRESHOLD_HOURS → Present
	  working_hours <  PRESENT_THRESHOLD_HOURS → Absent

	Returns the saved Attendance document.
	"""
	working_hours = round((out_time - in_time).total_seconds() / 3600, 2)
	status  = "Absent" if force_absent or working_hours < PRESENT_THRESHOLD_HOURS else "Present"
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
			att = frappe.get_doc("Attendance", existing.name)  # reload after cancel
		att.status        = status
		att.in_time       = in_time
		att.out_time      = out_time
		att.working_hours = working_hours
		att.flags.ignore_permissions = True
		att.save(ignore_permissions=True)
		att.flags.ignore_permissions = True
		att.submit()
	else:
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


def auto_checkout_and_mark_absent():
	"""
	Scheduled hourly job.
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
		        AND co.time <= ci.time + INTERVAL 23*60+59 MINUTE
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
