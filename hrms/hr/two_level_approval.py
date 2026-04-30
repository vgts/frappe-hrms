"""
Reusable two-level approval helpers for Leave Application, Attendance Request, Shift Request.

Every doctype that uses this must have:
  - approver field  (leave_approver or approver)
  - status field    (Open/Draft → Approved/Rejected)
  - custom_secondary_leave_approver   (Link → User, read_only)
  - custom_secondary_approver_name    (Data, read_only)
  - custom_approval_stage             (Select, read_only)
"""

import frappe
from frappe import _

from hrms.hr.utils import share_doc_with_approver


# ---------------------------------------------------------------------------
# Helpers to resolve the approver field name per doctype
# ---------------------------------------------------------------------------

def _approver_field(doc):
	"""Return the field name that stores the primary approver."""
	if doc.doctype == "Leave Application":
		return "leave_approver"
	return "approver"


# ---------------------------------------------------------------------------
# Validate / auto-populate (call from doc.validate)
# ---------------------------------------------------------------------------

def set_secondary_approver(doc):
	"""Auto-fetch secondary approver from employee.custom_secondary_reporting_ → user_id."""
	if doc.custom_secondary_leave_approver or not doc.get("employee"):
		return

	secondary_emp = frappe.db.get_value("Employee", doc.employee, "custom_secondary_reporting_")
	if secondary_emp:
		user_id = frappe.db.get_value("Employee", secondary_emp, "user_id")
		if user_id:
			doc.custom_secondary_leave_approver = user_id
			doc.custom_secondary_approver_name = frappe.db.get_value("User", user_id, "full_name")


def set_approval_stage(doc):
	"""Set initial approval stage for new documents."""
	if doc.is_new() and doc.custom_secondary_leave_approver:
		doc.custom_approval_stage = "Pending Project Reporting Approval"


# ---------------------------------------------------------------------------
# On-update helpers (call from doc.on_update)
# ---------------------------------------------------------------------------

def handle_secondary_approval_flow(doc):
	"""When primary approver approves, forward to secondary approver."""
	if doc.docstatus != 0:
		return

	status_field = "status"
	approved_value = "Approved"

	if not (
		doc.has_value_changed(status_field)
		and doc.get(status_field) == approved_value
		and doc.custom_approval_stage == "Pending Project Reporting Approval"
		and doc.custom_secondary_leave_approver
	):
		return

	_forward_to_secondary(doc)


def _forward_to_secondary(doc):
	"""Move to secondary approval stage, share doc, and notify."""
	doc.db_set("custom_approval_stage", "Pending Secondary Reporting Approval")
	doc.custom_approval_stage = "Pending Secondary Reporting Approval"

	# Share with secondary approver
	frappe.share.add_docshare(
		doc.doctype,
		doc.name,
		doc.custom_secondary_leave_approver,
		write=1,
		submit=1,
		flags={"ignore_share_permission": True},
	)

	_notify_secondary_approver(doc)


def _notify_secondary_approver(doc):
	"""Send PWA notification to the secondary approver."""
	to_user = doc.custom_secondary_leave_approver
	if not to_user or frappe.session.user == to_user:
		return

	try:
		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{frappe.bold(doc.employee_name)}'s {frappe.bold(doc.doctype)} "
			f"{doc.name} requires your secondary approval"
		)
		notification.from_user = frappe.session.user
		notification.to_user = to_user
		notification.reference_document_type = doc.doctype
		notification.reference_document_name = doc.name
		notification.insert(ignore_permissions=True)
	except Exception:
		pass


def is_pending_secondary(doc):
	return (
		doc.custom_secondary_leave_approver
		and doc.custom_approval_stage in (
			"Pending Project Reporting Approval",
			"Pending Secondary Reporting Approval",
		)
	)


# ---------------------------------------------------------------------------
# Before-submit gate (call from doc.before_submit)
# ---------------------------------------------------------------------------

def gate_submission(doc):
	"""Gate submission: only secondary approver (or normal flow without secondary) can submit."""
	if not doc.custom_secondary_leave_approver:
		return

	user = frappe.session.user

	# Secondary approver submitting — mark fully approved and allow
	if (
		user == doc.custom_secondary_leave_approver
		and doc.custom_approval_stage == "Pending Secondary Reporting Approval"
	):
		doc.custom_approval_stage = "Approved"
		return

	# Already fully approved or rejected by secondary
	if doc.custom_approval_stage in ("Approved", "Rejected"):
		return

	# Anyone else — forward to secondary silently (revert docstatus so doc stays draft)
	if doc.get("status") == "Approved" and doc.custom_approval_stage in (
		"Pending Project Reporting Approval",
		"Pending Secondary Reporting Approval",
	):
		if doc.custom_approval_stage == "Pending Project Reporting Approval":
			_forward_to_secondary(doc)

		doc.docstatus = 0
		frappe.msgprint(
			_("{0} has been forwarded to {1} for final approval.").format(
				doc.doctype,
				doc.custom_secondary_approver_name or doc.custom_secondary_leave_approver,
			),
			title=_("Forwarded to Secondary Approver"),
			indicator="blue",
		)
		return

	frappe.throw(
		_("{0} cannot be submitted at this stage: {1}").format(
			doc.doctype, doc.custom_approval_stage
		)
	)


# ---------------------------------------------------------------------------
# Whitelisted API helpers  (generic — works for any doctype)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def primary_reject(doctype, docname, reason=None):
	"""Primary approver rejects — set rejected, submit then cancel."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc(doctype, docname)
	approver = doc.get(_approver_field(doc))

	if frappe.session.user != approver:
		frappe.throw(_("Only the Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Project Reporting Approval":
		frappe.throw(_("This {0} is not pending project reporting approval.").format(doctype))

	if doc.docstatus != 0:
		frappe.throw(_("This {0} has already been submitted.").format(doctype))

	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment("Comment", _("Rejected by Project Reporting (Approver): {0}").format(reason))

	return {"status": "success", "message": _("{0} rejected and cancelled.").format(doctype)}


@frappe.whitelist()
def secondary_approve(doctype, docname):
	"""Secondary approver approves — set fully approved and auto-submit."""
	doc = frappe.get_doc(doctype, docname)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(_("This {0} is not pending secondary approval.").format(doctype))

	if doc.status != "Approved":
		frappe.throw(_("{0} must be approved by the primary Approver first.").format(doctype))

	doc.custom_approval_stage = "Approved"
	doc.flags.ignore_permissions = True
	doc.submit()

	return {"status": "success", "message": _("{0} approved and submitted.").format(doctype)}


@frappe.whitelist()
def secondary_reject(doctype, docname, reason=None):
	"""Secondary approver rejects — set rejected, submit then cancel."""
	if not reason:
		frappe.throw(_("Please provide a reason for rejection."))

	doc = frappe.get_doc(doctype, docname)

	if frappe.session.user != doc.custom_secondary_leave_approver:
		frappe.throw(_("Only the Secondary Approver can perform this action."))

	if doc.custom_approval_stage != "Pending Secondary Reporting Approval":
		frappe.throw(_("This {0} is not pending secondary approval.").format(doctype))

	doc.status = "Rejected"
	doc.custom_approval_stage = "Rejected"
	doc.flags.ignore_permissions = True
	doc.submit()

	doc.reload()
	doc.flags.ignore_permissions = True
	doc.cancel()

	doc.add_comment("Comment", _("Rejected by Secondary Approver: {0}").format(reason))

	return {"status": "success", "message": _("{0} rejected and cancelled.").format(doctype)}


@frappe.whitelist()
def force_approve_all_pending(doctype=None, from_date=None, to_date=None):
	"""
	Admin-only: bulk approve all pending requests bypassing the approver user check.
	Approves both Stage 1 (Pending Project Reporting) and Stage 2 (Pending Secondary Reporting).

	Called by the MCP via:
	    POST /api/method/hrms.hr.two_level_approval.force_approve_all_pending
	    body: {"doctype": "Attendance Request", "from_date": "2026-04-01", "to_date": "2026-04-30"}
	    (doctype=None → processes both Leave Application and Attendance Request)
	"""
	if not any(r in frappe.get_roles() for r in ("HR Manager", "HR User", "System Manager")):
		frappe.throw("Only HR Manager / System Manager can use force approve.", frappe.PermissionError)

	doctypes = [doctype] if doctype else ["Leave Application", "Attendance Request"]
	processed = []; skipped = []; errors = []

	for dt in doctypes:
		filters = {"docstatus": 0}
		if from_date:
			filters["from_date"] = [">=", from_date]
		if to_date:
			filters["to_date"] = ["<=", to_date]

		pending = frappe.db.get_all(
			dt,
			filters=filters,
			fields=["name", "employee_name", "status", "custom_approval_stage",
			        "custom_secondary_leave_approver"],
			limit=0,
		)

		for rec in pending:
			name  = rec["name"]
			stage = rec.get("custom_approval_stage") or ""
			try:
				doc = frappe.get_doc(dt, name)

				# Stage 1: forward to secondary if not yet done
				if stage == "Pending Project Reporting Approval":
					if doc.custom_secondary_leave_approver:
						doc.db_set("custom_approval_stage", "Pending Secondary Reporting Approval")
						doc.custom_approval_stage = "Pending Secondary Reporting Approval"
						frappe.share.add_docshare(
							dt, name, doc.custom_secondary_leave_approver,
							write=1, submit=1,
							flags={"ignore_share_permission": True},
						)
					# Fall through to Stage 2 submission below

				# Stage 2: mark fully approved and submit
				doc.reload()
				doc.status            = "Approved"
				doc.custom_approval_stage = "Approved"
				doc.flags.ignore_permissions = True
				doc.flags.ignore_validate_update_after_submit = True
				doc.submit()

				processed.append({
					"doctype":  dt,
					"name":     name,
					"employee": rec.get("employee_name"),
					"from_stage": stage,
				})

			except Exception as exc:
				errors.append({
					"doctype": dt, "name": name,
					"employee": rec.get("employee_name"),
					"error": str(exc)[:200],
				})

	frappe.db.commit()

	return {
		"processed_count": len(processed),
		"skipped_count":   len(skipped),
		"error_count":     len(errors),
		"processed":       processed,
		"errors":          errors,
	}


@frappe.whitelist()
def get_approval_details(doctype, docname):
	"""Return approval stage info with avatar details for the frontend."""
	doc = frappe.get_doc(doctype, docname)
	approver_field = _approver_field(doc)

	def _get_user_image(user_id):
		if not user_id:
			return None
		image = frappe.db.get_value("User", user_id, "user_image")
		if not image:
			image = frappe.db.get_value("Employee", {"user_id": user_id}, "image")
		return image

	approver = doc.get(approver_field)
	approver_name = doc.get(approver_field + "_name") if doc.meta.has_field(approver_field + "_name") else (
		frappe.db.get_value("User", approver, "full_name") if approver else ""
	)

	return {
		"approval_stage": doc.custom_approval_stage,
		"approver": approver,
		"approver_name": approver_name,
		"approver_image": _get_user_image(approver),
		"secondary_leave_approver": doc.custom_secondary_leave_approver,
		"secondary_approver_name": doc.custom_secondary_approver_name,
		"secondary_approver_image": _get_user_image(doc.custom_secondary_leave_approver),
	}


def is_current_user_doc_employee(employee: str) -> bool:
	"""True if the logged-in user's active Employee matches doc.employee (same rule as PWA session)."""
	if not employee:
		return False
	curr_emp = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
	)
	return bool(curr_emp and curr_emp == employee)
