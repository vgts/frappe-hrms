// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Attendance Regularization", {
	setup: function (frm) {
		frm.set_query("leave_approver", function () {
			return {
				query: "hrms.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: frm.doc.doctype,
				},
			};
		});
		frm.set_query("employee", erpnext.queries.employee);
	},

	refresh: function (frm) {
		frm.trigger("set_employee");

		if (frm.doc.docstatus === 0) {
			frm.set_intro("");
			if (frm.doc.__islocal && !in_list(frappe.user_roles, "Employee")) {
				frm.set_intro(__("Fill the form and save it"));
			} else if (
				frm.perm[0] &&
				frm.perm[0].submit &&
				!frm.is_dirty() &&
				!frm.is_new() &&
				!frappe.model.has_workflow(frm.doctype)
			) {
				frm.set_intro(__("Submit this Attendance Regularization to confirm."));
			}
		}

		// Hide approval section if no secondary approver is configured
		areg_toggle_approval_section(frm);

		// Two-level approval UI
		areg_show_approval_stage_tracker(frm);
		areg_handle_secondary_approval(frm);
	},

	async set_employee(frm) {
		if (frm.doc.employee) return;

		const employee = await hrms.get_current_employee(frm);
		if (employee) {
			frm.set_value("employee", employee);
		}
	},

	employee: function (frm) {
		frm.trigger("set_leave_approver");
	},

	leave_approver: function (frm) {
		areg_toggle_approval_section(frm);
		if (frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	set_leave_approver: function (frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: "hrms.hr.doctype.attendance_regularization.attendance_regularization.get_leave_approver",
				args: {
					employee: frm.doc.employee,
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("leave_approver", r.message);
					}
				},
			});
		}
	},

	checkin_time: function (frm) {
		frm.trigger("calculate_total_hours");
	},

	checkout_time: function (frm) {
		frm.trigger("calculate_total_hours");
	},

	calculate_total_hours: function (frm) {
		if (frm.doc.checkin_time && frm.doc.checkout_time) {
			const checkin = moment(frm.doc.checkin_time, "HH:mm:ss");
			const checkout = moment(frm.doc.checkout_time, "HH:mm:ss");
			if (checkout.isAfter(checkin)) {
				const hours = checkout.diff(checkin, "hours", true);
				frm.set_value("total_hours", Math.round(hours * 100) / 100);
			} else {
				frm.set_value("total_hours", 0);
			}
		} else {
			frm.set_value("total_hours", 0);
		}
	},
});

// ---------------------------------------------------------------------------
// Hide approval section when no secondary approver is configured
// ---------------------------------------------------------------------------

function areg_toggle_approval_section(frm) {
	const hasSecondaryApprover = !!frm.doc.custom_secondary_leave_approver;

	frm.toggle_display("approval_section", hasSecondaryApprover);
	frm.toggle_display("custom_secondary_leave_approver", hasSecondaryApprover);
	frm.toggle_display("custom_secondary_approver_name", hasSecondaryApprover);
	frm.toggle_display("column_break_approval", hasSecondaryApprover);
	frm.toggle_display("custom_approval_stage", hasSecondaryApprover);
}

// ---------------------------------------------------------------------------
// Two-level approval: stage tracker with avatars + secondary approve buttons
// ---------------------------------------------------------------------------

function areg_show_approval_stage_tracker(frm) {
	if (!frm.doc.custom_approval_stage || frm.is_new()) return;

	frappe.call({
		method: "hrms.hr.doctype.attendance_regularization.attendance_regularization.get_regularization_approval_details",
		args: { name: frm.doc.name },
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

			const approverCheck = colors.approver === "green" ? "\u2713" : (colors.approver === "orange" ? "\u25CF" : "\u25CB");
			const secondaryCheck = colors.secondary === "green" ? "\u2713" : (colors.secondary === "red" ? "\u2717" : (colors.secondary === "orange" ? "\u25CF" : "\u25CB"));

			const lineColor = colors.secondary === "green" ? "#22c55e" : (colors.secondary === "red" ? "#ef4444" : "#d1d5db");

			const html = `
				<div class="approval-stage-tracker" style="display:flex;align-items:center;gap:8px;padding:12px 0;">
					<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
						${getAvatar(d.leave_approver_name, d.leave_approver_image)}
						<span style="font-size:11px;color:#374151;text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${frappe.utils.escape_html(d.leave_approver_name || "Leave Approver")}</span>
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

			// Remove old tracker
			$(frm.fields_dict.approval_section?.wrapper)
				.find(".approval-stage-tracker").remove();

			if (frm.fields_dict.approval_section) {
				$(frm.fields_dict.approval_section.wrapper).prepend(html);
			} else {
				frm.dashboard.add_section(html);
			}
		},
	});
}

function areg_handle_secondary_approval(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.custom_secondary_leave_approver) return;

	const isSecondary = frappe.session.user === frm.doc.custom_secondary_leave_approver;
	const stage = frm.doc.custom_approval_stage;

	// Hide submit for leave approver when pending secondary
	if (stage === "Pending Secondary Reporting Approval" && !isSecondary) {
		frm.page.btn_primary.hide();
		frm.disable_save();
	}

	// Hide submit when approved but not yet forwarded
	if (frm.doc.status === "Approved" && !isSecondary && stage !== "Approved") {
		frm.page.btn_primary.hide();
	}

	// Show reject button for project reporting (primary leave approver)
	const isPrimaryApprover = frappe.session.user === frm.doc.leave_approver;
	if (stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject Attendance Regularization"),
				fields: [
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Reason for Rejection"),
						reqd: 1,
					},
				],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_project_reporting_reject",
						args: {
							name: frm.doc.name,
							reason: values.reason,
						},
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

		frm.change_custom_button_type(__("Reject"), __("Leave Approver"), "danger");
	}

	// Show approve/reject buttons for secondary approver
	if (stage === "Pending Secondary Reporting Approval" && isSecondary) {
		frm.page.btn_primary.hide();

		frm.dashboard.set_headline(
			`<span class="indicator-pill yellow">Waiting for your approval</span>`
		);

		frm.add_custom_button(__("Approve & Submit"), () => {
			frappe.confirm(
				__("Approve and submit this Attendance Regularization?"),
				() => {
					frappe.call({
						method: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_approve",
						args: { name: frm.doc.name },
						freeze: true,
						freeze_message: __("Approving..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "green" });
								frm.reload_doc();
							}
						},
					});
				}
			);
		}, __("Secondary Approver"));

		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject Attendance Regularization"),
				fields: [
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Reason for Rejection"),
						reqd: 1,
					},
				],
				primary_action_label: __("Reject"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_reject",
						args: {
							name: frm.doc.name,
							reason: values.reason,
						},
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
	}
}
