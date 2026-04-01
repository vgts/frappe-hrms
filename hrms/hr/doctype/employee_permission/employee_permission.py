# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, get_datetime, getdate, flt, cint, formatdate

from hrms.hr.utils import validate_active_employee, share_doc_with_approver, set_employee_name
from hrms.mixins.pwa_notifications import PWANotificationsMixin


class EmployeePermission(Document, PWANotificationsMixin):
	def validate(self):
		validate_active_employee(self.employee)
		set_employee_name(self)
		self.validate_times()
		self.validate_duration()
		self.validate_monthly_limit()
		self.validate_overlap()
		self.validate_status_change()
		self.set_leave_approver()
		self.set_secondary_leave_approver()
		self.set_approval_stage()

	def validate_status_change(self):
		"""Prevent employee from approving or rejecting their own permission request."""
		if self.docstatus != 0:
			return
		if not self.is_new() and not self.has_value_changed("status"):
			return
		if self.status in ("Approved", "Rejected"):
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user == frappe.session.user:
				frappe.throw(_("You cannot approve or reject your own Permission Request."))

	def validate_times(self):
		if self.from_time and self.to_time:
			# Compare time strings directly (HH:MM:SS format)
			if self.from_time >= self.to_time:
				frappe.throw(_("To Time must be after From Time"))

	def validate_duration(self):
		if self.from_time and self.to_time:
			# Calculate duration in hours
			from datetime import datetime, timedelta

			from_dt = datetime.strptime(str(self.from_time), "%H:%M:%S")
			to_dt = datetime.strptime(str(self.to_time), "%H:%M:%S")
			diff = (to_dt - from_dt).total_seconds() / 3600
			self.duration = round(diff, 2)

			if self.duration < 0.5:
				frappe.throw(_("Minimum permission duration is 30 minutes"))
			if self.duration > 2:
				frappe.throw(_("Maximum permission duration is 2 hours"))

	def validate_monthly_limit(self):
		if not self.permission_date or not self.employee:
			return

		month_start = getdate(self.permission_date).replace(day=1)
		if month_start.month == 12:
			month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
		else:
			month_end = month_start.replace(month=month_start.month + 1, day=1)

		from frappe.utils import add_days

		month_end = add_days(month_end, -1)

		existing = frappe.db.sql(
			"""
			SELECT SUM(duration) as total
			FROM `tabEmployee Permission`
			WHERE employee = %s
			AND permission_date BETWEEN %s AND %s
			AND docstatus < 2
			AND name != %s
		""",
			(self.employee, month_start, month_end, self.name or ""),
			as_dict=True,
		)

		total = flt(existing[0].total) if existing else 0
		if total + flt(self.duration) > 4:
			frappe.throw(
				_(
					"Monthly permission limit exceeded. Used: {0} hrs, Requesting: {1} hrs, Limit: 4 hrs"
				).format(total, self.duration)
			)

	def validate_overlap(self):
		if not self.permission_date or not self.from_time or not self.to_time:
			return

		overlaps = frappe.db.sql(
			"""
			SELECT name FROM `tabEmployee Permission`
			WHERE employee = %s
			AND permission_date = %s
			AND docstatus < 2
			AND name != %s
			AND (
				(from_time < %s AND to_time > %s)
				OR (from_time < %s AND to_time > %s)
				OR (from_time >= %s AND to_time <= %s)
			)
		""",
			(
				self.employee,
				self.permission_date,
				self.name or "",
				self.to_time,
				self.from_time,
				self.to_time,
				self.from_time,
				self.from_time,
				self.to_time,
			),
		)

		if overlaps:
			frappe.throw(
				_("Permission request overlaps with existing request {0}").format(overlaps[0][0])
			)

	def set_leave_approver(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id")

		# Clear self-assigned approver (employee cannot be their own approver)
		if self.leave_approver and self.leave_approver == employee_user:
			self.leave_approver = None
			self.leave_approver_name = None

		if self.leave_approver:
			return

		leave_approver = frappe.db.get_value("Employee", self.employee, "leave_approver")

		if leave_approver and leave_approver != employee_user:
			self.leave_approver = leave_approver
			self.leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name")

	def set_secondary_leave_approver(self):
		if self.custom_secondary_leave_approver or not self.employee:
			return

		secondary_emp = frappe.db.get_value("Employee", self.employee, "custom_secondary_reporting_")
		if secondary_emp:
			user_id = frappe.db.get_value("Employee", secondary_emp, "user_id")
			if user_id:
				self.custom_secondary_leave_approver = user_id
				self.custom_secondary_approver_name = frappe.db.get_value("User", user_id, "full_name")

	def set_approval_stage(self):
		if self.is_new() and self.custom_secondary_leave_approver:
			self.custom_approval_stage = "Pending Project Reporting Approval"

	def after_insert(self):
		self.notify_approver()

	def on_update(self):
		if self.status == "Open" and self.docstatus < 1:
			if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
				self.notify_leave_approver()

		share_doc_with_approver(self, self.leave_approver)
		self.handle_secondary_approval_flow()

		if not self._is_pending_secondary():
			self.notify_approval_status()

		self.publish_update()

	def _is_pending_secondary(self):
		return (
			self.custom_secondary_leave_approver
			and self.custom_approval_stage in (
				"Pending Project Reporting Approval",
				"Pending Secondary Reporting Approval",
			)
		)

	def handle_secondary_approval_flow(self):
		if self.docstatus != 0:
			return
		if not (
			self.has_value_changed("status")
			and self.status == "Approved"
			and self.custom_approval_stage == "Pending Project Reporting Approval"
			and self.custom_secondary_leave_approver
		):
			return
		self._forward_to_secondary()

	def _forward_to_secondary(self):
		self.db_set("custom_approval_stage", "Pending Secondary Reporting Approval")
		self.custom_approval_stage = "Pending Secondary Reporting Approval"

		frappe.share.add_docshare(
			self.doctype,
			self.name,
			self.custom_secondary_leave_approver,
			write=1,
			submit=1,
			flags={"ignore_share_permission": True},
		)
		self.notify_secondary_approver()

	def notify_secondary_approver(self):
		to_user = self.custom_secondary_leave_approver
		if not to_user or frappe.session.user == to_user:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{frappe.bold(self.employee_name)}'s {frappe.bold('Permission Request')} "
			f"{self.name} requires your secondary approval"
		)
		notification.from_user = frappe.session.user
		notification.to_user = to_user
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

		self._trigger_notification_count_refetch(to_user)

	def notify_leave_approver(self):
		if not self.leave_approver:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{frappe.bold(self.employee_name)} has requested a "
			f"{frappe.bold('Permission')} on {formatdate(self.permission_date)}"
		)
		notification.from_user = frappe.session.user
		notification.to_user = self.leave_approver
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

	def before_submit(self):
		if not self.custom_secondary_leave_approver:
			return

		user = frappe.session.user

		if (
			user == self.custom_secondary_leave_approver
			and self.custom_approval_stage == "Pending Secondary Reporting Approval"
		):
			self.custom_approval_stage = "Approved"
			return

		if self.custom_approval_stage in ("Approved", "Rejected"):
			return

		if self.status == "Approved" and self.custom_approval_stage in (
			"Pending Project Reporting Approval",
			"Pending Secondary Reporting Approval",
		):
			if self.custom_approval_stage == "Pending Project Reporting Approval":
				self._forward_to_secondary()

			self.docstatus = 0
			frappe.msgprint(
				_(
					"Permission Request has been forwarded to {0} for final approval."
				).format(
					self.custom_secondary_approver_name
					or self.custom_secondary_leave_approver
				),
				title=_("Forwarded to Secondary Approver"),
				indicator="blue",
			)
			return

		frappe.throw(
			_("Permission Request cannot be submitted at this stage: {0}").format(
				self.custom_approval_stage
			)
		)

	def on_submit(self):
		if self.status in ["Open", "Cancelled"]:
			frappe.throw(
				_(
					"Only Permission Requests with status 'Approved' and 'Rejected' can be submitted"
				)
			)
		self.publish_update()

	def on_cancel(self):
		self.publish_update()

	def publish_update(self):
		import hrms

		employee_user = frappe.db.get_value(
			"Employee", self.employee, "user_id", cache=True
		)

		# Notify the employee
		if employee_user:
			hrms.refetch_resource("hrms:my_permissions", employee_user)

		# Notify the primary approver
		if self.leave_approver:
			hrms.refetch_resource("hrms:team_permissions", self.leave_approver)

		# Notify the secondary approver
		if self.custom_secondary_leave_approver:
			hrms.refetch_resource("hrms:team_permissions", self.custom_secondary_leave_approver)

	def after_delete(self):
		self.publish_update()


# Whitelisted methods for two-level approval


@frappe.whitelist()
def permission_project_reporting_reject(employee_permission, reason=None):
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Employee Permission", employee_permission)

	if frappe.session.user != doc.leave_approver:
		frappe.throw(_("Only the Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Project Reporting Approval":
		frappe.throw(
			_("This permission request is not pending project reporting approval.")
		)

	if doc.docstatus != 0:
		frappe.throw(_("This permission request has already been submitted."))

	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment(
		"Comment",
		_("Rejected by Project Reporting (Leave Approver): {0}").format(reason),
	)
	return {"status": "success", "message": _("Permission Request rejected and cancelled.")}


@frappe.whitelist()
def permission_secondary_approve(employee_permission):
	doc = frappe.get_doc("Employee Permission", employee_permission)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(
			_("This permission request is not pending secondary approval.")
		)

	if doc.status != "Approved":
		frappe.throw(
			_(
				"Permission Request must be approved by the primary Leave Approver first."
			)
		)

	doc.custom_approval_stage = "Approved"
	doc.flags.ignore_permissions = True
	doc.submit()

	return {"status": "success", "message": _("Permission Request approved and submitted.")}


@frappe.whitelist()
def permission_secondary_reject(employee_permission, reason=None):
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Employee Permission", employee_permission)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(
			_("This permission request is not pending secondary approval.")
		)

	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment(
		"Comment", _("Rejected by Secondary Approver: {0}").format(reason)
	)
	return {"status": "success", "message": _("Permission Request rejected and cancelled.")}


@frappe.whitelist()
def permission_primary_approve_submit(employee_permission):
	"""Approve and submit for leave_approver when there is no secondary approver."""
	doc = frappe.get_doc("Employee Permission", employee_permission)

	if frappe.session.user != doc.leave_approver:
		frappe.throw(_("Only the Leave Approver can perform this action."))

	if doc.custom_secondary_leave_approver:
		frappe.throw(_("This request requires secondary approval. Use the two-level approval flow."))

	if doc.status != "Open" or doc.docstatus != 0:
		frappe.throw(_("This permission request cannot be approved at this stage."))

	doc.status = "Approved"
	doc.flags.ignore_permissions = True
	doc.submit()

	return {"status": "success", "message": _("Permission Request approved and submitted.")}


@frappe.whitelist()
def permission_primary_reject_submit(employee_permission, reason=None):
	"""Reject and cancel for leave_approver when there is no secondary approver."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Employee Permission", employee_permission)

	if frappe.session.user != doc.leave_approver:
		frappe.throw(_("Only the Leave Approver can perform this action."))

	if doc.custom_secondary_leave_approver:
		frappe.throw(_("This request requires secondary approval. Use the two-level approval flow."))

	if doc.docstatus != 0:
		frappe.throw(_("This permission request has already been submitted."))

	doc.status = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment("Comment", _("Rejected by Leave Approver: {0}").format(reason))
	return {"status": "success", "message": _("Permission Request rejected.")}


@frappe.whitelist()
def get_available_permission_hours(employee, date=None):
	"""Return available permission hours for the month with approved/pending breakdown."""
	if not date:
		date = frappe.utils.today()

	month_start = getdate(date).replace(day=1)
	if month_start.month == 12:
		month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
	else:
		month_end = month_start.replace(month=month_start.month + 1, day=1)

	from frappe.utils import add_days
	month_end = add_days(month_end, -1)

	# Approved (submitted, docstatus=1) - final deducted hours
	approved = frappe.db.sql("""
		SELECT COALESCE(SUM(duration), 0) as total
		FROM `tabEmployee Permission`
		WHERE employee = %s
		AND permission_date BETWEEN %s AND %s
		AND docstatus = 1
	""", (employee, month_start, month_end), as_dict=True)

	# Pending (open/draft, docstatus=0) - applied but not yet approved
	pending = frappe.db.sql("""
		SELECT COALESCE(SUM(duration), 0) as total
		FROM `tabEmployee Permission`
		WHERE employee = %s
		AND permission_date BETWEEN %s AND %s
		AND docstatus = 0
		AND status = 'Open'
	""", (employee, month_start, month_end), as_dict=True)

	approved_hours = flt(approved[0].total) if approved else 0
	pending_hours = flt(pending[0].total) if pending else 0
	used_hours = approved_hours + pending_hours
	available = max(4 - used_hours, 0)

	def _fmt(h):
		hrs = int(h)
		mins = int(round((h - hrs) * 60))
		return f"{hrs:02d}:{mins:02d}"

	return {
		"available_hours": available,
		"approved_hours": approved_hours,
		"pending_hours": pending_hours,
		"used_hours": used_hours,
		"monthly_limit": 4,
		"formatted_available": _fmt(available),
		"formatted_approved": _fmt(approved_hours),
		"formatted_pending": _fmt(pending_hours),
		"formatted_used": _fmt(used_hours),
		"available_percentage": round((available / 4) * 100),
	}


@frappe.whitelist()
def get_permission_approval_details(employee_permission):
	doc = frappe.get_doc("Employee Permission", employee_permission)

	def _get_user_image(user_id):
		if not user_id:
			return None
		image = frappe.db.get_value("User", user_id, "user_image")
		if not image:
			image = frappe.db.get_value("Employee", {"user_id": user_id}, "image")
		return image

	return {
		"approval_stage": doc.custom_approval_stage,
		"employee": doc.employee,
		"employee_user_id": frappe.db.get_value("Employee", doc.employee, "user_id"),
		"leave_approver": doc.leave_approver,
		"leave_approver_name": doc.leave_approver_name,
		"leave_approver_image": _get_user_image(doc.leave_approver),
		"secondary_leave_approver": doc.custom_secondary_leave_approver,
		"secondary_approver_name": doc.custom_secondary_approver_name,
		"secondary_approver_image": _get_user_image(
			doc.custom_secondary_leave_approver
		),
	}
