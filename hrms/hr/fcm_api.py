import frappe
from frappe import _


@frappe.whitelist()
def register_fcm_token(token, device_name=None):
	"""Register an FCM token for the current user."""
	if not token:
		frappe.throw(_("Token is required"))

	user = frappe.session.user

	# Check if token already exists
	existing = frappe.db.exists("FCM Device Token", {"token": token})
	if existing:
		# Update user if different
		frappe.db.set_value("FCM Device Token", existing, "user", user)
		return {"status": "updated"}

	doc = frappe.get_doc(
		{
			"doctype": "FCM Device Token",
			"user": user,
			"token": token,
			"device_name": device_name or "",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "registered"}


@frappe.whitelist()
def unregister_fcm_token(token):
	"""Remove an FCM token."""
	if not token:
		frappe.throw(_("Token is required"))

	frappe.db.delete("FCM Device Token", {"token": token, "user": frappe.session.user})
	frappe.db.commit()
	return {"status": "unregistered"}
