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
		if (listview._hrms_la_action_delegation) return;
		listview._hrms_la_action_delegation = true;

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

		// ── Inject button styles ─────────────────────────────
		if (!document.getElementById("la-list-action-styles")) {
			const style = document.createElement("style");
			style.id = "la-list-action-styles";
			style.textContent = `
				.la-approval-cell {
					display: flex;
					align-items: center;
					justify-content: space-between;
					gap: 8px;
					width: 100%;
					max-width: 320px;
				}
				.la-approval-stage {
					flex: 0 0 auto;
					min-width: 0;
				}
				.la-action-wrap {
					display: inline-flex;
					align-items: center;
					justify-content: flex-end;
					gap: 6px;
					flex-wrap: nowrap;
					flex: 0 0 auto;
					min-width: 0;
				}
				.la-action-btn {
					display: inline-flex;
					align-items: center;
					gap: 4px;
					padding: 3px 11px;
					border-radius: 20px;
					font-size: 11.5px;
					font-weight: 600;
					border: 1.5px solid;
					cursor: pointer;
					background: transparent;
					transition: background 0.15s, color 0.15s;
					white-space: nowrap;
					line-height: 1.5;
					outline: none;
				}
				.la-action-btn.la-approve {
					color: #1b5e20;
					border-color: #2e7d32;
				}
				.la-action-btn.la-approve:hover {
					background: #2e7d32;
					color: #fff;
				}
				.la-action-btn.la-reject {
					color: #b71c1c;
					border-color: #c62828;
				}
				.la-action-btn.la-reject:hover {
					background: #c62828;
					color: #fff;
				}
				@media (max-width: 991px) {
					.la-approval-cell {
						flex-direction: column;
						align-items: flex-start;
						max-width: 100%;
					}
					.la-action-wrap {
						justify-content: flex-start;
						flex-wrap: wrap;
					}
				}
			`;
			document.head.appendChild(style);
		}

		// ── Click delegation ─────────────────────────────
		const refresh = () => listview.refresh();

		listview.$result.on("click", ".la-list-approve-primary", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const name = $(this).data("name");

			frappe.confirm(__("Approve and forward to secondary approver?"), () => {
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
			});
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
						args: { leave_application: name, reason: values.reason },
						freeze: true,
						freeze_message: __("Rejecting..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({
									message: r.message.message,
									indicator: "red",
								});
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

			frappe.confirm(__("Approve and submit this Leave Application?"), () => {
				frappe.call({
					method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
					args: { leave_application: name },
					freeze: true,
					freeze_message: __("Approving..."),
					callback(r) {
						if (r.message && r.message.status === "success") {
							frappe.show_alert({
								message: r.message.message,
								indicator: "green",
							});
							refresh();
						}
					},
				});
			});
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
						args: { leave_application: name, reason: values.reason },
						freeze: true,
						freeze_message: __("Rejecting..."),
						callback(r) {
							if (r.message && r.message.status === "success") {
								frappe.show_alert({
									message: r.message.message,
									indicator: "red",
								});
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
			const title = `${__(df.label || "ID")}: ${esc(v)}`;
			const idLink = `<a class="filterable ellipsis" data-filter="name,=${esc(v)}">${esc(v)}</a>`;

			return `<span class="ellipsis" title="${title}">${idLink}</span>`;
		},

		custom_approval_stage(value, df, doc) {
			const esc = frappe.utils.escape_html;
			const stage_value = value || doc.custom_approval_stage || "";

			const base_stage =
				stage_value
					? `<span class="ellipsis la-approval-stage">${frappe.format(
							stage_value,
							df,
							null,
							doc,
					  )}</span>`
					: `<span class="ellipsis la-approval-stage"></span>`;

			if (doc.docstatus !== 0) {
				return `<div class="la-approval-cell">${base_stage}</div>`;
			}

			const user = frappe.session.user;
			const hasSecondary = !!doc.custom_secondary_leave_approver;
			const stage = doc.custom_approval_stage;
			const isSecondary = user === doc.custom_secondary_leave_approver;
			const isPrimaryApprover = user === doc.leave_approver;

			let actions = "";

			if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
				actions = `
					<div class="la-action-wrap">
						<button class="la-action-btn la-approve la-list-secondary-approve" data-name="${esc(
							doc.name,
						)}">
							✓ ${__("Approve & Submit")}
						</button>
						<button class="la-action-btn la-reject la-list-secondary-reject" data-name="${esc(
							doc.name,
						)}">
							✗ ${__("Reject")}
						</button>
					</div>`;
			} else if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
				actions = `
					<div class="la-action-wrap">
						<button class="la-action-btn la-approve la-list-approve-primary" data-name="${esc(
							doc.name,
						)}">
							✓ ${__("Approve")}
						</button>
						<button class="la-action-btn la-reject la-list-reject-primary" data-name="${esc(
							doc.name,
						)}">
							✗ ${__("Reject")}
						</button>
					</div>`;
			}

			return `<div class="la-approval-cell">${base_stage}${actions}</div>`;
		},
	},
};