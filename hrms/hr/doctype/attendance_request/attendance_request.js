// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on("Attendance Request", {
	setup(frm) {
		frm.set_query("approver", function () {
			return {
				query: "hrms.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: "Leave Application",
				},
			};
		});
		frm.set_query("employee", erpnext.queries.employee);
	},

	refresh(frm) {
		frm.trigger("show_attendance_warnings");

		const hasSecondary = !!frm.doc.custom_secondary_leave_approver;
		frm.toggle_display("custom_secondary_approval_section", hasSecondary);
		frm.toggle_display("custom_secondary_leave_approver", hasSecondary);
		frm.toggle_display("custom_secondary_approver_name", hasSecondary);
		frm.toggle_display("custom_approval_stage", hasSecondary);

		hrms_show_approval_tracker(frm, "Attendance Request");
		hrms_handle_secondary_buttons(frm, "Attendance Request");
	},

	employee(frm) {
		frm.trigger("set_approver");
	},

	set_approver(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_approver",
				args: { employee: frm.doc.employee },
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("approver", r.message);
					}
				},
			});
		}
	},

	show_attendance_warnings(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.dashboard.clear_headline();

			frm.call("get_attendance_warnings").then((r) => {
				if (r.message?.length) {
					frm.dashboard.reset();
					frm.dashboard.add_section(
						frappe.render_template("attendance_warnings", {
							warnings: r.message || [],
						}),
						__("Attendance Warnings"),
					);
					frm.dashboard.show();
				}
			});
		}
	},
});


// ── Two-level approval: stage tracker ─────────────────────────────────────
function hrms_show_approval_tracker(frm, doctype) {
	if (!frm.doc.custom_approval_stage || frm.is_new()) return;

	frappe.call({
		method: "hrms.hr.two_level_approval.get_approval_details",
		args: { doctype: doctype, docname: frm.doc.name },
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
				<div class="approval-stage-tracker" style="display:flex;align-items:center;gap:8px;padding:12px 0;">
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

			$(frm.fields_dict.custom_secondary_approval_section?.wrapper)
				.find(".approval-stage-tracker").remove();

			if (frm.fields_dict.custom_secondary_approval_section) {
				$(frm.fields_dict.custom_secondary_approval_section.wrapper).prepend(html);
			} else {
				frm.dashboard.add_section(html);
			}
		},
	});
}


// ── Two-level approval: action buttons ────────────────────────────────────
function hrms_handle_secondary_buttons(frm, doctype) {
	if (frm.doc.docstatus !== 0 || !frm.doc.custom_secondary_leave_approver) return;

	const isSecondary = frappe.session.user === frm.doc.custom_secondary_leave_approver;
	const stage = frm.doc.custom_approval_stage;

	if (stage === "Pending Secondary Reporting Approval" && !isSecondary) {
		frm.page.btn_primary.hide();
		frm.disable_save();
	}

	if (frm.doc.status === "Approved" && !isSecondary && stage !== "Approved") {
		frm.page.btn_primary.hide();
	}

	const isPrimaryApprover = frappe.session.user === frm.doc.approver;
	if (stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject " + doctype),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.two_level_approval.primary_reject",
						args: { doctype: doctype, docname: frm.doc.name, reason: values.reason },
						freeze: true,
						callback(r) {
							if (r.message?.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		}, __("Approver"));
		frm.change_custom_button_type(__("Reject"), __("Approver"), "danger");
	}

	if (stage === "Pending Secondary Reporting Approval" && isSecondary) {
		frm.page.btn_primary.hide();
		frm.dashboard.set_headline(`<span class="indicator-pill yellow">Waiting for your approval</span>`);

		frm.add_custom_button(__("Approve & Submit"), () => {
			frappe.confirm(__("Approve and submit this " + doctype + "?"), () => {
				frappe.call({
					method: "hrms.hr.two_level_approval.secondary_approve",
					args: { doctype: doctype, docname: frm.doc.name },
					freeze: true,
					callback(r) {
						if (r.message?.status === "success") {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			});
		}, __("Secondary Approver"));

		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject " + doctype),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.two_level_approval.secondary_reject",
						args: { doctype: doctype, docname: frm.doc.name, reason: values.reason },
						freeze: true,
						callback(r) {
							if (r.message?.status === "success") {
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
	}
}
