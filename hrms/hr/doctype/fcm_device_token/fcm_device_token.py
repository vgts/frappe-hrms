import frappe
from frappe.model.document import Document


class FCMDeviceToken(Document):
	def validate(self):
		# Check if this token already exists for a different record
		existing = frappe.db.exists(
			"FCM Device Token",
			{"token": self.token, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				frappe._("This FCM token is already registered."),
				frappe.DuplicateEntryError,
			)
