// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on("Attendance Request", {
	setup(frm) {
		frm.set_query("approver", function () {
			return { filters: { enabled: 1 } };
		});
		frm.set_query("employee", erpnext.queries.employee);
	},

	async refresh(frm) {
		if (frm.is_new()) {
			frm.trigger("set_employee");
		}

		frm.trigger("show_attendance_warnings");

		// Determine if current user is employee, approver, or secondary
		const emp_user = frm.doc.employee
			? (await frappe.db.get_value("Employee", frm.doc.employee, "user_id")).message?.user_id
			: null;
		const is_employee = emp_user === frappe.session.user;
		const is_approver = frappe.session.user === frm.doc.approver;
		const is_secondary = frappe.session.user === frm.doc.custom_secondary_leave_approver;
		const is_hr = frappe.user_roles.some(r => ["HR Manager", "HR User", "System Manager"].includes(r));

		// Employee: hide status, make content editable
		// Approver: show status, make content read-only, show approve/reject
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			if (is_employee && !is_approver && !is_hr) {
				frm.set_df_property("status", "hidden", 1);
			}

			if ((is_approver || is_secondary || is_hr) && !is_employee) {
				// Lock content fields for approver
				["employee", "from_date", "to_date", "half_day", "half_day_date",
				 "reason", "explanation", "shift", "include_holidays"].forEach(f => {
					frm.set_df_property(f, "read_only", 1);
				});
				// Show status for approver to change
				frm.set_df_property("status", "hidden", 0);
				frm.set_df_property("approval_section", "hidden", 0);
			}
		}

		// Show two-level approval UI
		_att_show_approval_tracker(frm);
		_att_handle_secondary_buttons(frm, is_approver, is_secondary);
	},

	async set_employee(frm) {
		if (frm.doc.employee) return;
		const employee = await hrms.get_current_employee(frm);
		if (employee) frm.set_value("employee", employee);
	},

	employee(frm) {
		frm.trigger("set_approver");
	},

	set_approver(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_approver",
				args: { employee: frm.doc.employee },
				callback(r) {
					if (r && r.message) frm.set_value("approver", r.message);
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


// ── Approval stage tracker ────────────────────────────────────────────────
function _att_show_approval_tracker(frm) {
	if (!frm.doc.custom_approval_stage || frm.is_new()) return;

	frappe.call({
		method: "hrms.hr.two_level_approval.get_approval_details",
		args: { doctype: "Attendance Request", docname: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const d = r.message;
			const stage = d.approval_stage;

			const getAvatar = (name, image) => {
				if (image) return `<img src="${image}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" title="${frappe.utils.escape_html(name || "")}">`;
				const initials = (name || "?").split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
				return `<div style="width:32px;height:32px;border-radius:50%;background:#d1d5db;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#374151;" title="${frappe.utils.escape_html(name || "")}">${initials}</div>`;
			};

			const sc = {
				"Pending Project Reporting Approval": { a: "orange", s: "gray" },
				"Pending Secondary Reporting Approval": { a: "green", s: "orange" },
				"Approved": { a: "green", s: "green" },
				"Rejected": { a: "red", s: "gray" },
			};
			const c = sc[stage] || { a: "gray", s: "gray" };
			const ac = c.a === "green" ? "✓" : c.a === "orange" ? "●" : "○";
			const sc2 = c.s === "green" ? "✓" : c.s === "red" ? "✗" : c.s === "orange" ? "●" : "○";
			const lc = c.s === "green" ? "#22c55e" : c.s === "red" ? "#ef4444" : "#d1d5db";

			const html = `
			<div class="approval-stage-tracker" style="display:flex;align-items:center;gap:8px;padding:12px 0;margin-bottom:12px;">
				<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
					${getAvatar(d.approver_name, d.approver_image)}
					<span style="font-size:11px;color:#374151;text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${frappe.utils.escape_html(d.approver_name || "Approver")}</span>
					<span style="font-size:18px;color:${c.a === "green" ? "#22c55e" : c.a === "orange" ? "#f59e0b" : "#9ca3af"}">${ac}</span>
				</div>
				<div style="flex:1;height:2px;background:${lc};min-width:40px;"></div>
				<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
					${getAvatar(d.secondary_approver_name, d.secondary_approver_image)}
					<span style="font-size:11px;color:#374151;text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${frappe.utils.escape_html(d.secondary_approver_name || "Secondary Approver")}</span>
					<span style="font-size:18px;color:${c.s === "green" ? "#22c55e" : c.s === "red" ? "#ef4444" : c.s === "orange" ? "#f59e0b" : "#9ca3af"}">${sc2}</span>
				</div>
			</div>`;

			frm.dashboard.add_section(html);
		},
	});
}


// ── Approval action buttons ───────────────────────────────────────────────
function _att_handle_secondary_buttons(frm, is_approver, is_secondary) {
	if (frm.doc.docstatus !== 0 || !frm.doc.custom_secondary_leave_approver) return;
	const stage = frm.doc.custom_approval_stage;

	// Hide submit when pending secondary and user is not secondary
	if (stage === "Pending Secondary Reporting Approval" && !is_secondary) {
		frm.page.btn_primary.hide();
		frm.disable_save();
	}
	if (frm.doc.status === "Approved" && !is_secondary && stage !== "Approved") {
		frm.page.btn_primary.hide();
	}

	// Primary approver: reject button
	if (stage === "Pending Project Reporting Approval" && is_approver) {
		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject Attendance Request"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(v) {
					d.hide();
					frappe.call({
						method: "hrms.hr.two_level_approval.primary_reject",
						args: { doctype: "Attendance Request", docname: frm.doc.name, reason: v.reason },
						freeze: true,
						callback(r) { if (r.message?.status === "success") { frappe.show_alert({ message: r.message.message, indicator: "red" }); frm.reload_doc(); } },
					});
				},
			});
			d.show();
		}, __("Approver"));
		frm.change_custom_button_type(__("Reject"), __("Approver"), "danger");
	}

	// Secondary approver: approve + reject buttons
	if (stage === "Pending Secondary Reporting Approval" && is_secondary) {
		frm.page.btn_primary.hide();
		frm.dashboard.set_headline(`<span class="indicator-pill yellow">Waiting for your approval</span>`);

		frm.add_custom_button(__("Approve & Submit"), () => {
			frappe.confirm(__("Approve and submit this Attendance Request?"), () => {
				frappe.call({
					method: "hrms.hr.two_level_approval.secondary_approve",
					args: { doctype: "Attendance Request", docname: frm.doc.name },
					freeze: true,
					callback(r) { if (r.message?.status === "success") { frappe.show_alert({ message: r.message.message, indicator: "green" }); frm.reload_doc(); } },
				});
			});
		}, __("Secondary Approver"));

		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject Attendance Request"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
				primary_action_label: __("Reject"),
				primary_action(v) {
					d.hide();
					frappe.call({
						method: "hrms.hr.two_level_approval.secondary_reject",
						args: { doctype: "Attendance Request", docname: frm.doc.name, reason: v.reason },
						freeze: true,
						callback(r) { if (r.message?.status === "success") { frappe.show_alert({ message: r.message.message, indicator: "red" }); frm.reload_doc(); } },
					});
				},
			});
			d.show();
		}, __("Secondary Approver"));

		frm.change_custom_button_type(__("Approve & Submit"), __("Secondary Approver"), "primary");
		frm.change_custom_button_type(__("Reject"), __("Secondary Approver"), "danger");
	}
}
