import json
import frappe
from frappe import _

# Cache the access token
_access_token_cache = {}


def get_fcm_settings():
	"""Get FCM settings from site config."""
	return {
		"service_account": frappe.conf.get("fcm_service_account"),  # path to service account JSON
		"project_id": frappe.conf.get("fcm_project_id"),
	}


def get_access_token():
	"""Get OAuth2 access token for FCM v1 API using service account."""
	import google.auth.transport.requests
	from google.oauth2 import service_account

	settings = get_fcm_settings()
	sa_path = settings.get("service_account")

	if not sa_path:
		frappe.log_error("FCM service account not configured in site_config", "FCM Error")
		return None

	SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

	credentials = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
	request = google.auth.transport.requests.Request()
	credentials.refresh(request)
	return credentials.token


def send_notification(user, title, body, data=None, link=None, icon=None):
	"""Send push notification to a user via FCM."""
	import requests as http_requests

	settings = get_fcm_settings()
	project_id = settings.get("project_id")

	if not project_id:
		return

	# Get all FCM tokens for this user
	tokens = frappe.get_all(
		"FCM Device Token",
		filters={"user": user},
		pluck="token",
	)

	if not tokens:
		return

	access_token = get_access_token()
	if not access_token:
		return

	url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/json",
	}

	notification_data = data or {}
	if link:
		notification_data["click_action"] = link
	if icon:
		notification_data["notification_icon"] = icon
	notification_data["title"] = title
	notification_data["body"] = body or ""

	for token in tokens:
		payload = {
			"message": {
				"token": token,
				"data": {k: str(v) for k, v in notification_data.items()},
			}
		}

		try:
			resp = http_requests.post(url, headers=headers, json=payload, timeout=10)
			if resp.status_code == 404 or (
				resp.status_code == 400 and "UNREGISTERED" in resp.text
			):
				# Token is invalid, remove it
				frappe.db.delete("FCM Device Token", {"token": token})
				frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"FCM send failed for token {token[:20]}...: {e}", "FCM Error")


def send_notification_to_user(user, title, body, link=None, icon=None, data=None):
	"""Convenience wrapper, enqueued for background execution."""
	frappe.enqueue(
		send_notification,
		user=user,
		title=title,
		body=body,
		data=data,
		link=link,
		icon=icon,
		queue="short",
		is_async=True,
	)
