const get_attendance_regularization_action_type = (doc) => {
	if (doc.docstatus !== 0) return null;

	const user = frappe.session.user;
	const hasSecondary = !!doc.custom_secondary_leave_approver;
	const stage = doc.custom_approval_stage;
	const isPrimaryApprover = user === doc.leave_approver;
	const isSecondaryApprover = user === doc.custom_secondary_leave_approver;

	if (
		hasSecondary &&
		stage === "Pending Project Reporting Approval" &&
		isPrimaryApprover
	) {
		return "primary_two_level";
	}

	if (
		hasSecondary &&
		stage === "Pending Secondary Reporting Approval" &&
		isSecondaryApprover
	) {
		return "secondary";
	}

	if (!hasSecondary && isPrimaryApprover && doc.status === "Open") {
		return "primary_single";
	}

	return null;
};

const refresh_attendance_regularization_list = () => {
	if (
		window.cur_list &&
		cur_list.doctype === "Attendance Regularization"
	) {
		cur_list.refresh();
	}
};

const show_attendance_regularization_reject_dialog = (doc, method) => {
	const d = new frappe.ui.Dialog({
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
				method,
				args: {
					attendance_regularization: doc.name,
					reason: values.reason,
				},
				freeze: true,
				freeze_message: __("Rejecting..."),
				callback(r) {
					if (r.message && r.message.status === "success") {
						frappe.show_alert({ message: r.message.message, indicator: "red" });
						refresh_attendance_regularization_list();
					}
				},
			});
		},
	});
	d.show();
};

frappe.listview_settings["Attendance Regularization"] = {
	add_fields: [
		"status",
		"leave_approver",
		"custom_secondary_leave_approver",
		"custom_approval_stage",
	],

	has_indicator_for_draft: 1,

	get_indicator(doc) {
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

	onload() {
		if (!document.getElementById("areg-list-action-styles")) {
			const style = document.createElement("style");
			style.id = "areg-list-action-styles";
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
					const type = get_attendance_regularization_action_type(doc);
					if (type === "primary_two_level") {
						return __("Approve and forward to secondary approver");
					}
					return __("Approve and submit this Attendance Regularization");
				},
				show: (doc) => !!get_attendance_regularization_action_type(doc),
				action: (doc) => {
					const type = get_attendance_regularization_action_type(doc);
					if (!type) return;

					if (type === "primary_two_level") {
						frappe.confirm(__("Approve and forward to secondary approver?"), () => {
							frappe.call({
								method: "frappe.client.set_value",
								args: {
									doctype: "Attendance Regularization",
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
										refresh_attendance_regularization_list();
									}
								},
							});
						});
						return;
					}

					const method =
						type === "secondary"
							? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_approve"
							: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_approve_submit";

					frappe.confirm(__("Approve and submit this Attendance Regularization?"), () => {
						frappe.call({
							method,
							args: { attendance_regularization: doc.name },
							freeze: true,
							freeze_message: __("Approving..."),
							callback(r) {
								if (r.message && r.message.status === "success") {
									frappe.show_alert({ message: r.message.message, indicator: "green" });
									refresh_attendance_regularization_list();
								}
							},
						});
					});
				},
			},
			{
				get_label: __("Reject"),
				get_description: () => __("Reject Attendance Regularization"),
				show: (doc) => !!get_attendance_regularization_action_type(doc),
				action: (doc) => {
					const type = get_attendance_regularization_action_type(doc);
					if (!type) return;

					const reject_method =
						type === "secondary"
							? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_reject"
							: type === "primary_two_level"
								? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_project_reporting_reject"
								: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_reject_submit";

					show_attendance_regularization_reject_dialog(doc, reject_method);
				},
			},
		],
	},
};
