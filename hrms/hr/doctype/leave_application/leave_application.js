// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Leave Application", {
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

	onload: function (frm) {
		// Ignore cancellation of doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];

		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}
		if (frm.doc.docstatus == 0) {
			return frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_mandatory_approval",
				args: {
					doctype: frm.doc.doctype,
				},
				callback: function (r) {
					if (!r.exc && r.message) {
						frm.toggle_reqd("leave_approver", true);
					}
				},
			});
		}
	},

	validate: function (frm) {
		hrms_sync_half_day_session(frm);
		const hasHalfSelection =
			cint(frm.doc.custom_first_half) || cint(frm.doc.custom_second_half);
		// Drive the hidden `half_day` from session checkboxes.
		frm.set_value("half_day", hasHalfSelection ? 1 : 0);

		if (frm.doc.from_date === frm.doc.to_date && cint(frm.doc.half_day)) {
			frm.doc.half_day_date = frm.doc.from_date;
		} else if (frm.doc.half_day === 0) {
			frm.doc.half_day_date = "";
		}
		frm.toggle_reqd("half_day_date", cint(frm.doc.half_day));
	},

	make_dashboard: function (frm) {
		let leave_details;
		let lwps;

		if (frm.doc.employee) {
			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_details",
				async: false,
				args: {
					employee: frm.doc.employee,
					date: frm.doc.from_date || frm.doc.posting_date,
				},
				callback: function (r) {
					if (!r.exc && r.message["leave_allocation"]) {
						leave_details = r.message["leave_allocation"];
					}
					lwps = r.message["lwps"];
				},
			});

			$("div").remove(".form-dashboard-section.custom");

			frm.dashboard.add_section(
				frappe.render_template("leave_application_dashboard", {
					data: leave_details,
				}),
				__("Allocated Leaves"),
			);
			frm.dashboard.show();

			// Show all leave types — no allocation filter
			frm.set_query("leave_type", function () {
				return {};
			});
		}
	},

	refresh: function (frm) {
		hrms.leave_utils.add_view_ledger_button(frm);
		if (frm.is_new()) {
			frm.trigger("calculate_total_days");
		}

		frm.set_intro("");
		if (frm.doc.__islocal && !in_list(frappe.user_roles, "Employee")) {
			frm.set_intro(__("Fill the form and save it"));
		} else if (
			frm.perm[0] &&
			frm.perm[0].submit &&
			!frm.is_dirty() &&
			!frm.is_new() &&
			!frappe.model.has_workflow(frm.doctype) &&
			frm.doc.docstatus === 0
		) {
			frm.set_intro(__("Submit this Leave Application to confirm."));
		}

		frm.trigger("set_employee");
		if (frm.doc.docstatus === 0) {
			frm.trigger("make_dashboard");
		}
		frm.trigger("set_form_buttons");

		// Make fields read-only for approvers (they can only approve/reject, not edit)
		hrms_set_approver_readonly(frm);

		// Hide approval section if no secondary approver is configured
		hrms_toggle_approval_section(frm);

		// Two-level approval UI
		hrms_show_approval_stage_tracker(frm);
		hrms_handle_secondary_approval(frm);
	},

	async set_employee(frm) {
		if (frm.doc.employee) return;

		const employee = await hrms.get_current_employee(frm);
		if (employee) {
			frm.set_value("employee", employee);
		}
	},

	employee: function (frm) {
		frm.trigger("make_dashboard");
		frm.trigger("get_leave_balance");
		frm.trigger("set_leave_approver");
	},

	leave_approver: function (frm) {
		// Re-toggle approval section visibility now that approver is set
		hrms_toggle_approval_section(frm);
		if (frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	leave_type: function (frm) {
		frm.trigger("get_leave_balance");
	},

	half_day: function (frm) {
		hrms_sync_half_day_session(frm);
		if (frm.doc.half_day) {
			if (frm.doc.from_date == frm.doc.to_date) {
				frm.set_value("half_day_date", frm.doc.from_date);
			} else {
				frm.trigger("half_day_datepicker");
			}
		} else {
			frm.set_value("half_day_date", "");
		}
		frm.trigger("calculate_total_days");
	},

	custom_first_half: function (frm) {
		hrms_sync_half_day_session(frm, "custom_first_half");
		frm.set_value("half_day", cint(frm.doc.custom_first_half) || cint(frm.doc.custom_second_half) ? 1 : 0);
		frm.trigger("calculate_total_days");
	},

	custom_second_half: function (frm) {
		hrms_sync_half_day_session(frm, "custom_second_half");
		frm.set_value("half_day", cint(frm.doc.custom_first_half) || cint(frm.doc.custom_second_half) ? 1 : 0);
		frm.trigger("calculate_total_days");
	},

	from_date: function (frm) {
		frm.events.validate_from_to_date(frm, "from_date");
		frm.trigger("make_dashboard");
		frm.trigger("half_day_datepicker");
		frm.trigger("calculate_total_days");
	},

	to_date: function (frm) {
		frm.events.validate_from_to_date(frm, "to_date");
		frm.trigger("make_dashboard");
		frm.trigger("half_day_datepicker");
		frm.trigger("calculate_total_days");
	},

	half_day_date(frm) {
		frm.trigger("calculate_total_days");
	},

	validate_from_to_date: function (frm, updated_field) {
		if (!frm.doc.from_date || !frm.doc.to_date) return;

		const from_date = Date.parse(frm.doc.from_date);
		const to_date = Date.parse(frm.doc.to_date);

		if (to_date < from_date) {
			const other_field = updated_field === "from_date" ? "to_date" : "from_date";

			frm.set_value(other_field, frm.doc[updated_field]);
			frappe.show_alert({
				message: __("Changing '{0}' to {1}.", [
					__(frm.fields_dict[other_field].df.label),
					frappe.datetime.str_to_user(frm.doc[updated_field]),
				]),
				indicator: "blue",
			});
		}
	},

	half_day_datepicker: function (frm) {
		frm.set_value("half_day_date", "");
		if (!(frm.doc.half_day && frm.doc.from_date && frm.doc.to_date)) return;

		const half_day_datepicker = frm.fields_dict.half_day_date.datepicker;
		half_day_datepicker.update({
			minDate: frappe.datetime.str_to_obj(frm.doc.from_date),
			maxDate: frappe.datetime.str_to_obj(frm.doc.to_date),
		});
	},

	get_leave_balance: function (frm) {
		if (
			frm.doc.docstatus === 0 &&
			frm.doc.employee &&
			frm.doc.leave_type &&
			frm.doc.from_date &&
			frm.doc.to_date
		) {
			return frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
				args: {
					employee: frm.doc.employee,
					date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					leave_type: frm.doc.leave_type,
					consider_all_leaves_in_the_allocation_period: 1,
				},
				callback: function (r) {
					if (!r.exc && r.message) {
						frm.set_value("leave_balance", r.message);
					} else {
						frm.set_value("leave_balance", "0");
					}
				},
			});
		}
	},

	calculate_total_days: function (frm) {
		if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
				args: {
					employee: frm.doc.employee,
					leave_type: frm.doc.leave_type,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					half_day: frm.doc.half_day,
					half_day_date: frm.doc.half_day_date,
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("total_leave_days", r.message);
						frm.trigger("get_leave_balance");
					}
				},
			});
		}
	},

	set_leave_approver: function (frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_approver",
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

	set_form_buttons: async function (frm) {
		let self_approval_not_allowed = frm.doc.__onload
			? frm.doc.__onload.self_leave_approval_not_allowed
			: 0;
		let current_employee = await hrms.get_current_employee();
		if (
			frm.doc.docstatus === 0 &&
			!frm.is_dirty() &&
			!frappe.model.has_workflow(frm.doctype)
		) {
			if (self_approval_not_allowed && current_employee == frm.doc.employee) {
				frm.set_df_property("status", "read_only", 1);
				frm.trigger("show_save_button");
			}
		}
	},
	show_save_button: function (frm) {
		frm.page.set_primary_action(__("Save"), () => {
			frm.save();
		});
		$(".form-message").prop("hidden", true);
	},
	posting_date: function (frm) {
		frm.trigger("make_dashboard");
		frm.trigger("get_leave_balance");
	},
});

function hrms_sync_half_day_session(frm, changed_field = null) {
	if (frm.__syncing_half_day_session) return;
	frm.__syncing_half_day_session = true;

	try {
		// When a custom session checkbox is explicitly enabled, auto-enable half_day
		// so it isn't immediately cleared by the !halfDayEnabled guard below.
		if (
			(changed_field === "custom_first_half" && cint(frm.doc.custom_first_half)) ||
			(changed_field === "custom_second_half" && cint(frm.doc.custom_second_half))
		) {
			frm.doc.half_day = 1;
			frm.refresh_field("half_day");
			// Set half_day_date immediately so calculate_total_days returns 0.5
			if (frm.doc.from_date) {
				frm.doc.half_day_date = frm.doc.from_date;
				frm.refresh_field("half_day_date");
			}
		}

		const halfDayEnabled = cint(frm.doc.half_day);
		let first = cint(frm.doc.custom_first_half);
		let second = cint(frm.doc.custom_second_half);

		// If half-day is off, clear both session checkboxes.
		if (!halfDayEnabled) {
			if (first) frm.set_value("custom_first_half", 0);
			if (second) frm.set_value("custom_second_half", 0);
			return;
		}

		// Enforce mutual exclusion (only one of first/second can be checked).
		if (first && second) {
			if (changed_field === "custom_second_half") {
				frm.set_value("custom_first_half", 0);
				first = 0;
			} else {
				frm.set_value("custom_second_half", 0);
				second = 0;
			}
		}

		// If half-day is enabled and user unchecks both, default to first half.
		if (!first && !second) {
			frm.set_value("custom_first_half", 1);
		}
	} finally {
		frm.__syncing_half_day_session = false;
	}
}

function hrms_toggle_half_day_session(frm) {
	const show = cint(frm.doc.half_day);
	frm.toggle_display("custom_first_half", show);
	frm.toggle_display("custom_second_half", show);

	if (show) {
		// If user enabled half-day and didn't choose a session yet, default to first half.
		if (!cint(frm.doc.custom_first_half) && !cint(frm.doc.custom_second_half)) {
			frm.set_value("custom_first_half", 1);
		}
	} else {
		// Clean values when half-day is off.
		if (cint(frm.doc.custom_first_half)) frm.set_value("custom_first_half", 0);
		if (cint(frm.doc.custom_second_half)) frm.set_value("custom_second_half", 0);
	}
}

// ---------------------------------------------------------------------------
// Hide approval section when no secondary approver is configured
// ---------------------------------------------------------------------------

function hrms_toggle_approval_section(frm) {
	const hasApprover = frm.doc.leave_approver || frm.doc.custom_secondary_leave_approver;
	const hasSecondaryApprover = !!frm.doc.custom_secondary_leave_approver;

	// Hide the primary "Approval" section if no approver at all
	frm.toggle_display("section_break_7", hasApprover);
	frm.toggle_display("leave_approver", hasApprover);
	frm.toggle_display("leave_approver_name", hasApprover);

	// Hide the secondary approval section if no secondary approver
	frm.toggle_display("custom_secondary_approval_section", hasSecondaryApprover);
	frm.toggle_display("custom_secondary_leave_approver", hasSecondaryApprover);
	frm.toggle_display("custom_secondary_approver_name", hasSecondaryApprover);
	frm.toggle_display("custom_column_break_secondary", hasSecondaryApprover);
	frm.toggle_display("custom_approval_stage", hasSecondaryApprover);
}

// ---------------------------------------------------------------------------
// Make leave application fields read-only for approvers
// ---------------------------------------------------------------------------

function hrms_set_approver_readonly(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;

	const user = frappe.session.user;
	const isApprover = user === frm.doc.leave_approver ||
		user === frm.doc.custom_secondary_leave_approver;

	// Get employee's user_id to check if current user is the employee
	const employeeUserId = frm.doc.__onload?.employee_user_id;

	if (!isApprover) return;

	// Check if current user is also the employee (self-approval case)
	frappe.db.get_value("Employee", frm.doc.employee, "user_id", (r) => {
		if (r && r.user_id === user) return; // Employee viewing own application

		// Approver viewing — lock all content fields
		const readonlyFields = [
			"leave_type", "from_date", "to_date", "half_day", "half_day_date",
			"description", "follow_via_email", "total_leave_days",
			"leave_balance", "posting_date", "employee", "employee_name",
		];
		readonlyFields.forEach((fieldname) => {
			frm.set_df_property(fieldname, "read_only", 1);
		});
	});
}

// ---------------------------------------------------------------------------
// Two-level approval: stage tracker with avatars + secondary approve buttons
// ---------------------------------------------------------------------------

function hrms_show_approval_stage_tracker(frm) {
	if (!frm.doc.custom_approval_stage || frm.is_new()) return;

	frappe.call({
		method: "hrms.hr.doctype.leave_application.leave_application.get_secondary_approval_details",
		args: { leave_application: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const d = r.message;
			const stage = d.approval_stage;

			const getAvatar = (name, image) => {
				if (image) return `<img src="${image}" class="avatar avatar-small" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" title="${frappe.utils.escape_html(name || "")}">`;
				const initials = (name || "?").split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
				return `<div style="width:32px;height:32px;border-radius:50%;background:#d1d5db;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#374151;" title="${frappe.utils.escape_html(name || "")}">${initials}</div>`;
			};

			// Determine if rejection was at primary or secondary level
			const wasRejectedAtPrimary = stage === "Rejected" && d.approval_stage === "Rejected" &&
				frm.doc.status === "Rejected" &&
				frm.doc.custom_approval_stage === "Rejected" &&
				frm.doc.docstatus === 2;

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

function hrms_handle_secondary_approval(frm) {
	if (frm.doc.docstatus !== 0) return;

	const hasSecondary = !!frm.doc.custom_secondary_leave_approver;
	const isSecondary = frappe.session.user === frm.doc.custom_secondary_leave_approver;
	const stage = frm.doc.custom_approval_stage;
	const isPrimaryApprover = frappe.session.user === frm.doc.leave_approver;

	// --- Secondary approver: final approval ---
	if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
		frm.page.btn_primary.hide();

		frm.dashboard.set_headline(
			`<span class="indicator-pill yellow">Waiting for your approval</span>`
		);

		frm.add_custom_button(__("Approve & Submit"), () => {
			frappe.confirm(
				__("Approve and submit this Leave Application?"),
				() => {
					frappe.call({
						method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
						args: { leave_application: frm.doc.name },
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
				title: __("Reject Leave Application"),
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
						method: "hrms.hr.doctype.leave_application.leave_application.secondary_reject",
						args: {
							leave_application: frm.doc.name,
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
		return;
	}

	// Hide submit for two-level flows (waiting on secondary or forwarding)
	if (hasSecondary) {
		if (stage === "Pending Secondary Reporting Approval" && !isSecondary) {
			frm.page.btn_primary.hide();
			frm.disable_save();
		}
		if (frm.doc.status === "Approved" && !isSecondary && stage !== "Approved") {
			frm.page.btn_primary.hide();
		}
	}

	// Two-level: primary leave approver — approve (forward) + reject with reason
	if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
		frm.add_custom_button(__("Approve"), () => {
			frappe.confirm(
				__("Approve and forward to secondary approver?"),
				() => {
					frappe.call({
						method: "frappe.client.set_value",
						args: {
							doctype: "Leave Application",
							name: frm.doc.name,
							fieldname: "status",
							value: "Approved",
						},
						freeze: true,
						freeze_message: __("Approving..."),
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({
									message: __("Forwarded for secondary approval"),
									indicator: "blue",
								});
								frm.reload_doc();
							}
						},
					});
				}
			);
		}, __("Leave Approver"));

		frm.add_custom_button(__("Reject"), () => {
			let d = new frappe.ui.Dialog({
				title: __("Reject Leave Application"),
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
						method: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject",
						args: {
							leave_application: frm.doc.name,
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

		frm.change_custom_button_type(__("Approve"), __("Leave Approver"), "primary");
		frm.change_custom_button_type(__("Reject"), __("Leave Approver"), "danger");
	}
}

frappe.tour["Leave Application"] = [
	{
		fieldname: "employee",
		title: "Employee",
		description: __("Select the Employee."),
	},
	{
		fieldname: "leave_type",
		title: "Leave Type",
		description: __(
			"Select type of leave the employee wants to apply for, like Sick Leave, Privilege Leave, Casual Leave, etc.",
		),
	},
	{
		fieldname: "from_date",
		title: "From Date",
		description: __("Select the start date for your Leave Application."),
	},
	{
		fieldname: "to_date",
		title: "To Date",
		description: __("Select the end date for your Leave Application."),
	},
	{
		fieldname: "half_day",
		title: "Half Day",
		description: __("To apply for a Half Day check 'Half Day' and select the Half Day Date"),
	},
	{
		fieldname: "leave_approver",
		title: "Leave Approver",
		description: __(
			"Select your Leave Approver i.e. the person who approves or rejects your leaves.",
		),
	},
];
