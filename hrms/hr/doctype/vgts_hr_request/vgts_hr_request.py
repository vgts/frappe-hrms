import frappe
from frappe.model.document import Document
from frappe.utils import cint


class VGTSHRRequest(Document):
	"""Virtual doctype; data is provided via get_list, not stored."""

	def db_insert(self, *args, **kwargs):
		frappe.throw(frappe._("VGTS HR Request is a virtual DocType and cannot be saved."))

	def db_update(self, *args, **kwargs):
		frappe.throw(frappe._("VGTS HR Request is a virtual DocType and cannot be updated."))

	def load_from_db(self):
		# List view uses get_list; individual form view is not required for this DocType.
		pass


def _build_base_query():
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	user = frappe.session.user

	# If no employee record, show only items where user is approver.
	employee_clause = "employee = %(employee)s" if employee else "1=0"

	queries = []

	# Leave Application
	queries.append(
		f"""
		select
			'Leave Application' as request_type,
			'Leave Application' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			from_date as request_date,
			leave_type as reason,
			custom_approval_stage as approval_stage,
			leave_approver_name as approver_name,
			creation
		from `tabLeave Application`
		where docstatus < 2
			and ({employee_clause}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	# Attendance Regularization
	queries.append(
		f"""
		select
			'Attendance Regularization' as request_type,
			'Attendance Regularization' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			attendance_date as request_date,
			reason,
			custom_approval_stage as approval_stage,
			leave_approver_name as approver_name,
			creation
		from `tabAttendance Regularization`
		where docstatus < 2
			and ({employee_clause}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	# Employee Permission
	queries.append(
		f"""
		select
			'Employee Permission' as request_type,
			'Employee Permission' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			permission_date as request_date,
			reason,
			custom_approval_stage as approval_stage,
			leave_approver_name as approver_name,
			creation
		from `tabEmployee Permission`
		where docstatus < 2
			and ({employee_clause}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	# Compensatory Leave Request (optional approver columns on custom / older schemas)
	_comp_cols = set(frappe.db.get_table_columns("Compensatory Leave Request"))
	_comp_ext = {
		"leave_approver",
		"custom_secondary_leave_approver",
		"custom_approval_stage",
		"leave_approver_name",
	}
	_st = "status" if "status" in _comp_cols else "''"
	if _comp_ext <= _comp_cols:
		queries.append(
			f"""
			select
				'Compensatory Leave Request' as request_type,
				'Compensatory Leave Request' as reference_doctype,
				name as reference_name,
				employee_name,
				{_st} as status,
				work_from_date as request_date,
				reason,
				custom_approval_stage as approval_stage,
				leave_approver_name as approver_name,
				creation
			from `tabCompensatory Leave Request`
			where docstatus < 2
				and ({employee_clause}
					 or leave_approver = %(user)s
					 or custom_secondary_leave_approver = %(user)s)
			"""
		)
	else:
		queries.append(
			f"""
			select
				'Compensatory Leave Request' as request_type,
				'Compensatory Leave Request' as reference_doctype,
				name as reference_name,
				employee_name,
				{_st} as status,
				work_from_date as request_date,
				reason,
				null as approval_stage,
				null as approver_name,
				creation
			from `tabCompensatory Leave Request`
			where docstatus < 2
				and ({employee_clause})
			"""
		)

	# Attendance Request (primary approver field is `approver`, not leave_approver)
	queries.append(
		f"""
		select
			'Attendance Request' as request_type,
			'Attendance Request' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			from_date as request_date,
			reason,
			custom_approval_stage as approval_stage,
			approver_name as approver_name,
			creation
		from `tabAttendance Request`
		where docstatus < 2
			and ({employee_clause}
			     or approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	return " union all ".join(queries)


def _build_dashboard_base_query():
	"""Same visibility as list view, with extra columns for approval actions in the dashboard UI."""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	employee_clause = "employee = %(employee)s" if employee else "1=0"
	queries = []

	def tail_leave_like(doctype_name, type_label, date_field, reason_expr, approver_name_col):
		tn = doctype_name if doctype_name.startswith("tab") else f"tab{doctype_name}"
		return f"""
		select
			'{type_label}' as request_type,
			'{type_label}' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			{date_field} as request_date,
			{reason_expr} as reason,
			custom_approval_stage as approval_stage,
			{approver_name_col} as approver_name,
			creation,
			docstatus,
			leave_approver,
			custom_secondary_leave_approver
		from `{tn}`
		where docstatus < 2
			and ({employee_clause}
				 or leave_approver = %(user)s
				 or custom_secondary_leave_approver = %(user)s)
		"""

	queries.append(tail_leave_like("Leave Application", "Leave Application", "from_date", "leave_type", "leave_approver_name"))
	queries.append(
		tail_leave_like(
			"Attendance Regularization",
			"Attendance Regularization",
			"attendance_date",
			"reason",
			"leave_approver_name",
		)
	)
	queries.append(
		tail_leave_like(
			"Employee Permission",
			"Employee Permission",
			"permission_date",
			"reason",
			"leave_approver_name",
		)
	)

	# Compensatory — same column guards as list query
	comp_cols = set(frappe.db.get_table_columns("Compensatory Leave Request"))
	comp_ext = {
		"leave_approver",
		"custom_secondary_leave_approver",
		"custom_approval_stage",
		"leave_approver_name",
	}
	st_sel = "status" if "status" in comp_cols else "''"
	if comp_ext <= comp_cols:
		queries.append(
			f"""
			select
				'Compensatory Leave Request' as request_type,
				'Compensatory Leave Request' as reference_doctype,
				name as reference_name,
				employee_name,
				{st_sel} as status,
				work_from_date as request_date,
				reason,
				custom_approval_stage as approval_stage,
				leave_approver_name as approver_name,
				creation,
				docstatus,
				leave_approver,
				custom_secondary_leave_approver
			from `tabCompensatory Leave Request`
			where docstatus < 2
				and ({employee_clause}
					 or leave_approver = %(user)s
					 or custom_secondary_leave_approver = %(user)s)
			"""
		)
	else:
		queries.append(
			f"""
			select
				'Compensatory Leave Request' as request_type,
				'Compensatory Leave Request' as reference_doctype,
				name as reference_name,
				employee_name,
				{st_sel} as status,
				work_from_date as request_date,
				reason,
				null as approval_stage,
				null as approver_name,
				creation,
				docstatus,
				null as leave_approver,
				null as custom_secondary_leave_approver
			from `tabCompensatory Leave Request`
			where docstatus < 2
				and ({employee_clause})
			"""
		)

	queries.append(
		f"""
		select
			'Attendance Request' as request_type,
			'Attendance Request' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			from_date as request_date,
			reason,
			custom_approval_stage as approval_stage,
			approver_name as approver_name,
			creation,
			docstatus,
			approver as leave_approver,
			custom_secondary_leave_approver
		from `tabAttendance Request`
		where docstatus < 2
			and ({employee_clause}
				 or approver = %(user)s
				 or custom_secondary_leave_approver = %(user)s)
		"""
	)

	return " union all ".join(queries)


def _dashboard_sql_params():
	return {
		"user": frappe.session.user,
		"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
	}


@frappe.whitelist()
def get_dashboard_data(limit_start=0, limit_page_length=80, status_filter=None):
	"""Feed the HR Requests desk dashboard.

	Phase 1 (as requested): return Leave Application rows only.
	- HR roles (System Manager / HR Manager / HR User): see all employee leave requests.
	- Other users: see own requests + requests where they are approver/secondary approver.
	"""
	start = cint(limit_start)
	limit = cint(limit_page_length) or 80
	if limit > 200:
		limit = 200

	status_filter = (status_filter or "").strip()
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	roles = set(frappe.get_roles(frappe.session.user))
	is_hr_viewer = bool({"System Manager", "HR Manager", "HR User"} & roles)

	params = {"user": frappe.session.user, "employee": employee, "start": start, "limit": limit}
	where_parts = ["la.docstatus < 2"]

	if not is_hr_viewer:
		where_parts.append(
			"(la.employee = %(employee)s or la.leave_approver = %(user)s or la.custom_secondary_leave_approver = %(user)s)"
		)
	if status_filter and status_filter.lower() != "all":
		where_parts.append("la.status = %(status_filter)s")
		params["status_filter"] = status_filter

	query = f"""
		select
			'Leave Application' as request_type,
			'Leave Application' as reference_doctype,
			la.name as reference_name,
			la.employee_name,
			la.status,
			la.from_date as request_date,
			la.leave_type as reason,
			la.total_leave_days,
			la.custom_approval_stage as approval_stage,
			la.leave_approver_name as approver_name,
			case
				when la.custom_approval_stage = 'Pending Project Reporting Approval' then la.leave_approver_name
				when la.custom_approval_stage = 'Pending Secondary Reporting Approval' then la.custom_secondary_approver_name
				when la.status = 'Open' and ifnull(la.custom_secondary_leave_approver, '') = '' then la.leave_approver_name
				else ''
			end as pending_with,
			la.creation,
			la.docstatus,
			la.leave_approver,
			la.custom_secondary_leave_approver,
			la.custom_secondary_approver_name
		from `tabLeave Application` la
		where {" and ".join(where_parts)}
		order by creation desc
		limit %(start)s, %(limit)s
	"""
	return frappe.db.sql(query, params, as_dict=True)


def get_list(args):
	limit = args.get("limit_page_length") or 20
	start = args.get("limit_start") or 0

	base_query = _build_base_query()

	order_by = "order by creation desc"
	query = f"""
		select
			request_type,
			reference_doctype,
			reference_name,
			employee_name,
			status,
			request_date,
			reason,
			approval_stage,
			approver_name
		from (
			{base_query}
		) as q
		{order_by}
		limit %(start)s, %(limit)s
	"""

	rows = frappe.db.sql(
		query,
		{
			"user": frappe.session.user,
			"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
			"start": start,
			"limit": limit,
		},
		as_dict=True,
	)

	# Frappe expects "name" field; reuse reference_name for that.
	for row in rows:
		row.name = row.reference_name

	return rows


def get_count(args):
	base_query = _build_base_query()
	query = f"select count(1) as cnt from ({base_query}) as q"
	return frappe.db.sql(
		query,
		{
			"user": frappe.session.user,
			"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
		},
	)[0][0]

