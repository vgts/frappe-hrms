# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from calendar import monthrange
from datetime import date
from itertools import groupby

from pypika import Field
from pypika.terms import Criterion

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Extract, Sum
from frappe.utils import cint, cstr, formatdate, getdate
from frappe.utils.nestedset import get_descendants_of

from hrms.utils import date_diff, get_date_range

Filters = frappe._dict

status_map = {
	"Present": "P",
	"Absent": "A",
	# For half-day we intentionally don't show `HD/*` in the report anymore.
	# Output format now becomes either `P/<leave_or_permission>` or `<leave_or_permission>/P`.
	"Half Day/Other Half Absent": "P/<type>",
	"Half Day/Other Half Present": "<type>/P",
	"Work From Home": "WFH",
	"On Duty": "OD",
	"On Leave": "L",
	"Holiday": "H",
	"Weekly Off": "W",
}

LEAVE_SHORT_CODES = {
	"Monthly Off": "MO",
	"Leave Without Pay": "LWP",
}

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def execute(filters: Filters | None = None) -> tuple:
	filters = frappe._dict(filters or {})

	if not filters.filter_based_on:
		frappe.throw(_("Please select Filter Based On"))

	if filters.filter_based_on == "Month" and not (filters.month and filters.year):
		frappe.throw(_("Please select month and year."))

	if filters.filter_based_on == "Date Range":
		if not (filters.start_date and filters.end_date):
			frappe.throw(_("Please set the date range."))
		if getdate(filters.start_date) > getdate(filters.end_date):
			frappe.throw(_("Start date cannot be greater than end date."))
		if date_diff(filters.end_date, filters.start_date) > 90:
			frappe.throw(_("Please set a date range less than 90 days."))

	if not filters.company:
		frappe.throw(_("Please select company."))

	if filters.company:
		filters.companies = [filters.company]
		if filters.include_company_descendants:
			filters.companies.extend(get_descendants_of("Company", filters.company))

	attendance_map, leave_type_map = get_attendance_map(filters)

	# Pending Leave Applications (WFH, On Leave, etc.) + pending Attendance Requests (WFH, On Duty)
	pending_leave_map = get_pending_leave_applications(filters)
	for key, val in get_pending_attendance_requests(filters).items():
		# Leave Application entry takes priority; only fill gaps
		if key not in pending_leave_map:
			pending_leave_map[key] = val
	# Approved Attendance Requests should also reflect in sheet display
	approved_request_map = get_approved_attendance_requests(filters)

	columns = get_columns(filters)
	data = get_data(filters, attendance_map, leave_type_map, pending_leave_map, approved_request_map)

	if not data:
		frappe.msgprint(_("No employees found for this criteria."), alert=True, indicator="orange")
		return columns, [], None, None

	message = get_message() if not filters.summarized_view else ""
	chart = get_chart_data(attendance_map, filters)

	return columns, data, message, chart


def get_message() -> str:
	message = ""
	colors = [
		"green",
		"red",
		"orange",
		"#914EE3",
		"green",
		"#2563EB",
		"#3187D8",
		"#878787",
		"#878787",
	]

	count = 0
	for status, abbr in status_map.items():
		message += f"""
			<span style='border-left: 2px solid {colors[count]}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{_(status)} - {abbr}
			</span>
		"""
		count += 1

	# Extra legend for leave short codes and permission
	extra_legends = [
		("Monthly Off", "MO", "#F59E0B"),
		("Leave Without Pay", "LWP", "#EF4444"),
		("Half Day + Leave (Other half absent)", "P/<type>", "#914EE3"),
		("Half Day + Leave (Other half present)", "<type>/P", "#914EE3"),
		("Half Day + Permission (Other half absent)", "P/<n>PM", "#06B6D4"),
		("Half Day + Permission (Other half present)", "<n>PM/P", "#06B6D4"),
		("Present + Permission", "P/&lt;n&gt;PM", "#06B6D4"),
		("WFH + Permission (second half)", "WFH/&lt;n&gt;PM", "#06B6D4"),
		("WFH + Permission (first half)", "&lt;n&gt;PM/WFH", "#06B6D4"),
		("WFH + Leave (second half)", "WFH/&lt;type&gt;", "#10B981"),
		("WFH + Leave (first half)", "&lt;type&gt;/WFH", "#10B981"),
	]
	for status, abbr, color in extra_legends:
		message += f"""
			<span style='border-left: 2px solid {color}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{_(status)} - {abbr}
			</span>
		"""

	return message


def get_columns(filters: Filters) -> list[dict]:
	columns = []

	if filters.group_by:
		options_mapping = {
			"Branch": "Branch",
			"Grade": "Employee Grade",
			"Department": "Department",
			"Designation": "Designation",
		}
		options = options_mapping.get(filters.group_by)
		columns.append(
			{
				"label": _(filters.group_by),
				"fieldname": frappe.scrub(filters.group_by),
				"fieldtype": "Link",
				"options": options,
				"width": 120,
			}
		)

	columns.extend(
		[
			{
				"label": _("Employee"),
				"fieldname": "employee",
				"fieldtype": "Link",
				"options": "Employee",
				"width": 135,
			},
			{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 120},
		]
	)

	if filters.summarized_view:
		columns.extend(
			[
				{
					"label": _("Total Present"),
					"fieldname": "total_present",
					"fieldtype": "Float",
					"width": 110,
				},
				{"label": _("Total Leaves"), "fieldname": "total_leaves", "fieldtype": "Float", "width": 110},
				{"label": _("Total Absent"), "fieldname": "total_absent", "fieldtype": "Float", "width": 110},
				{
					"label": _("Total Holidays"),
					"fieldname": "total_holidays",
					"fieldtype": "Float",
					"width": 120,
				},
				{
					"label": _("Unmarked Days"),
					"fieldname": "unmarked_days",
					"fieldtype": "Float",
					"width": 130,
				},
			]
		)
		columns.extend(get_columns_for_leave_types())
		columns.extend(
			[
				{
					"label": _("Total Late Entries"),
					"fieldname": "total_late_entries",
					"fieldtype": "Float",
					"width": 140,
				},
				{
					"label": _("Total Early Exits"),
					"fieldname": "total_early_exits",
					"fieldtype": "Float",
					"width": 140,
				},
			]
		)
	else:
		columns.append({"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 120})
		columns.extend(get_columns_for_days(filters))

	return columns


def get_columns_for_leave_types() -> list[dict]:
	leave_types = frappe.db.get_all("Leave Type", pluck="name")
	types = []
	for entry in leave_types:
		types.append({"label": entry, "fieldname": frappe.scrub(entry), "fieldtype": "Float", "width": 120})

	return types


def get_columns_for_days(filters: Filters) -> list[dict]:
	days = []
	dates_in_period = get_dates_in_period(filters)
	for d in dates_in_period:
		d = getdate(d)
		# gets abbr from weekday number
		abbr_weekday = day_abbr[d.weekday()]
		# sets days as 1 Mon, 2 Tue, 3 Wed
		label = f"{d.day} {abbr_weekday}"
		days.append({"label": label, "fieldtype": "Data", "fieldname": d.strftime("%d-%m-%Y"), "width": 65})

	return days


def get_dates_in_period(filters: Filters) -> list[str]:
	dates_in_period = []
	if filters.filter_based_on == "Month":
		total_days = get_total_days_in_month(filters)
		# forms the datelist from selected year and month from filters
		dates_in_period = [
			f"{cstr(filters.year)}-{cstr(filters.month)}-{cstr(day)}" for day in range(1, total_days + 1)
		]
	if filters.filter_based_on == "Date Range":
		dates_in_period = get_date_range(filters.start_date, filters.end_date)

	return dates_in_period


def get_total_days_in_month(filters: Filters) -> int:
	return monthrange(cint(filters.year), cint(filters.month))[1]


def get_date_condition(docfield: Field, filters: Filters) -> Criterion:
	if filters.filter_based_on == "Month":
		return (Extract("month", docfield) == filters.month) & (Extract("year", docfield) == filters.year)
	if filters.filter_based_on == "Date Range":
		return (docfield >= filters.start_date) & (docfield <= filters.end_date)


def get_data(
	filters: Filters,
	attendance_map: dict,
	leave_type_map: dict = None,
	pending_leave_map: dict = None,
	approved_request_map: dict = None,
	half_day_leave_map: dict = None,
) -> list[dict]:
	employee_details, group_by_param_values = get_employee_related_details(filters)
	holiday_map = get_holiday_map(filters)
	permission_map = get_permission_map(filters)
	checkin_map = get_checkin_map(filters)
	data = []

	if filters.group_by:
		group_by_column = frappe.scrub(filters.group_by)

		for value in group_by_param_values:
			if not value:
				continue

			records = get_rows(employee_details[value], filters, holiday_map, attendance_map,
			                   leave_type_map, permission_map, checkin_map, pending_leave_map, approved_request_map, half_day_leave_map)

			if records:
				data.append({group_by_column: value})
				data.extend(records)

	else:
		data = get_rows(
			employee_details,
			filters,
			holiday_map,
			attendance_map,
			leave_type_map,
			permission_map,
			checkin_map,
			pending_leave_map,
			approved_request_map,
			half_day_leave_map,
		)

	return data


def get_attendance_map(filters: Filters) -> dict:
	"""Returns a dictionary of employee wise attendance map as per shifts for all the days of the month like
	{
	    'employee1': {
	            'Morning Shift': {1: 'Present', 2: 'Absent', ...}
	            'Evening Shift': {1: 'Absent', 2: 'Present', ...}
	    },
	    'employee2': {
	            'Afternoon Shift': {1: 'Present', 2: 'Absent', ...}
	            'Night Shift': {1: 'Absent', 2: 'Absent', ...}
	    },
	    'employee3': {
	            None: {1: 'On Leave'}
	    }
	}
	"""
	attendance_list = get_attendance_records(filters)
	attendance_map = {}
	leave_map = {}
	leave_type_map = {}  # (employee, date) → leave_type

	for d in attendance_list:
		if d.get("leave_type"):
			leave_type_map[(d.employee, d.attendance_date)] = d.leave_type

		if d.status == "On Leave":
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.attendance_date)
			continue

		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		attendance_map[d.employee][d.shift][d.attendance_date] = d.status

	# leave is applicable for the entire day so all shifts should show the leave entry

	for employee, leave_days in leave_map.items():
		for assigned_shift, dates in leave_days.items():
			# no attendance records exist except leaves
			if employee not in attendance_map:
				attendance_map.setdefault(employee, {}).setdefault(assigned_shift or "", {})

			for d in dates:
				for shift in attendance_map[employee].keys():
					attendance_map[employee][shift][d] = "On Leave"

	# Merge blank-shift records into named shifts to avoid duplicate rows.
	# This happens when some attendance records are saved without a shift assignment
	# while the same employee also has records with a named shift.
	for employee in list(attendance_map.keys()):
		shifts = list(attendance_map[employee].keys())
		named_shifts = [s for s in shifts if s]  # non-empty shift names

		if "" in shifts and named_shifts:
			empty_data = attendance_map[employee].pop("")
			for d, status in empty_data.items():
				for shift in named_shifts:
					# only fill in days that are not already recorded under a named shift
					if d not in attendance_map[employee][shift]:
						attendance_map[employee][shift][d] = status

	return attendance_map, leave_type_map


def get_attendance_records(filters: Filters) -> list[dict]:
	Attendance = frappe.qb.DocType("Attendance")
	attendance_date_condition = get_date_condition(Attendance.attendance_date, filters)
	status = (
		frappe.qb.terms.Case()
		.when(
			((Attendance.status == "Half Day") & (Attendance.half_day_status == "Present")),
			"Half Day/Other Half Present",
		)
		.when(
			((Attendance.status == "Half Day") & (Attendance.half_day_status == "Absent")),
			"Half Day/Other Half Absent",
		)
		.else_(Attendance.status)
	)
	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Attendance.attendance_date,
			(status).as_("status"),
			Attendance.shift,
			Attendance.leave_type,
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.company.isin(filters.companies))
			& (attendance_date_condition)
		)
	)

	if filters.employee:
		query = query.where(Attendance.employee == filters.employee)
	query = query.orderby(Attendance.employee, Attendance.attendance_date)

	return query.run(as_dict=1)


def get_employee_related_details(filters: Filters) -> tuple[dict, list]:
	"""Returns
	1. nested dict for employee details
	2. list of values for the group by filter
	"""
	Employee = frappe.qb.DocType("Employee")

	joining_date_condition = get_date_condition(Employee.date_of_joining, filters)

	query = (
		frappe.qb.from_(Employee)
		.select(
			Employee.name,
			Employee.employee_name,
			Employee.designation,
			Employee.grade,
			Employee.department,
			Employee.branch,
			Employee.company,
			Employee.holiday_list,
			(Employee.date_of_joining).as_("joined_date"),
			Case()
			.when(
				joining_date_condition,
				1,
			)
			.else_(0)
			.as_("joined_in_current_period"),
		)
		.where(Employee.company.isin(filters.companies))
	)

	# Exclude employees who left before the report period starts.
	# Active employees always appear; Left employees only appear if their
	# relieving_date falls on or after the period start (they were still
	# employed for at least part of the period).
	if filters.filter_based_on == "Date Range":
		period_start = getdate(filters.start_date)
	else:
		from calendar import monthrange as _monthrange
		period_start = date(cint(filters.year), cint(filters.month), 1)

	query = query.where(
		(Employee.status == "Active")
		| (Employee.relieving_date >= period_start)
	)

	if filters.employee:
		query = query.where(Employee.name == filters.employee)

	group_by = filters.group_by
	if group_by:
		group_by = group_by.lower()
		query = query.orderby(group_by)

	employee_details = query.run(as_dict=True)

	group_by_param_values = []
	emp_map = {}

	if group_by:
		group_key = lambda d: "" if d[group_by] is None else d[group_by]  # noqa
		for parameter, employees in groupby(sorted(employee_details, key=group_key), key=group_key):
			group_by_param_values.append(parameter)
			emp_map.setdefault(parameter, frappe._dict())

			for emp in employees:
				emp_map[parameter][emp.name] = emp
	else:
		for emp in employee_details:
			emp_map[emp.name] = emp

	return emp_map, group_by_param_values


def get_holiday_map(filters: Filters) -> dict[str, list[dict]]:
	"""
	Returns a dict of holidays falling in the filter period with holiday list name as key.
	Fetched in a single query for efficiency and reliability.
	Also stores a combined "__all__" key merging all lists (used as fallback).
	"""
	Holiday = frappe.qb.DocType("Holiday")
	holiday_condition = get_date_condition(Holiday.holiday_date, filters)

	all_rows = (
		frappe.qb.from_(Holiday)
		.select(Holiday.parent, Holiday.holiday_date, Holiday.weekly_off)
		.where(holiday_condition)
	).run(as_dict=True)

	holiday_map = frappe._dict()
	for row in all_rows:
		holiday_map.setdefault(row.parent, []).append(
			{"holiday_date": row.holiday_date, "weekly_off": row.weekly_off}
		)

	# Build a merged fallback list (deduped by date) for employees with no holiday list
	seen = set()
	merged = []
	for h_list in holiday_map.values():
		for h in h_list:
			if h["holiday_date"] not in seen:
				seen.add(h["holiday_date"])
				merged.append(h)
	holiday_map["__all__"] = merged

	return holiday_map


def get_checkin_map(filters: Filters) -> dict:
	"""Returns employee → {'in_time': 'HH:MM', 'completed': bool} for today only.
	completed=True when first IN to last OUT spans >= 9 hours 30 minutes."""
	today = date.today()
	dates = get_dates_in_period(filters)
	if not any(getdate(d) == today for d in dates):
		return {}

	try:
		ci_list = frappe.db.get_all(
			"Employee Checkin",
			filters={
				"time": ["between", [
					str(today) + " 00:00:00",
					str(today) + " 23:59:59",
				]],
			},
			fields=["employee", "log_type", "time"],
			order_by="time asc",
		)

		emp_checkins = {}
		for ci in ci_list:
			emp_checkins.setdefault(ci.employee, {"in": [], "out": []})
			if ci.log_type == "IN":
				emp_checkins[ci.employee]["in"].append(ci.time)
			elif ci.log_type == "OUT":
				emp_checkins[ci.employee]["out"].append(ci.time)

		result = {}
		for emp, times in emp_checkins.items():
			if not times["in"]:
				continue

			first_in = times["in"][0]
			in_time_str = str(first_in)[-8:][:5]

			completed = False
			if times["out"]:
				from datetime import datetime as _dt
				last_out = times["out"][-1]
				in_dt = first_in if hasattr(first_in, "hour") else _dt.strptime(str(first_in), "%Y-%m-%d %H:%M:%S")
				out_dt = last_out if hasattr(last_out, "hour") else _dt.strptime(str(last_out), "%Y-%m-%d %H:%M:%S")
				if (out_dt - in_dt).total_seconds() >= 9.5 * 3600:
					completed = True

			result[emp] = {"in_time": in_time_str, "completed": completed}

		return result
	except Exception:
		return {}


def get_permission_map(filters: Filters) -> dict:
	"""Returns a dict of (employee, date) → {from_time, to_time} for approved permissions."""
	perm_map = {}
	try:
		EmployeePermission = frappe.qb.DocType("Employee Permission")
		date_condition = get_date_condition(EmployeePermission.permission_date, filters)
		perms = (
			frappe.qb.from_(EmployeePermission)
			.select(
				EmployeePermission.employee,
				EmployeePermission.permission_date,
				EmployeePermission.from_time,
				EmployeePermission.to_time,
			)
			.where(
				(EmployeePermission.docstatus == 1)
				& (date_condition)
			)
		).run(as_dict=True)
		for p in perms:
			perm_map[(p.employee, p.permission_date)] = {
				"from_time": p.from_time,
				"to_time": p.to_time,
			}
	except Exception:
		pass
	return perm_map


def get_pending_leave_applications(filters: Filters) -> dict:
	"""
	Build a map for draft/open leave applications so Monthly Attendance Sheet can show
	leave codes immediately (before Leave Application is approved / Attendance is created).

	Returns:
	    {(employee, attendance_date): {"status": <MonthlySheetStatus>, "leave_type": <Leave Type>}}
	"""
	if not filters.company:
		return {}

	# Determine report window
	if filters.filter_based_on == "Month":
		start_date = date(cint(filters.year), cint(filters.month), 1)
		end_date = date(cint(filters.year), cint(filters.month), get_total_days_in_month(filters))
	else:
		start_date = getdate(filters.start_date)
		end_date = getdate(filters.end_date)

	LeaveApplication = frappe.qb.DocType("Leave Application")

	try:
		pending_rows = (
			frappe.qb.from_(LeaveApplication)
			.select(
				LeaveApplication.employee,
				LeaveApplication.leave_type,
				LeaveApplication.from_date,
				LeaveApplication.to_date,
				LeaveApplication.half_day,
				LeaveApplication.half_day_date,
				LeaveApplication.custom_first_half,
				LeaveApplication.custom_second_half,
			)
			.where(
				(LeaveApplication.company.isin(filters.companies))
				& (LeaveApplication.status == "Open")
				& (LeaveApplication.docstatus == 0)
				& (LeaveApplication.from_date <= end_date)
				& (LeaveApplication.to_date >= start_date)
			)
		).run(as_dict=True)
	except Exception:
		# If custom half-day session fields are not present in DB yet,
		# do not block the report entirely.
		return {}

	pending_leave_map = {}

	for la in pending_rows:
		employee = la.get("employee")
		leave_type = la.get("leave_type") or ""
		if not employee or not la.get("from_date") or not la.get("to_date"):
			continue

		# Only iterate the overlap with the report window
		overlap_start = max(getdate(la.from_date), start_date)
		overlap_end = min(getdate(la.to_date), end_date)
		if overlap_start > overlap_end:
			continue

		half_day = cint(la.get("half_day"))
		half_day_date = getdate(la.get("half_day_date")) if la.get("half_day_date") else None
		is_second_half = bool(cint(la.get("custom_second_half")))

		for d_str in get_date_range(str(overlap_start), str(overlap_end)):
			d = getdate(d_str)

			if half_day and half_day_date and getdate(d) == half_day_date:
				# Match Monthly Attendance Sheet expected status mapping
				status_label = (
					"Half Day/Other Half Absent" if is_second_half else "Half Day/Other Half Present"
				)
			elif leave_type == "Work From Home":
				# WFH leave applied (even before approval) → show WFH
				status_label = "Work From Home"
			else:
				status_label = "On Leave"

			pending_leave_map[(employee, d)] = {"status": status_label, "leave_type": leave_type}

	return pending_leave_map


def get_pending_attendance_requests(filters: Filters) -> dict:
	"""
	Build a map for pending (Open, before approval) Attendance Requests so the
	Monthly Attendance Sheet shows WFH / OD immediately after the employee applies,
	without waiting for manager approval.

	reason = "Work From Home" → status "Work From Home" → displays WFH
	reason = "On Duty"        → status "On Duty"        → displays OD

	Returns:
	    {(employee, date): {"status": <MonthlySheetStatus>, "leave_type": ""}}
	"""
	if not filters.company:
		return {}

	if filters.filter_based_on == "Month":
		start_date = date(cint(filters.year), cint(filters.month), 1)
		end_date   = date(cint(filters.year), cint(filters.month), get_total_days_in_month(filters))
	else:
		start_date = getdate(filters.start_date)
		end_date   = getdate(filters.end_date)

	AttendanceRequest = frappe.qb.DocType("Attendance Request")

	try:
		pending_rows = (
			frappe.qb.from_(AttendanceRequest)
			.select(
				AttendanceRequest.employee,
				AttendanceRequest.from_date,
				AttendanceRequest.to_date,
				AttendanceRequest.reason,
			)
			.where(
				(AttendanceRequest.company.isin(filters.companies))
				& (AttendanceRequest.status == "Open")
				& (AttendanceRequest.docstatus == 0)
				& (AttendanceRequest.from_date <= end_date)
				& (AttendanceRequest.to_date >= start_date)
			)
		).run(as_dict=True)
	except Exception:
		return {}

	REASON_STATUS = {
		"Work From Home": "Work From Home",
		"WFH":            "Work From Home",
		"On Duty":        "On Duty",
		"OD":             "On Duty",
	}

	pending_map = {}
	for ar in pending_rows:
		employee     = ar.get("employee")
		raw_reason = (ar.get("reason") or "").strip()
		status_label = REASON_STATUS.get(raw_reason)
		if not employee or not status_label:
			continue

		overlap_start = max(getdate(ar.from_date), start_date)
		overlap_end   = min(getdate(ar.to_date),   end_date)
		if overlap_start > overlap_end:
			continue

		for d_str in get_date_range(str(overlap_start), str(overlap_end)):
			d = getdate(d_str)
			# Only set if no Leave Application entry already exists for this day
			if (employee, d) not in pending_map:
				pending_map[(employee, d)] = {"status": status_label, "leave_type": ""}

	return pending_map


def get_approved_attendance_requests(filters: Filters) -> dict:
	"""
	Build a map for approved Attendance Requests so Monthly Attendance Sheet can
	display WFH / OD even when Attendance status is limited to standard values.

	Returns:
	    {(employee, date): {"status": "Work From Home" | "On Duty", "leave_type": ""}}
	"""
	if not filters.company:
		return {}

	if filters.filter_based_on == "Month":
		start_date = date(cint(filters.year), cint(filters.month), 1)
		end_date = date(cint(filters.year), cint(filters.month), get_total_days_in_month(filters))
	else:
		start_date = getdate(filters.start_date)
		end_date = getdate(filters.end_date)

	AttendanceRequest = frappe.qb.DocType("Attendance Request")
	try:
		rows = (
			frappe.qb.from_(AttendanceRequest)
			.select(
				AttendanceRequest.employee,
				AttendanceRequest.from_date,
				AttendanceRequest.to_date,
				AttendanceRequest.reason,
			)
			.where(
				(AttendanceRequest.company.isin(filters.companies))
				& (AttendanceRequest.docstatus == 1)
				& (AttendanceRequest.from_date <= end_date)
				& (AttendanceRequest.to_date >= start_date)
				& (AttendanceRequest.reason.isin(["Work From Home", "WFH", "On Duty", "OD"]))
			)
		).run(as_dict=True)
	except Exception:
		return {}

	reason_status = {
		"Work From Home": "Work From Home",
		"WFH": "Work From Home",
		"On Duty": "On Duty",
		"OD": "On Duty",
	}

	out = {}
	for ar in rows:
		employee = ar.get("employee")
		status_label = reason_status.get((ar.get("reason") or "").strip())
		if not employee or not status_label:
			continue

		overlap_start = max(getdate(ar.from_date), start_date)
		overlap_end = min(getdate(ar.to_date), end_date)
		if overlap_start > overlap_end:
			continue

		for d_str in get_date_range(str(overlap_start), str(overlap_end)):
			d = getdate(d_str)
			key = (employee, d)
			# WFH takes precedence over OD if both exist for same day.
			if key not in out or status_label == "Work From Home":
				out[key] = {"status": status_label, "leave_type": ""}

	return out



def get_half_day_leave_map(filters: Filters) -> dict:
	"""Returns {(employee, date): {leave_type, is_second_half}} for approved half-day leaves.
	Used to display WFH/<leave> or <leave>/WFH combos in the attendance sheet."""
	if not filters.company:
		return {}

	if filters.filter_based_on == "Month":
		start_date = date(cint(filters.year), cint(filters.month), 1)
		end_date = date(cint(filters.year), cint(filters.month), get_total_days_in_month(filters))
	else:
		start_date = getdate(filters.start_date)
		end_date = getdate(filters.end_date)

	LeaveApplication = frappe.qb.DocType("Leave Application")
	try:
		rows = (
			frappe.qb.from_(LeaveApplication)
			.select(
				LeaveApplication.employee,
				LeaveApplication.leave_type,
				LeaveApplication.half_day_date,
				LeaveApplication.custom_second_half,
			)
			.where(
				(LeaveApplication.company.isin(filters.companies))
				& (LeaveApplication.docstatus == 1)
				& (LeaveApplication.status == "Approved")
				& (LeaveApplication.half_day == 1)
				& (LeaveApplication.half_day_date >= start_date)
				& (LeaveApplication.half_day_date <= end_date)
			)
		).run(as_dict=True)
	except Exception:
		return {}

	result = {}
	for la in rows:
		if not la.employee or not la.half_day_date:
			continue
		d = getdate(la.half_day_date)
		is_second_half = bool(cint(la.get("custom_second_half")))
		result[(la.employee, d)] = {
			"leave_type": la.leave_type or "",
			"is_second_half": is_second_half,
		}

	return result


def get_rows(employee_details: dict, filters: Filters, holiday_map: dict, attendance_map: dict,
             leave_type_map: dict = None, permission_map: dict = None, checkin_map: dict = None,
             pending_leave_map: dict = None, approved_request_map: dict = None,
             half_day_leave_map: dict = None) -> list[dict]:
	records = []
	default_holiday_list = frappe.get_cached_value("Company", filters.company, "default_holiday_list")
	checkin_map = checkin_map or {}
	today = date.today()
	is_today_in_period = any(getdate(d) == today for d in get_dates_in_period(filters))

	for employee, details in employee_details.items():
		emp_holiday_list = details.holiday_list or default_holiday_list
		holidays = holiday_map.get(emp_holiday_list) or holiday_map.get(default_holiday_list) or holiday_map.get("__all__", [])

		if filters.summarized_view:
			attendance = get_attendance_status_for_summarized_view(
				employee, filters, holidays, details.joined_in_current_period, details.joined_date
			)
			if not attendance:
				continue

			leave_summary = get_leave_summary(employee, filters)
			entry_exits_summary = get_entry_exits_summary(employee, filters)

			row = {"employee": employee, "employee_name": details.employee_name}
			set_defaults_for_summarized_view(filters, row)
			row.update(attendance)
			row.update(leave_summary)
			row.update(entry_exits_summary)

			records.append(row)
		else:
			# Always show all active employees; fall back to empty row if no attendance records yet
			employee_attendance = attendance_map.get(employee) or {"": {}}

			attendance_for_employee = get_attendance_status_for_detailed_view(
				employee,
				filters,
				employee_attendance,
				holidays,
				leave_type_map,
				permission_map,
				checkin_map,
				pending_leave_map,
				approved_request_map,
				details.joined_date,
				half_day_leave_map,
			)
			# set employee details in the first row
			for record in attendance_for_employee:
				record.update({"employee": employee, "employee_name": details.employee_name})

			records.extend(attendance_for_employee)

	return records


def set_defaults_for_summarized_view(filters, row):
	for entry in get_columns(filters):
		if entry.get("fieldtype") == "Float":
			row[entry.get("fieldname")] = 0.0


def get_attendance_status_for_summarized_view(
	employee: str, filters: Filters, holidays: list, joined_in_current_period: int, joined_date: int
) -> dict:
	"""Returns dict of attendance status for employee like
	{'total_present': 1.5, 'total_leaves': 0.5, 'total_absent': 13.5, 'total_holidays': 8, 'unmarked_days': 5}
	"""
	summary, attendance_days = get_attendance_summary_and_days(employee, filters)
	if not any(summary.values()):
		return {}

	total_days = get_dates_in_period(filters)
	total_holidays = total_unmarked_days = 0

	for d in total_days:
		d = getdate(d)
		if d.day in attendance_days or (joined_in_current_period and d < joined_date):
			continue

		status = get_holiday_status(d, holidays)
		if status in ["Weekly Off", "Holiday"]:
			total_holidays += 1
		elif not status:
			total_unmarked_days += 1

	return {
		"total_present": summary.total_present + summary.total_half_days,
		"total_leaves": summary.total_leaves + summary.total_half_days,
		"total_absent": summary.total_absent,
		"total_holidays": total_holidays,
		"unmarked_days": total_unmarked_days,
	}


def get_attendance_summary_and_days(employee: str, filters: Filters) -> tuple[dict, list]:
	Attendance = frappe.qb.DocType("Attendance")

	present_case = (
		frappe.qb.terms.Case()
		.when(
			(
				(Attendance.status == "Present")
				| (Attendance.status == "Work From Home")
				| (Attendance.status == "On Duty")
			),
			1,
		)
		.else_(0)
	)
	sum_present = Sum(present_case).as_("total_present")

	absent_case = frappe.qb.terms.Case().when(Attendance.status == "Absent", 1).else_(0)
	sum_absent = Sum(absent_case).as_("total_absent")

	leave_case = frappe.qb.terms.Case().when(Attendance.status == "On Leave", 1).else_(0)
	sum_leave = Sum(leave_case).as_("total_leaves")

	half_day_case = frappe.qb.terms.Case().when(Attendance.status == "Half Day", 0.5).else_(0)
	sum_half_day = Sum(half_day_case).as_("total_half_days")

	attendance_date_condition = get_date_condition(Attendance.attendance_date, filters)

	summary = (
		frappe.qb.from_(Attendance)
		.select(
			sum_present,
			sum_absent,
			sum_leave,
			sum_half_day,
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.employee == employee)
			& (Attendance.company.isin(filters.companies))
			& (attendance_date_condition)
		)
	).run(as_dict=True)

	days = (
		frappe.qb.from_(Attendance)
		.select(Extract("day", Attendance.attendance_date).as_("day_of_month"))
		.distinct()
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.employee == employee)
			& (Attendance.company.isin(filters.companies))
			& (attendance_date_condition)
		)
	).run(pluck=True)

	return summary[0], days


def _fmt_perm_duration(from_time, to_time):
	"""Format permission duration as hours with PM suffix (PM = Permission).
	e.g. 15:28→16:28 = 1 hour → '1PM'; 15:28→16:58 = 1.5 hrs → '1.5PM'
	"""
	try:
		def to_minutes(t):
			parts = str(t or "").split(":")
			return int(parts[0]) * 60 + int(parts[1])
		diff = to_minutes(to_time) - to_minutes(from_time)
		if diff <= 0:
			return "PM"
		hours = diff / 60
		return f"{int(hours)}PM" if hours == int(hours) else f"{hours:.1f}PM"
	except Exception:
		return "PM"


def _is_second_half_permission(from_time) -> bool:
	"""Returns True if permission starts at or after 13:30 (second half)."""
	try:
		parts = str(from_time or "").split(":")
		total_minutes = int(parts[0]) * 60 + int(parts[1])
		return total_minutes >= 13 * 60 + 30  # 13:30
	except Exception:
		return False


def get_attendance_status_for_detailed_view(
	employee: str, filters: Filters, employee_attendance: dict, holidays: list,
	leave_type_map: dict = None, permission_map: dict = None, checkin_map: dict = None,
	pending_leave_map: dict = None, approved_request_map: dict = None, joined_date=None,
	half_day_leave_map: dict = None,
) -> list[dict]:
	"""Returns list of shift-wise attendance status for employee
	[
	        {'shift': 'Morning Shift', 1: 'A', 2: 'P', 3: 'A'....},
	        {'shift': 'Evening Shift', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = get_dates_in_period(filters)
	attendance_values = []
	leave_type_map = leave_type_map or {}
	permission_map = permission_map or {}
	checkin_map = checkin_map or {}
	pending_leave_map = pending_leave_map or {}
	approved_request_map = approved_request_map or {}
	half_day_leave_map = half_day_leave_map or {}
	today_date = date.today()

	for shift, status_dict in employee_attendance.items():
		row = {"shift": shift}
		for d in total_days:
			d = getdate(d)

			status = status_dict.get(d)

			if status is None and holidays:
				status = get_holiday_status(d, holidays)

			# Sat/Sun: force Weekly Off regardless of any WFH/OD/attendance on that day
			if d.weekday() >= 5:
				status = "Weekly Off"

			# Add pending leave from draft/open Leave Applications.
			# Rules:
			# - Full-day pending leave should only apply when attendance is NOT marked yet.
			# - Half-day pending leave should keep showing leave+P/P+leave even if attendance was later
			#   marked (e.g. employee checked in for the working half).
			pending_leave_type = ""
			pending = pending_leave_map.get((employee, d)) if pending_leave_map else None
			if pending:
				pending_status = pending.get("status")
				pending_leave_type = pending.get("leave_type") or ""

				if status is None:
					status = pending_status
				elif pending_status and pending_status.startswith("Half Day/") and status not in ("Holiday", "Weekly Off"):
					status = pending_status

			# Approved Attendance Requests should be visible in report output.
			approved = approved_request_map.get((employee, d)) if approved_request_map else None
			if approved and status not in ("Holiday", "Weekly Off"):
				status = approved.get("status") or status

			# Resolve abbreviation
			perm = permission_map.get((employee, d))
			if status == "On Leave":
				lt = leave_type_map.get((employee, d), "") or pending_leave_type
				# Prefer showing the actual leave_type code/name.
				# Use MO/LWP for those special types; for others show `leave_type` instead of generic `L`.
				abbr = LEAVE_SHORT_CODES.get(lt, lt or "L")
			elif status in ("Half Day/Other Half Present", "Half Day/Other Half Absent"):
				# We intentionally avoid showing "HD/..." in the sheet.
				# Desired format:
				# - HD/A (Half Day/Other Half Absent): P/<leave_or_permission>
				# - HD/P (Half Day/Other Half Present): <leave_or_permission>/P
				lt = leave_type_map.get((employee, d), "") or pending_leave_type
				lt_abbr = LEAVE_SHORT_CODES.get(lt, lt) if lt else ""

				perm_code = (
					_fmt_perm_duration(perm.get("from_time"), perm.get("to_time")) if perm else ""
				)

				if status == "Half Day/Other Half Absent":
					# Present half, other half absent.
					absent_code = lt_abbr or perm_code or "A"
					abbr = f"P/{absent_code}"
				else:
					# Absent half, other half present.
					absent_code = lt_abbr or perm_code or "A"
					abbr = f"{absent_code}/P"
			elif d == today_date:
				# Today: priority order → Holiday/Weekly Off → WFH → check-in → status → pending
				if status in ("Holiday", "Weekly Off"):
					abbr = status_map.get(status, "")
				elif status in ("Work From Home", "On Duty"):
					# Approved WFH/OD attendance should be shown as-is even if checked in.
					abbr = status_map.get(status, "")
					if abbr == "WFH":
						if perm:
							duration = _fmt_perm_duration(perm.get('from_time'), perm.get('to_time'))
							if _is_second_half_permission(perm.get('from_time')):
								abbr = f"WFH/{duration}"
							else:
								abbr = f"{duration}/WFH"
						else:
							hd = half_day_leave_map.get((employee, d))
							if hd:
								lt_abbr = LEAVE_SHORT_CODES.get(hd.get("leave_type") or "", hd.get("leave_type") or "L")
								abbr = f"WFH/{lt_abbr}" if hd.get("is_second_half") else f"{lt_abbr}/WFH"
				else:
					ci_info = checkin_map.get(employee)
					if ci_info:
						abbr = "P"
					elif status is not None:
						abbr = status_map.get(status, "")
					else:
						abbr = "-"
					# Append permission duration when present + permission exists
					if abbr == "P" and perm:
						duration = _fmt_perm_duration(perm.get('from_time'), perm.get('to_time'))
						abbr = f"P/{duration}"
			elif status is not None:
				abbr = status_map.get(status, "")
				# Present + approved permission → P/<duration>
				if abbr == "P" and perm:
					duration = _fmt_perm_duration(perm.get('from_time'), perm.get('to_time'))
					abbr = f"P/{duration}"
				# WFH + permission → WFH/<duration> (second half) or <duration>/WFH (first half)
				elif abbr == "WFH" and perm:
					duration = _fmt_perm_duration(perm.get('from_time'), perm.get('to_time'))
					if _is_second_half_permission(perm.get('from_time')):
						abbr = f"WFH/{duration}"
					else:
						abbr = f"{duration}/WFH"
				# WFH + half-day leave → WFH/<leave> (second half) or <leave>/WFH (first half)
				elif abbr == "WFH":
					hd = half_day_leave_map.get((employee, d))
					if hd:
						lt_abbr = LEAVE_SHORT_CODES.get(hd.get("leave_type") or "", hd.get("leave_type") or "L")
						abbr = f"WFH/{lt_abbr}" if hd.get("is_second_half") else f"{lt_abbr}/WFH"
			elif d > today_date:
				# Future workday — no attendance yet
				abbr = "-"
			else:
				# Past working day with no submitted attendance and no leave/holiday:
				# show Absent (A). Leave / pending leave / holidays / weekly off stay as above.
				if joined_date and d < getdate(joined_date):
					abbr = ""
				else:
					abbr = "A"

			row[d.strftime("%d-%m-%Y")] = abbr

		attendance_values.append(row)

	return attendance_values


def get_holiday_status(holiday_date: date, holidays: list) -> str:
	status = None
	if holidays:
		for holiday in holidays:
			if holiday_date == holiday.get("holiday_date"):
				if holiday.get("weekly_off"):
					status = "Weekly Off"
				else:
					status = "Holiday"
				break
	return status


def get_leave_summary(employee: str, filters: Filters) -> dict[str, float]:
	"""Returns a dict of leave type and corresponding leaves taken by employee like:
	{'leave_without_pay': 1.0, 'sick_leave': 2.0}
	"""
	Attendance = frappe.qb.DocType("Attendance")
	day_case = frappe.qb.terms.Case().when(Attendance.status == "Half Day", 0.5).else_(1)
	sum_leave_days = Sum(day_case).as_("leave_days")

	attendance_date_condition = get_date_condition(Attendance.attendance_date, filters)

	leave_details = (
		frappe.qb.from_(Attendance)
		.select(Attendance.leave_type, sum_leave_days)
		.where(
			(Attendance.employee == employee)
			& (Attendance.docstatus == 1)
			& (Attendance.company.isin(filters.companies))
			& ((Attendance.leave_type.isnotnull()) | (Attendance.leave_type != ""))
			& (attendance_date_condition)
		)
		.groupby(Attendance.leave_type)
	).run(as_dict=True)

	leaves = {}
	for d in leave_details:
		leave_type = frappe.scrub(d.leave_type)
		leaves[leave_type] = d.leave_days

	return leaves


def get_entry_exits_summary(employee: str, filters: Filters) -> dict[str, float]:
	"""Returns total late entries and total early exits for employee like:
	{'total_late_entries': 5, 'total_early_exits': 2}
	"""
	Attendance = frappe.qb.DocType("Attendance")

	late_entry_case = frappe.qb.terms.Case().when(Attendance.late_entry == "1", "1")
	count_late_entries = Count(late_entry_case).as_("total_late_entries")

	early_exit_case = frappe.qb.terms.Case().when(Attendance.early_exit == "1", "1")
	count_early_exits = Count(early_exit_case).as_("total_early_exits")

	attendance_date_condition = get_date_condition(Attendance.attendance_date, filters)

	entry_exits = (
		frappe.qb.from_(Attendance)
		.select(count_late_entries, count_early_exits)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.employee == employee)
			& (Attendance.company.isin(filters.companies))
			& (attendance_date_condition)
		)
	).run(as_dict=True)

	return entry_exits[0]


@frappe.whitelist()
def get_attendance_years() -> str:
	"""Returns all the years for which attendance records exist"""
	Attendance = frappe.qb.DocType("Attendance")
	year_list = (
		frappe.qb.from_(Attendance).select(Extract("year", Attendance.attendance_date).as_("year")).distinct()
	).run(as_dict=True)

	if year_list:
		year_list.sort(key=lambda d: d.year, reverse=True)
	else:
		year_list = [frappe._dict({"year": getdate().year})]

	return "\n".join(cstr(entry.year) for entry in year_list)


def get_chart_data(attendance_map: dict, filters: Filters) -> dict:
	days = get_columns_for_days(filters)
	labels = []
	absent = []
	present = []
	leave = []

	for day in days:
		labels.append(day["label"])
		total_absent_on_day = total_leaves_on_day = total_present_on_day = 0

		for __, attendance_dict in attendance_map.items():
			for __, attendance in attendance_dict.items():
				attendance_on_day = attendance.get(getdate(day["fieldname"], parse_day_first=True))

				if attendance_on_day == "On Leave":
					# leave should be counted only once for the entire day
					total_leaves_on_day += 1
					break
				elif attendance_on_day == "Absent":
					total_absent_on_day += 1
				elif attendance_on_day in ["Present", "Work From Home", "On Duty"]:
					total_present_on_day += 1
				elif attendance_on_day == "Half Day":
					total_present_on_day += 0.5
					total_leaves_on_day += 0.5

		absent.append(total_absent_on_day)
		present.append(total_present_on_day)
		leave.append(total_leaves_on_day)

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Absent"), "values": absent},
				{"name": _("Present"), "values": present},
				{"name": _("Leave"), "values": leave},
			],
		},
		"type": "line",
		"colors": ["red", "green", "blue"],
	}
