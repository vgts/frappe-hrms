# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, get_link_to_form, getdate, time_diff_in_hours

import hrms
from hrms.hr.utils import (
	set_employee_name,
	share_doc_with_approver,
	validate_active_employee,
)


class AttendanceRegularization(Document):
	def validate(self):
		validate_active_employee(self.employee)
		set_employee_name(self)
		self.validate_times()
		self.calculate_total_hours()
		self.set_leave_approver()
		self.set_secondary_leave_approver()
		self.set_approval_stage()

	def validate_times(self):
		"""Validate that check-in time is before check-out time when both are provided."""
		if self.checkin_time and self.checkout_time:
			checkin = datetime.datetime.strptime(str(self.checkin_time), "%H:%M:%S")
			checkout = datetime.datetime.strptime(str(self.checkout_time), "%H:%M:%S")
			if checkin >= checkout:
				frappe.throw(_("Check-in Time must be before Check-out Time"))

		if self.reason in ("Forgot to Check-in", "Forgot Both") and not self.checkin_time:
			frappe.throw(_("Check-in Time is required for reason: {0}").format(self.reason))

		if self.reason in ("Forgot to Check-out", "Forgot Both") and not self.checkout_time:
			frappe.throw(_("Check-out Time is required for reason: {0}").format(self.reason))

	def calculate_total_hours(self):
		"""Calculate total hours between check-in and check-out times."""
		if self.checkin_time and self.checkout_time:
			checkin = datetime.datetime.strptime(str(self.checkin_time), "%H:%M:%S")
			checkout = datetime.datetime.strptime(str(self.checkout_time), "%H:%M:%S")
			diff = (checkout - checkin).total_seconds() / 3600.0
			self.total_hours = flt(diff, 2)
		else:
			self.total_hours = 0

	def set_leave_approver(self):
		"""Set leave approver from employee record if not already set."""
		if self.leave_approver:
			return

		leave_approver, department = frappe.db.get_value(
			"Employee", self.employee, ["leave_approver", "department"]
		)

		if not leave_approver and department:
			leave_approver = frappe.db.get_value(
				"Department Approver",
				{"parent": department, "parentfield": "leave_approvers", "idx": 1},
				"approver",
			)

		if leave_approver:
			self.leave_approver = leave_approver
			self.leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name")

	def on_update(self):
		share_doc_with_approver(self, self.leave_approver)
		self.publish_update()
		self.handle_secondary_approval_flow()

	def before_submit(self):
		"""Gate submission: only secondary approver (or normal flow without secondary) can submit."""
		if not self.custom_secondary_leave_approver:
			return

		user = frappe.session.user

		# Secondary approver submitting - mark fully approved and allow
		if (
			user == self.custom_secondary_leave_approver
			and self.custom_approval_stage == "Pending Secondary Reporting Approval"
		):
			self.custom_approval_stage = "Approved"
			return

		# Already fully approved or rejected by secondary
		if self.custom_approval_stage in ("Approved", "Rejected"):
			return

		# Anyone else - forward to secondary silently (revert docstatus so doc stays draft)
		if self.status == "Approved" and self.custom_approval_stage in (
			"Pending Project Reporting Approval",
			"Pending Secondary Reporting Approval",
		):
			if self.custom_approval_stage == "Pending Project Reporting Approval":
				self._forward_to_secondary()

			self.docstatus = 0
			frappe.msgprint(
				_("Attendance Regularization has been forwarded to {0} for final approval.").format(
					self.custom_secondary_approver_name or self.custom_secondary_leave_approver
				),
				title=_("Forwarded to Secondary Approver"),
				indicator="blue",
			)
			return

		frappe.throw(
			_("Attendance Regularization cannot be submitted at this stage: {0}").format(
				self.custom_approval_stage
			)
		)

	def on_submit(self):
		if self.status in ["Open", "Cancelled"]:
			frappe.throw(
				_("Only Attendance Regularizations with status 'Approved' or 'Rejected' can be submitted")
			)

		if self.status == "Approved":
			self.create_employee_checkin()
			self.create_attendance()

		self.publish_update()

	def on_cancel(self):
		self.cancel_attendance()
		self.delete_employee_checkin()
		self.publish_update()

	def before_cancel(self):
		self.status = "Cancelled"

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def after_delete(self):
		self.publish_update()

	def create_employee_checkin(self):
		"""Create Employee Checkin records based on the regularization reason."""
		if self.reason in ("Forgot to Check-in", "Forgot Both") and self.checkin_time:
			checkin_datetime = get_datetime(
				"{} {}".format(self.attendance_date, self.checkin_time)
			)
			checkin = frappe.new_doc("Employee Checkin")
			checkin.employee = self.employee
			checkin.log_type = "IN"
			checkin.time = checkin_datetime
			checkin.skip_auto_attendance = 1
			checkin.flags.ignore_permissions = True
			checkin.insert()
			checkin.add_comment("Info", _("Created via Attendance Regularization {0}").format(self.name))

		if self.reason in ("Forgot to Check-out", "Forgot Both") and self.checkout_time:
			checkout_datetime = get_datetime(
				"{} {}".format(self.attendance_date, self.checkout_time)
			)
			checkout = frappe.new_doc("Employee Checkin")
			checkout.employee = self.employee
			checkout.log_type = "OUT"
			checkout.time = checkout_datetime
			checkout.skip_auto_attendance = 1
			checkout.flags.ignore_permissions = True
			checkout.insert()
			checkout.add_comment("Info", _("Created via Attendance Regularization {0}").format(self.name))

	def create_attendance(self):
		"""Create or update Attendance record for the regularization date."""
		# Check if attendance already exists for this date
		existing = frappe.db.exists(
			"Attendance",
			{
				"employee": self.employee,
				"attendance_date": self.attendance_date,
				"docstatus": ("!=", 2),
			},
		)

		if existing:
			# Update existing attendance to Present
			att = frappe.get_doc("Attendance", existing)
			if att.docstatus == 1:
				# Already submitted — add comment linking to regularization
				att.add_comment("Info", _("Regularized via {0}").format(self.name))
			else:
				# Draft — update and submit
				att.status = "Present"
				att.attendance_request = None
				att.flags.ignore_permissions = True
				att.save()
				att.submit()
				att.add_comment("Info", _("Marked Present via Attendance Regularization {0}").format(self.name))
		else:
			# Create new attendance record
			company = frappe.db.get_value("Employee", self.employee, "company")
			att = frappe.new_doc("Attendance")
			att.employee = self.employee
			att.attendance_date = self.attendance_date
			att.status = "Present"
			att.company = company
			att.flags.ignore_permissions = True
			att.insert()
			att.submit()
			att.add_comment("Info", _("Created via Attendance Regularization {0}").format(self.name))

		# Store the attendance reference
		self.db_set("attendance", att.name)

	def cancel_attendance(self):
		"""Cancel attendance record created by this regularization."""
		if not self.attendance:
			return

		try:
			att = frappe.get_doc("Attendance", self.attendance)
			if att.docstatus == 1:
				att.flags.ignore_permissions = True
				att.cancel()
		except frappe.DoesNotExistError:
			pass

	def delete_employee_checkin(self):
		"""Delete Employee Checkin records created by this regularization (linked via comment)."""
		# Find checkins created for this date by this employee with skip_auto_attendance
		checkins = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": self.employee,
				"time": ("between", [
					"{} 00:00:00".format(self.attendance_date),
					"{} 23:59:59".format(self.attendance_date),
				]),
				"skip_auto_attendance": 1,
			},
			pluck="name",
		)
		# Only delete checkins that have our regularization comment
		for checkin_name in checkins:
			comments = frappe.get_all(
				"Comment",
				filters={
					"reference_doctype": "Employee Checkin",
					"reference_name": checkin_name,
					"content": ("like", "%{}%".format(self.name)),
				},
			)
			if comments:
				frappe.delete_doc("Employee Checkin", checkin_name, force=True, ignore_permissions=True)

	def publish_update(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id", cache=True)

		# Notify the employee
		if employee_user:
			hrms.refetch_resource("hrms:my_leaves", employee_user)

		# Notify the primary approver (project reporting)
		if self.leave_approver:
			hrms.refetch_resource("hrms:team_leaves", self.leave_approver)

		# Notify the secondary approver
		if self.custom_secondary_leave_approver:
			hrms.refetch_resource("hrms:team_leaves", self.custom_secondary_leave_approver)

	# ---- Two-level approval helpers ----

	def set_secondary_leave_approver(self):
		"""Auto-fetch secondary leave approver from employee master."""
		if self.custom_secondary_leave_approver or not self.employee:
			return

		# Check if the field exists on Employee before querying
		employee_meta = frappe.get_meta("Employee")
		if not employee_meta.has_field("custom_secondary_leave_approver"):
			return

		secondary = frappe.db.get_value(
			"Employee", self.employee, "custom_secondary_leave_approver"
		)
		if secondary:
			self.custom_secondary_leave_approver = secondary
			self.custom_secondary_approver_name = frappe.db.get_value(
				"User", secondary, "full_name"
			)

	def set_approval_stage(self):
		"""Set initial approval stage for new attendance regularizations."""
		if self.is_new() and self.custom_secondary_leave_approver:
			self.custom_approval_stage = "Pending Project Reporting Approval"

	def handle_secondary_approval_flow(self):
		"""On save: when leave approver approves, forward to secondary approver."""
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
		"""Move to secondary approval stage, share doc, and notify."""
		self.db_set("custom_approval_stage", "Pending Secondary Reporting Approval")
		self.custom_approval_stage = "Pending Secondary Reporting Approval"

		# Share with secondary approver for list visibility and submit access
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
		"""Send PWA notification to the secondary leave approver."""
		to_user = self.custom_secondary_leave_approver
		if not to_user or frappe.session.user == to_user:
			return

		# PWA notification
		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{frappe.bold(self.employee_name)}'s {frappe.bold('Attendance Regularization')} "
			f"{self.name} requires your secondary approval"
		)
		notification.from_user = frappe.session.user
		notification.to_user = to_user
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Two-level approval whitelisted methods
# ---------------------------------------------------------------------------


@frappe.whitelist()
def regularization_project_reporting_reject(attendance_regularization, reason=None):
	"""Project reporting (primary leave approver) rejects - set rejected, submit then cancel."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Attendance Regularization", attendance_regularization)

	if frappe.session.user != doc.leave_approver:
		frappe.throw(_("Only the Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Project Reporting Approval":
		frappe.throw(_("This attendance regularization is not pending project reporting approval."))

	if doc.docstatus != 0:
		frappe.throw(_("This attendance regularization has already been submitted."))

	# Set rejected status and stage
	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	# Cancel the submitted doc so it goes to Cancelled stage
	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	# Add rejection reason as a comment
	doc.add_comment(
		"Comment",
		_("Rejected by Project Reporting (Leave Approver): {0}").format(reason),
	)

	return {"status": "success", "message": _("Attendance Regularization rejected and cancelled.")}


@frappe.whitelist()
def regularization_secondary_approve(attendance_regularization):
	"""Secondary approver approves - set fully approved and auto-submit."""
	doc = frappe.get_doc("Attendance Regularization", attendance_regularization)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(_("This attendance regularization is not pending secondary approval."))

	if doc.status != "Approved":
		frappe.throw(
			_("Attendance Regularization must be approved by the primary Leave Approver first.")
		)

	doc.custom_approval_stage = "Approved"
	doc.flags.ignore_permissions = True
	doc.submit()

	return {"status": "success", "message": _("Attendance Regularization approved and submitted.")}


@frappe.whitelist()
def regularization_secondary_reject(attendance_regularization, reason=None):
	"""Secondary approver rejects - set rejected, submit then cancel so it goes to Cancelled."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc("Attendance Regularization", attendance_regularization)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Leave Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(_("This attendance regularization is not pending secondary approval."))

	# Set rejected status and stage
	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	# Cancel the submitted doc so it goes to Cancelled stage
	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	# Add rejection reason as a comment
	doc.add_comment("Comment", _("Rejected by Secondary Approver: {0}").format(reason))

	return {"status": "success", "message": _("Attendance Regularization rejected and cancelled.")}


@frappe.whitelist()
def get_regularization_approval_details(attendance_regularization):
	"""Return approval stage info with avatar details for the frontend."""
	doc = frappe.get_doc("Attendance Regularization", attendance_regularization)

	def _get_user_image(user_id):
		"""Get user image, fallback to employee image."""
		if not user_id:
			return None
		image = frappe.db.get_value("User", user_id, "user_image")
		if not image:
			# Fallback: get employee image by user_id
			image = frappe.db.get_value("Employee", {"user_id": user_id}, "image")
		return image

	return {
		"approval_stage": doc.custom_approval_stage,
		"leave_approver": doc.leave_approver,
		"leave_approver_name": doc.leave_approver_name,
		"leave_approver_image": _get_user_image(doc.leave_approver),
		"secondary_leave_approver": doc.custom_secondary_leave_approver,
		"secondary_approver_name": doc.custom_secondary_approver_name,
		"secondary_approver_image": _get_user_image(doc.custom_secondary_leave_approver),
	}


@frappe.whitelist()
def get_leave_approver(employee):
	"""Return the leave approver for an employee."""
	leave_approver, department = frappe.db.get_value(
		"Employee", employee, ["leave_approver", "department"]
	)

	if not leave_approver and department:
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	return leave_approver
