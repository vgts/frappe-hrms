# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import bold


class PWANotificationsMixin:
	"""Mixin class for managing PWA updates"""

	def notify_approval_status(self):
		"""Send approval status notification to the employee"""
		status_field = self._get_doc_status_field()
		if not status_field:
			return

		status = self.get(status_field)

		if self.has_value_changed(status_field) and status in ["Approved", "Rejected"]:
			from_user = frappe.session.user
			from_user_name = self._get_user_name(from_user)
			to_user = self._get_employee_user()

			if from_user == to_user:
				return

			notification = frappe.new_doc("PWA Notification")
			notification.from_user = from_user
			notification.to_user = to_user
			notification.message = f"{bold('Your')} {bold(self.doctype)} {self.name} has been {bold(status)} by {bold(from_user_name)}"
			notification.reference_document_type = self.doctype
			notification.reference_document_name = self.name
			notification.insert(ignore_permissions=True)

			self._trigger_notification_count_refetch(to_user)

	def notify_approver(self):
		"""Send new request notification to the approver"""
		from_user = self._get_employee_user()
		to_user = self._get_doc_approver()

		if not to_user or from_user == to_user:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{bold(self.employee_name)} raised a new {bold(self.doctype)} for approval: {self.name}"
		)
		notification.from_user = from_user
		notification.to_user = to_user
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

		self._trigger_notification_count_refetch(to_user)

	def _trigger_notification_count_refetch(self, user):
		"""Push a realtime event so the bell icon updates immediately"""
		try:
			import hrms
			hrms.refetch_resource("hrms:unread_notifications_count", user)
		except Exception:
			pass

	def _get_doc_status_field(self) -> str | None:
		APPROVAL_STATUS_FIELD = {
			"Leave Application": "status",
			"Employee Permission": "status",
			"Expense Claim": "approval_status",
			"Shift Request": "status",
		}
		return APPROVAL_STATUS_FIELD.get(self.doctype)

	def _get_doc_approver(self) -> str:
		APPROVER_FIELD = {
			"Leave Application": "leave_approver",
			"Employee Permission": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver",
		}
		approver_field = APPROVER_FIELD.get(self.doctype)
		return self.get(approver_field) if approver_field else None

	def _get_employee_user(self) -> str:
		return frappe.db.get_value("Employee", self.employee, "user_id", cache=True)

	def _get_user_name(self, user) -> str:
		return frappe.db.get_value("User", user, "full_name", cache=True)
