# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, format_date, get_url_to_list, getdate

import hrms
from hrms.hr.two_level_approval import (
	gate_submission,
	handle_secondary_approval_flow,
	set_approval_stage,
	set_secondary_approver,
)
from hrms.hr.utils import (
	create_additional_leave_ledger_entry,
	get_holiday_dates_for_employee,
	get_leave_period,
	share_doc_with_approver,
	validate_active_employee,
	validate_dates,
	validate_overlap,
)


class CompensatoryLeaveRequest(Document):
	def validate(self):
		validate_active_employee(self.employee)
		validate_dates(self, self.work_from_date, self.work_end_date)
		if self.half_day:
			if not self.half_day_date:
				frappe.throw(_("Half Day Date is mandatory"))
			if not getdate(self.work_from_date) <= getdate(self.half_day_date) <= getdate(self.work_end_date):
				frappe.throw(_("Half Day Date should be in between Work From Date and Work End Date"))
		validate_overlap(self, self.work_from_date, self.work_end_date)
		self.validate_holidays()
		self.validate_attendance()
		if not self.leave_type:
			self._set_default_leave_type()
		if not self.leave_type:
			frappe.throw(_("Leave Type is mandatory"))
		self._set_approver()
		set_secondary_approver(self)
		set_approval_stage(self)
		self._validate_status_change()

	def _set_default_leave_type(self):
		"""Auto-set Compensatory Off leave type if it exists."""
		if frappe.db.exists("Leave Type", "Compensatory Off"):
			self.leave_type = "Compensatory Off"

	def _set_approver(self):
		"""Auto-set approver from employee's leave_approver if not set."""
		if self.approver:
			return
		approver = frappe.db.get_value("Employee", self.employee, "leave_approver")
		if approver:
			self.approver = approver
			self.approver_name = frappe.db.get_value("User", approver, "full_name")

	def _validate_status_change(self):
		"""Prevent employee from approving their own request."""
		if self.docstatus != 0:
			return
		if not self.is_new() and not self.has_value_changed("status"):
			return
		if self.status in ("Approved", "Rejected"):
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user == frappe.session.user:
				frappe.throw(_("You cannot approve or reject your own Compensatory Leave Request."))

	def validate_attendance(self):
		attendance_records = frappe.get_all(
			"Attendance",
			filters=[
				["attendance_date", "between", [self.work_from_date, self.work_end_date]],
				["status", "in", ["Present", "Work From Home", "Half Day", "On Duty"]],
				["docstatus", "=", 1],
				["employee", "=", self.employee],
			],
			fields=["attendance_date", "status"],
		)

		half_days = [entry.attendance_date for entry in attendance_records if entry.status == "Half Day"]

		if half_days and (not self.half_day or getdate(self.half_day_date) not in half_days):
			frappe.throw(
				_(
					"You were only present for Half Day on {}. Cannot apply for a full day compensatory leave"
				).format(", ".join([frappe.bold(format_date(half_day)) for half_day in half_days]))
			)

		if len(attendance_records) < date_diff(self.work_end_date, self.work_from_date) + 1:
			frappe.throw(_("You are not present all day(s) between compensatory leave request days"))

	def validate_holidays(self):
		holidays = get_holiday_dates_for_employee(self.employee, self.work_from_date, self.work_end_date)
		if len(holidays) < date_diff(self.work_end_date, self.work_from_date) + 1:
			if date_diff(self.work_end_date, self.work_from_date):
				msg = _("The days between {0} to {1} are not valid holidays.").format(
					frappe.bold(format_date(self.work_from_date)),
					frappe.bold(format_date(self.work_end_date)),
				)
			else:
				msg = _("{0} is not a holiday.").format(frappe.bold(format_date(self.work_from_date)))

			frappe.throw(msg)

	def before_submit(self):
		gate_submission(self)

	def on_submit(self):
		if self.status in ("Open", "Cancelled"):
			frappe.throw(
				_("Only Compensatory Leave Requests with status 'Approved' or 'Rejected' can be submitted.")
			)
		if self.status == "Approved":
			self._create_leave_allocation()
		self.publish_update()

	def on_cancel(self):
		if self.leave_allocation:
			date_difference = date_diff(self.work_end_date, self.work_from_date) + 1
			if self.half_day:
				date_difference -= 0.5
			leave_allocation = frappe.get_doc("Leave Allocation", self.leave_allocation)
			if leave_allocation:
				leave_allocation.new_leaves_allocated -= date_difference
				if leave_allocation.new_leaves_allocated < 0:
					leave_allocation.new_leaves_allocated = 0
				leave_allocation.validate()
				leave_allocation.db_set("new_leaves_allocated", leave_allocation.total_leaves_allocated)
				leave_allocation.db_set("total_leaves_allocated", leave_allocation.total_leaves_allocated)

				# create reverse entry on cancellation
				create_additional_leave_ledger_entry(
					leave_allocation, date_difference * -1, add_days(self.work_end_date, 1)
				)
		self.publish_update()

	def on_update(self):
		if self.approver:
			share_doc_with_approver(self, self.approver)
		handle_secondary_approval_flow(self)
		self.publish_update()

	def after_delete(self):
		self.publish_update()

	def publish_update(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id", cache=True)
		hrms.refetch_resource("hrms:my_compensatory_requests", employee_user)
		hrms.refetch_resource("hrms:team_compensatory_requests")

	def _create_leave_allocation(self):
		"""Create or update leave allocation after approval."""
		company = frappe.db.get_value("Employee", self.employee, "company")
		date_difference = date_diff(self.work_end_date, self.work_from_date) + 1
		if self.half_day:
			date_difference -= 0.5

		comp_leave_valid_from = add_days(self.work_end_date, 1)
		leave_period = get_leave_period(comp_leave_valid_from, comp_leave_valid_from, company)
		if leave_period:
			leave_allocation = self.get_existing_allocation(comp_leave_valid_from)
			if leave_allocation:
				leave_allocation.new_leaves_allocated += date_difference
				leave_allocation.validate()
				leave_allocation.db_set("new_leaves_allocated", leave_allocation.total_leaves_allocated)
				leave_allocation.db_set("total_leaves_allocated", leave_allocation.total_leaves_allocated)

				# generate additional ledger entry for the new compensatory leaves off
				create_additional_leave_ledger_entry(leave_allocation, date_difference, comp_leave_valid_from)

			else:
				leave_allocation = self.create_leave_allocation(leave_period, date_difference)
			self.db_set("leave_allocation", leave_allocation.name)
		else:
			comp_leave_valid_from = frappe.bold(format_date(comp_leave_valid_from))
			msg = _("This compensatory leave will be applicable from {0}.").format(comp_leave_valid_from)
			msg += " " + _(
				"Currently, there is no {0} leave period for this date to create/update leave allocation."
			).format(frappe.bold(_("active")))
			msg += "<br><br>" + _("Please create a new {0} for the date {1} first.").format(
				f"""<a href='{get_url_to_list("Leave Period")}'>Leave Period</a>""",
				comp_leave_valid_from,
			)
			frappe.throw(msg, title=_("No Leave Period Found"))

	def get_existing_allocation(self, comp_leave_valid_from: datetime.date) -> dict | None:
		leave_allocation = frappe.db.get_all(
			"Leave Allocation",
			filters={
				"employee": self.employee,
				"leave_type": self.leave_type,
				"from_date": ("<=", comp_leave_valid_from),
				"to_date": (">=", comp_leave_valid_from),
				"docstatus": 1,
			},
			limit=1,
		)

		if leave_allocation:
			return frappe.get_doc("Leave Allocation", leave_allocation[0].name)

	def create_leave_allocation(self, leave_period, date_difference):
		is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
		allocation = frappe.get_doc(
			dict(
				doctype="Leave Allocation",
				employee=self.employee,
				employee_name=self.employee_name,
				leave_type=self.leave_type,
				from_date=add_days(self.work_end_date, 1),
				to_date=leave_period[0].to_date,
				carry_forward=cint(is_carry_forward),
				new_leaves_allocated=date_difference,
				total_leaves_allocated=date_difference,
				description=self.reason,
			)
		)
		allocation.insert(ignore_permissions=True)
		allocation.submit()
		return allocation


# ── Whitelisted approval API functions ────────────────────────────────────────

@frappe.whitelist()
def compensatory_approve_submit(compensatory_leave_request):
	"""Primary approver approves and submits (single-level flow — no secondary approver)."""
	doc = frappe.get_doc("Compensatory Leave Request", compensatory_leave_request)

	if frappe.session.user != doc.approver:
		frappe.throw(_("Only the Approver can perform this action."))

	if doc.custom_secondary_leave_approver:
		frappe.throw(_("This request has a secondary approver. Use the two-level approval flow."))

	if doc.docstatus != 0:
		frappe.throw(_("This compensatory leave request has already been submitted."))

	doc.status = "Approved"
	doc.flags.ignore_permissions = True
	doc.submit()

	return {"status": "success", "message": _("Compensatory Leave Request approved. Leave balance updated.")}


@frappe.whitelist()
def compensatory_reject_submit(compensatory_leave_request, reason=None):
	"""Primary approver rejects (single-level flow — no secondary approver)."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Compensatory Leave Request", compensatory_leave_request)

	if frappe.session.user != doc.approver:
		frappe.throw(_("Only the Approver can perform this action."))

	if doc.custom_secondary_leave_approver:
		frappe.throw(_("This request has a secondary approver. Use the two-level approval flow."))

	if doc.docstatus != 0:
		frappe.throw(_("This compensatory leave request has already been submitted."))

	doc.status = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment("Comment", _("Rejected by Approver: {0}").format(reason))

	return {"status": "success", "message": _("Compensatory Leave Request rejected.")}


@frappe.whitelist()
def compensatory_project_reporting_reject(compensatory_leave_request, reason=None):
	"""Primary rejects for two-level flow."""
	from hrms.hr.two_level_approval import primary_reject
	return primary_reject("Compensatory Leave Request", compensatory_leave_request, reason)


@frappe.whitelist()
def compensatory_secondary_approve(compensatory_leave_request):
	"""Secondary approver approves."""
	from hrms.hr.two_level_approval import secondary_approve
	return secondary_approve("Compensatory Leave Request", compensatory_leave_request)


@frappe.whitelist()
def compensatory_secondary_reject(compensatory_leave_request, reason=None):
	"""Secondary approver rejects."""
	from hrms.hr.two_level_approval import secondary_reject
	return secondary_reject("Compensatory Leave Request", compensatory_leave_request, reason)
