import frappe
from frappe.model.document import Document


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
	employee_filter = f"= '{employee}'" if employee else "is not null"

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
		where docstatus = 0
			and (employee {employee_filter}
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
		where docstatus = 0
			and (employee {employee_filter}
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
		where docstatus = 0
			and (employee {employee_filter}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	# Compensatory Leave Request
	queries.append(
		f"""
		select
			'Compensatory Leave Request' as request_type,
			'Compensatory Leave Request' as reference_doctype,
			name as reference_name,
			employee_name,
			status,
			work_from_date as request_date,
			reason,
			custom_approval_stage as approval_stage,
			leave_approver_name as approver_name,
			creation
		from `tabCompensatory Leave Request`
		where docstatus = 0
			and (employee {employee_filter}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	# Attendance Request
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
			leave_approver_name as approver_name,
			creation
		from `tabAttendance Request`
		where docstatus = 0
			and (employee {employee_filter}
			     or leave_approver = %(user)s
			     or custom_secondary_leave_approver = %(user)s)
		"""
	)

	return " union all ".join(queries)


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
		{"user": frappe.session.user, "start": start, "limit": limit},
		as_dict=True,
	)

	# Frappe expects "name" field; reuse reference_name for that.
	for row in rows:
		row.name = row.reference_name

	return rows


def get_count(args):
	base_query = _build_base_query()
	query = f"select count(1) as cnt from ({base_query}) as q"
	return frappe.db.sql(query, {"user": frappe.session.user})[0][0]

