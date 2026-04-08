// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Compensatory Leave Request", {
	refresh: function (frm) {
		frm.set_query("leave_type", function () {
			return {
				filters: {
					is_compensatory: true,
				},
			};
		});

		// Hide secondary approval section if no secondary approver
		clr_toggle_approval_section(frm);

		// Show stage tracker
		clr_show_approval_stage_tracker(frm);

		// Show approve/reject buttons for approvers
		clr_handle_secondary_approval(frm);
	},

	half_day: function (frm) {
		if (frm.doc.half_day == 1) {
			frm.set_df_property("half_day_date", "reqd", true);
		} else {
			frm.set_df_property("half_day_date", "reqd", false);
		}
	},
});

// ---------------------------------------------------------------------------
// Hide secondary approval section when no secondary approver is configured
// ---------------------------------------------------------------------------

function clr_toggle_approval_section(frm) {
	const hasSecondaryApprover = !!frm.doc.custom_secondary_leave_approver;
	frm.toggle_display("custom_secondary_leave_approver", hasSecondaryApprover);
	frm.toggle_display("custom_secondary_approver_name", hasSecondaryApprover);
	frm.toggle_display("custom_approval_stage", hasSecondaryApprover);
}

// ---------------------------------------------------------------------------
// Two-level approval: stage tracker with avatars
// ---------------------------------------------------------------------------

function clr_show_approval_stage_tracker(frm) {
	if (!frm.doc.custom_approval_stage || frm.is_new()) return;

	frappe.call({
		method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.get_compensatory_approval_details",
		args: { compensatory_leave_request: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const d = r.message;
			const stage = d.approval_stage;

			const getAvatar = (name, image) => {
				if (image) return `<img src="${image}" class="avatar avatar-small" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" title="${frappe.utils.escape_html(name || "")}">`;
				const initials = (name || "?").split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
				return `<div style="width:32px;height:32px;border-radius:50%;background:#d1d5db;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#374151;" title="${frappe.utils.escape_html(name || "")}">${initials}</div>`;
			};

			const stageColor = {
				"Pending Project Reporting Approval": { approver: "orange", secondary: "gray" },
				"Pending Secondary Reporting Approval": { approver: "green", secondary: "orange" },
				"Approved": { approver: "green", secondary: "green" },
				"Rejected": { approver: "red", secondary: "gray" },
			};
			const colors = stageColor[stage] || { approver: "gray", secondary: "gray" };

			const approverCheck = colors.approver === "green" ? "✓" : (colors.approver === "orange" ? "●" : "○");
			const secondaryCheck = colors.secondary === "green" ? "✓" : (colors.secondary === "red" ? "✗" : (colors.secondary === "orange" ? "●" : "○"));
			const lineColor = colors.secondary === "green" ? "#22c55e" : (colors.secondary === "red" ? "#ef4444" : "#d1d5db");

			const html = `
				<div class="clr-approval-stage-tracker" style="display:flex;align-items:center;gap:8px;padding:12px 0;">
					<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
						${getAvatar(d.approver_name, d.approver_image)}
						<span style="font-size:11px;color:#374151;text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${frappe.utils.escape_html(d.approver_name || "Approver")}</span>
						<span style="font-size:18px;color:${colors.approver === "green" ? "#22c55e" : (colors.approver === "orange" ? "#f59e0b" : "#9ca3af")}">${approverCheck}</span>
					</div>
					<div style="flex:1;height:2px;background:${lineColor};min-width:40px;"></div>
					<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
						${getAvatar(d.secondary_approver_name, d.secondary_approver_image)}
						<span style="font-size:11px;color:#374151;text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${frappe.utils.escape_html(d.secondary_approver_name || "Secondary Approver")}</span>
						<span style="font-size:18px;color:${colors.secondary === "green" ? "#22c55e" : (colors.secondary === "red" ? "#ef4444" : (colors.secondary === "orange" ? "#f59e0b" : "#9ca3af"))}">${secondaryCheck}</span>
					</div>
				</div>
			`;

			$(frm.fields_dict.custom_secondary_leave_approver?.wrapper)
				.closest(".form-section")
				.find(".clr-approval-stage-tracker").remove();

			frm.dashboard.add_section(html, __("Approval Progress"));
		},
	});
}

// ---------------------------------------------------------------------------
// Approve / Reject buttons for primary and secondary approvers
// ---------------------------------------------------------------------------

function clr_handle_secondary_approval(frm) {
	if (frm.doc.docstatus !== 0) return;

	const hasSecondary = !!frm.doc.custom_secondary_leave_approver;
	const stage = frm.doc.custom_approval_stage;
	const isPrimary = frappe.session.user === frm.doc.approver;
	const isSecondary = frappe.session.user === frm.doc.custom_secondary_leave_approver;

	// ── Secondary approver: final approval ──────────────────────────────────
	if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
		frm.page.btn_primary.hide();

		frm.dashboard.set_headline(
			`<span class="indicator-pill yellow">${__("Waiting for your approval")}</span>`
		);

		frm.add_custom_button(__("Approve & Submit"), () => {
			frappe.confirm(__("Approve and submit this Compensatory Leave Request?"), () => {
				frappe.call({
					method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_secondary_approve",
					args: { compensatory_leave_request: frm.doc.name },
					freeze: true,
					freeze_message: __("Approving..."),
					callback(r) {
						if (r.message && r.message.status === "success") {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			});
		}, __("Secondary Approver"));

		frm.add_custom_button(__("Reject"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Reject Compensatory Leave Request"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_secondary_reject",
						args: { compensatory_leave_request: frm.doc.name, reason: values.reason },
						freeze: true,
						freeze_message: __("Rejecting..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		}, __("Secondary Approver"));

		frm.change_custom_button_type(__("Approve & Submit"), __("Secondary Approver"), "primary");
		frm.change_custom_button_type(__("Reject"), __("Secondary Approver"), "danger");
		return;
	}

	// Hide submit for two-level flows waiting on secondary
	if (hasSecondary && stage === "Pending Secondary Reporting Approval" && !isSecondary) {
		frm.page.btn_primary.hide();
		frm.disable_save();
	}

	// ── Primary approver: approve (forward) + reject ─────────────────────────
	if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimary) {
		frm.add_custom_button(__("Approve"), () => {
			frappe.confirm(__("Approve and forward to secondary approver?"), () => {
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Compensatory Leave Request",
						name: frm.doc.name,
						fieldname: "status",
						value: "Approved",
					},
					freeze: true,
					freeze_message: __("Approving..."),
					callback(r) {
						if (!r.exc) {
							frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
							frm.reload_doc();
						}
					},
				});
			});
		}, __("Leave Approver"));

		frm.add_custom_button(__("Reject"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Reject Compensatory Leave Request"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_project_reporting_reject",
						args: { compensatory_leave_request: frm.doc.name, reason: values.reason },
						freeze: true,
						freeze_message: __("Rejecting..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		}, __("Leave Approver"));

		frm.change_custom_button_type(__("Approve"), __("Leave Approver"), "primary");
		frm.change_custom_button_type(__("Reject"), __("Leave Approver"), "danger");
	}

	// ── Single-level: primary approver only (no secondary) ──────────────────
	if (!hasSecondary && isPrimary && frm.doc.status === "Open") {
		frm.add_custom_button(__("Approve"), () => {
			frappe.confirm(__("Approve this Compensatory Leave Request?"), () => {
				frappe.call({
					method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_approve_submit",
					args: { compensatory_leave_request: frm.doc.name },
					freeze: true,
					freeze_message: __("Approving..."),
					callback(r) {
						if (r.message && r.message.status === "success") {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			});
		}, __("Leave Approver"));

		frm.add_custom_button(__("Reject"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Reject Compensatory Leave Request"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_reject_submit",
						args: { compensatory_leave_request: frm.doc.name, reason: values.reason },
						freeze: true,
						freeze_message: __("Rejecting..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		}, __("Leave Approver"));

		frm.change_custom_button_type(__("Approve"), __("Leave Approver"), "primary");
		frm.change_custom_button_type(__("Reject"), __("Leave Approver"), "danger");
	}
}
