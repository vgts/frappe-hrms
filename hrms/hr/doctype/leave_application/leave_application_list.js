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

		// ── Inject button styles ──────────────────────────────────────────────
		if (!document.getElementById("la-list-action-styles")) {
			const style = document.createElement("style");
			style.id = "la-list-action-styles";
			style.textContent = `
				/* Actions column header */
				.la-actions-th {
					min-width: 190px;
					flex-shrink: 0;
					font-size: 11px;
					font-weight: 600;
					text-transform: uppercase;
					letter-spacing: 0.5px;
					color: var(--text-muted, #8d99a6);
					padding: 0 8px;
					display: flex;
					align-items: center;
				}
				/* Actions cell per row */
				.la-actions-td {
					min-width: 190px;
					flex-shrink: 0;
					display: flex;
					align-items: center;
					gap: 6px;
					padding: 0 8px;
				}
				/* Base button */
				.la-action-btn {
					display: inline-flex;
					align-items: center;
					gap: 5px;
					padding: 4px 12px;
					border-radius: 20px;
					font-size: 11.5px;
					font-weight: 600;
					border: 1.5px solid;
					cursor: pointer;
					background: transparent;
					transition: background 0.15s ease, color 0.15s ease;
					white-space: nowrap;
					line-height: 1.5;
					outline: none;
				}
				/* Approve — green outline */
				.la-action-btn.la-approve {
					color: #2e7d32;
					border-color: #2e7d32;
				}
				.la-action-btn.la-approve:hover {
					background: #2e7d32;
					color: #fff;
				}
				/* Reject — red outline */
				.la-action-btn.la-reject {
					color: #c62828;
					border-color: #c62828;
				}
				.la-action-btn.la-reject:hover {
					background: #c62828;
					color: #fff;
				}
			`;
			document.head.appendChild(style);
		}

		// ── Click delegation ──────────────────────────────────────────────────
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
						args: { doctype: "Leave Application", name, fieldname: "status", value: "Approved" },
						freeze: true,
						freeze_message: __("Approving..."),
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
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
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
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
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 }],
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
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								refresh();
							}
						},
					});
				},
			});
			d.show();
		});

		// ── Inject "Actions" column after each list render ────────────────────
		function renderActionColumn() {
			const data = listview.data || [];
			const user = frappe.session.user;
			const esc = frappe.utils.escape_html;

			// Header: insert once before the last column (level-right)
			const $head = listview.$result.find(".list-row-head");
			if ($head.length && !$head.find(".la-actions-th").length) {
				$head.find(".level-right").first().before(
					`<div class="la-actions-th">${__("Actions")}</div>`
				);
			}

			// Per-row cells
			listview.$result.find(".list-row[data-name]").each(function () {
				const $row = $(this);
				if ($row.find(".la-actions-td").length) return; // already injected

				const name = $row.data("name");
				const doc = data.find((d) => d.name === name);

				// Empty cell placeholder to keep column alignment
				if (!doc || doc.docstatus !== 0) {
					$row.find(".level-right").first().before(`<div class="la-actions-td"></div>`);
					return;
				}

				const hasSecondary = !!doc.custom_secondary_leave_approver;
				const stage = doc.custom_approval_stage;
				const isSecondary = user === doc.custom_secondary_leave_approver;
				const isPrimaryApprover = user === doc.leave_approver;

				let btns = "";
				if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
					btns = `
						<button type="button" class="la-action-btn la-approve la-list-secondary-approve" data-name="${esc(name)}">
							✓ ${__("Approve & Submit")}
						</button>
						<button type="button" class="la-action-btn la-reject la-list-secondary-reject" data-name="${esc(name)}">
							✗ ${__("Reject")}
						</button>`;
				} else if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimaryApprover) {
					btns = `
						<button type="button" class="la-action-btn la-approve la-list-approve-primary" data-name="${esc(name)}">
							✓ ${__("Approve")}
						</button>
						<button type="button" class="la-action-btn la-reject la-list-reject-primary" data-name="${esc(name)}">
							✗ ${__("Reject")}
						</button>`;
				}

				$row.find(".level-right").first().before(
					`<div class="la-actions-td">${btns}</div>`
				);
			});
		}

		// Observe list result for re-renders and inject column each time
		const observer = new MutationObserver(function () {
			renderActionColumn();
		});
		if (listview.$result && listview.$result[0]) {
			observer.observe(listview.$result[0], { childList: true });
		}
	},

	formatters: {
		// Keep ID column clean — just the link, no buttons
		name(value, df, doc) {
			const v = value || doc.name || "";
			const esc = frappe.utils.escape_html;
			const title = `${__(df.label || "ID")}: ${esc(v)}`;
			const link = `<a class="filterable ellipsis" data-filter="name,=${esc(v)}">${esc(v)}</a>`;
			return `<span class="ellipsis" title="${title}">${link}</span>`;
		},
	},
};
