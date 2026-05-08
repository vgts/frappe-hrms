# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

import hrms


class PWANotification(Document):
	def on_update(self):
		hrms.refetch_resource("hrms:notifications", self.to_user)

	def after_insert(self):
		self.send_push_notification()

	def send_push_notification(self):
		try:
			from frappe.push_notification import PushNotification

			push_notification = PushNotification("hrms")
			if push_notification.is_enabled():
				push_notification.send_notification_to_user(
					self.to_user,
					self.reference_document_type,
					self.message,
					link=self.get_notification_link(),
					icon=f"{frappe.utils.get_url()}/assets/hrms/manifest/favicon-196.png",
				)
		except ImportError:
			# push notifications are not supported in the current framework version
			pass
		except Exception:
			self.log_error(f"Error sending push notification: {self.name}")

	def get_notification_link(self):
		base_url = f"{frappe.utils.get_url()}/hrms"

		route_map = {
			"Leave Application":           f"{base_url}/leave-applications/{self.reference_document_name}",
			"Expense Claim":               f"{base_url}/expense-claims/{self.reference_document_name}",
			"Attendance Request":          f"{base_url}/attendance-requests/{self.reference_document_name}",
			"Shift Request":               f"{base_url}/shift-requests/{self.reference_document_name}",
			"Employee Permission":         f"{base_url}/employee-permissions/{self.reference_document_name}",
			"Attendance Regularization":   f"{base_url}/attendance-regularization/{self.reference_document_name}",
			"Compensatory Leave Request":  f"{base_url}/compensatory-leave/{self.reference_document_name}",
		}

		return route_map.get(self.reference_document_type, base_url)
