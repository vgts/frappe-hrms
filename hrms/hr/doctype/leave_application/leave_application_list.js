const get_leave_application_action_type = (doc) => {
	if (doc.docstatus !== 0) return null;

	const user = frappe.session.user;
	const hasSecondary = !!doc.custom_secondary_leave_approver;
	const stage = doc.custom_approval_stage;

	if (
		hasSecondary &&
		stage === "Pending Secondary Reporting Approval" &&
		user === doc.custom_secondary_leave_approver
	) {
		return "secondary";
	}

	if (
		hasSecondary &&
		stage === "Pending Project Reporting Approval" &&
		user === doc.leave_approver
	) {
		return "primary";
	}

	return null;
};

const show_leave_application_reject_dialog = (doc, method, refresh) => {
	const d = new frappe.ui.Dialog({
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
				method,
				args: {
					leave_application: doc.name,
					reason: values.reason,
				},
				freeze: true,
				freeze_message: __("Rejecting..."),
				callback(r) {
					if (r.message && r.message.status === "success") {
						frappe.show_alert({ message: r.message.message, indicator: "red" });
						refresh();
					}
				},
			});
		},
	});
	d.show();
};

const refresh_leave_application_list = () => {
	if (window.cur_list && cur_list.doctype === "Leave Application") {
		cur_list.refresh();
	}
};

frappe.listview_settings["Leave Application"] = {
	add_fields: [
		"leave_type",
		"employee",
		"employee_name",
		"total_leave_days",
		"from_date",
		"to_date",
		"custom_approval_stage",
		"leave_approver",
		"custom_secondary_leave_approver",
	],
	has_indicator_for_draft: 1,

	get_indicator: function (doc) {
		if (
			doc.status === "Approved" &&
			doc.custom_approval_stage === "Pending Secondary Reporting Approval" &&
			!doc.docstatus
		) {
			return [
				__("Pending Secondary Reporting Approval"),
				"yellow",
				"custom_approval_stage,=,Pending Secondary Reporting Approval",
			];
		}
		const status_color = {
			Approved: "green",
			Rejected: "red",
			Open: "orange",
			Draft: "red",
			Cancelled: "red",
			Submitted: "blue",
		};
		const status =
			!doc.docstatus && ["Approved", "Rejected"].includes(doc.status) ? "Draft" : doc.status;
		return [__(status), status_color[status], "status,=," + doc.status];
	},

	onload(listview) {
		// ── REMOVE UNWANTED FILTERS ─────────────────────────────
		setTimeout(() => {
			try {
				const filters = listview.filter_area?.filter_list || [];

				let approvalStageRemoved = false;

				filters.forEach((f) => {
					// ❌ Remove Employee Name filter completely
					if (f.fieldname === "employee_name") {
						f.remove();
					}

					// ❌ Remove duplicate Approval Stage (keep only one)
					if (f.fieldname === "custom_approval_stage") {
						if (approvalStageRemoved) {
							f.remove();
						}
						approvalStageRemoved = true;
					}
				});
			} catch (e) {
				console.log("Filter cleanup error:", e);
			}
		}, 500);

		// ── Action column styles ─────────────────────────────
		if (!document.getElementById("la-list-action-styles")) {
			const style = document.createElement("style");
			style.id = "la-list-action-styles";
			style.textContent = `
				.list-row .inner-group-button[data-label="Actions"] {
					min-width: 92px;
				}
				.list-row .inner-group-button[data-label="Actions"] .btn {
					width: 100%;
					justify-content: center;
				}
			`;
			document.head.appendChild(style);
		}
	},

	dropdown_button: {
		get_label: __("Actions"),
		buttons: [
			{
				get_label: __("Approve"),
				get_description: (doc) => {
					const actionType = get_leave_application_action_type(doc);
					return actionType === "secondary"
						? __("Approve and submit this Leave Application")
						: __("Approve and forward to secondary approver");
				},
				show: (doc) => !!get_leave_application_action_type(doc),
				action: (doc) => {
					const actionType = get_leave_application_action_type(doc);
					if (!actionType) return;

					if (actionType === "primary") {
						frappe.confirm(__("Approve and forward to secondary approver?"), () => {
							frappe.call({
								method: "frappe.client.set_value",
								args: {
									doctype: "Leave Application",
									name: doc.name,
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
										refresh_leave_application_list();
									}
								},
							});
						});
						return;
					}

					frappe.confirm(__("Approve and submit this Leave Application?"), () => {
						frappe.call({
							method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
							args: { leave_application: doc.name },
							freeze: true,
							freeze_message: __("Approving..."),
							callback(r) {
								if (r.message && r.message.status === "success") {
									frappe.show_alert({
										message: r.message.message,
										indicator: "green",
									});
									refresh_leave_application_list();
								}
							},
						});
					});
				},
			},
			{
				get_label: __("Reject"),
				get_description: () => __("Reject Leave Application"),
				show: (doc) => !!get_leave_application_action_type(doc),
				action: (doc) => {
					const actionType = get_leave_application_action_type(doc);
					if (!actionType) return;

					const rejectMethod =
						actionType === "secondary"
							? "hrms.hr.doctype.leave_application.leave_application.secondary_reject"
							: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject";

					show_leave_application_reject_dialog(doc, rejectMethod, refresh_leave_application_list);
				},
			},
		],
	},

	formatters: {
		name(value, df, doc) {
			const v = value || doc.name || "";
			const esc = frappe.utils.escape_html;
			const title = `${__(df.label || "ID")}: ${esc(v)}`;
			const idLink = `<a class="filterable ellipsis" data-filter="name,=${esc(v)}">${esc(v)}</a>`;
			return `<span class="ellipsis" title="${title}">${idLink}</span>`;
		},

		custom_approval_stage(value, df, doc) {
			const stageValue = value || doc.custom_approval_stage || "";
			return stageValue ? frappe.format(stageValue, df, null, doc) : "";
		},
	},
};