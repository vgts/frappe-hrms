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
		// Show approval stage when pending secondary
		if (
			doc.status === "Approved" &&
			doc.custom_approval_stage === "Pending Secondary Reporting Approval" &&
			!doc.docstatus
		) {
			return [__("Pending Secondary Reporting Approval"), "yellow", "custom_approval_stage,=,Pending Secondary Reporting Approval"];
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
		if (listview._hrms_la_action_delegation) return;
		listview._hrms_la_action_delegation = true;

		const refresh = () => listview.refresh();

		listview.$result.on("click", ".la-list-approve-primary", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const name = $(this).data("name");
			frappe.confirm(
				__("Approve and forward to secondary approver?"),
				() => {
					frappe.call({
						method: "frappe.client.set_value",
						args: {
							doctype: "Leave Application",
							name,
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
								refresh();
							}
						},
					});
				},
			);
		});

		listview.$result.on("click", ".la-list-reject-primary", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const name = $(this).data("name");
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
						method: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject",
						args: {
							leave_application: name,
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
		});

		listview.$result.on("click", ".la-list-secondary-approve", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const name = $(this).data("name");
			frappe.confirm(
				__("Approve and submit this Leave Application?"),
				() => {
					frappe.call({
						method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
						args: { leave_application: name },
						freeze: true,
						freeze_message: __("Approving..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "green" });
								refresh();
							}
						},
					});
				},
			);
		});

		listview.$result.on("click", ".la-list-secondary-reject", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const name = $(this).data("name");
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
						method: "hrms.hr.doctype.leave_application.leave_application.secondary_reject",
						args: {
							leave_application: name,
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
		});
	},

	formatters: {
		name(value, df, doc) {
			const v = value || doc.name || "";
			const esc = frappe.utils.escape_html;
			const idPart = `<a class="filterable ellipsis" data-filter="name,=${esc(v)}">${esc(v)}</a>`;
			const title = `${__(df.label || "ID")}: ${esc(v)}`;

			if (doc.docstatus !== 0) {
				return `<span class="ellipsis" title="${title}"><span class="ellipsis">${idPart}</span></span>`;
			}

			const user = frappe.session.user;
			const hasSecondary = !!doc.custom_secondary_leave_approver;
			const stage = doc.custom_approval_stage;
			const isSecondary = user === doc.custom_secondary_leave_approver;
			const isPrimaryApprover = user === doc.leave_approver;

			let actions = "";
			if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
				actions = `<span class="la-list-actions" style="display:inline-flex;gap:4px;margin-left:6px;vertical-align:middle;flex-shrink:0;">
					<button type="button" class="btn btn-xs btn-primary la-list-secondary-approve" data-name="${esc(
						doc.name,
					)}">${__("Approve & Submit")}</button>
					<button type="button" class="btn btn-xs btn-danger la-list-secondary-reject" data-name="${esc(
						doc.name,
					)}">${__("Reject")}</button>
				</span>`;
			} else if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
				actions = `<span class="la-list-actions" style="display:inline-flex;gap:4px;margin-left:6px;vertical-align:middle;flex-shrink:0;">
					<button type="button" class="btn btn-xs btn-primary la-list-approve-primary" data-name="${esc(
						doc.name,
					)}">${__("Approve")}</button>
					<button type="button" class="btn btn-xs btn-danger la-list-reject-primary" data-name="${esc(
						doc.name,
					)}">${__("Reject")}</button>
				</span>`;
			}

			return `<span class="ellipsis" style="display:inline-flex;align-items:center;flex-wrap:wrap;max-width:100%;" title="${title}">${idPart}${actions}</span>`;
		},
	},
};
