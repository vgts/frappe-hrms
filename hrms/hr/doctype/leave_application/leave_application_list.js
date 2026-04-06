frappe.listview_settings["Leave Application"] = {
	add_fields: [
		"leave_type",
		"employee",
		"total_leave_days",
		"from_date",
		"to_date",
		"leave_approver",
		"custom_secondary_leave_approver",
		"custom_approval_stage",
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
			!doc.docstatus && ["Approved", "Rejected"].includes(doc.status)
				? "Draft"
				: doc.status;

		return [__(status), status_color[status], "status,=," + doc.status];
	},

	onload(listview) {
		if (listview._custom_action_setup) return;
		listview._custom_action_setup = true;

		// ✅ REMOVE unwanted filters
		setTimeout(() => {
			const filters = listview.filter_area?.filter_list || [];

			filters.forEach((f) => {
				if (
					f.fieldname === "employee_name" ||
					f.fieldname === "custom_approval_stage"
				) {
					f.remove();
				}
			});
		}, 300);

		// ✅ Inject styles
		if (!document.getElementById("la-action-style")) {
			const style = document.createElement("style");
			style.id = "la-action-style";
			style.textContent = `
				.la-actions {
					display: flex;
					gap: 6px;
					flex-wrap: wrap;
				}
				.la-btn {
					font-size: 11px;
					padding: 3px 10px;
					border-radius: 14px;
					border: 1px solid;
					cursor: pointer;
				}
				.la-approve {
					color: #1b5e20;
					border-color: #2e7d32;
				}
				.la-approve:hover {
					background:#2e7d32;
					color:#fff;
				}
				.la-reject {
					color: #b71c1c;
					border-color: #c62828;
				}
				.la-reject:hover {
					background:#c62828;
					color:#fff;
				}
			`;
			document.head.appendChild(style);
		}

		const refresh = () => listview.refresh();

		// ✅ Primary approve
		listview.$result.on("click", ".la-approve-primary", function (e) {
			e.preventDefault();
			e.stopPropagation();

			const name = $(this).data("name");

			frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Leave Application",
					name,
					fieldname: "status",
					value: "Approved",
				},
				callback: refresh,
			});
		});

		// ✅ Primary reject
		listview.$result.on("click", ".la-reject-primary", function (e) {
			e.preventDefault();
			e.stopPropagation();

			const name = $(this).data("name");

			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject",
				args: { leave_application: name },
				callback: refresh,
			});
		});

		// ✅ Secondary approve
		listview.$result.on("click", ".la-approve-secondary", function (e) {
			e.preventDefault();
			e.stopPropagation();

			const name = $(this).data("name");

			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
				args: { leave_application: name },
				callback: refresh,
			});
		});

		// ✅ Secondary reject
		listview.$result.on("click", ".la-reject-secondary", function (e) {
			e.preventDefault();
			e.stopPropagation();

			const name = $(this).data("name");

			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.secondary_reject",
				args: { leave_application: name },
				callback: refresh,
			});
		});
	},

	formatters: {
		// ✅ Keep ID column clean
		name(value) {
			return `<span class="ellipsis">${value}</span>`;
		},

		// ✅ NEW ACTION COLUMN (IMPORTANT 🔥)
		custom_approval_stage(value, df, doc) {
			const user = frappe.session.user;

			const isPrimary = user === doc.leave_approver;
			const isSecondary = user === doc.custom_secondary_leave_approver;

			let buttons = "";

			if (
				value === "Pending Secondary Reporting Approval" &&
				isSecondary
			) {
				buttons = `
					<div class="la-actions">
						<button class="la-btn la-approve la-approve-secondary" data-name="${doc.name}">Approve</button>
						<button class="la-btn la-reject la-reject-secondary" data-name="${doc.name}">Reject</button>
					</div>
				`;
			}

			else if (
				value === "Pending Project Reporting Approval" &&
				isPrimary
			) {
				buttons = `
					<div class="la-actions">
						<button class="la-btn la-approve la-approve-primary" data-name="${doc.name}">Approve</button>
						<button class="la-btn la-reject la-reject-primary" data-name="${doc.name}">Reject</button>
					</div>
				`;
			}

			// 👉 Show stage text + buttons
			return `
				<div>
					<div style="font-size:12px; margin-bottom:4px;">
						${value || ""}
					</div>
					${buttons}
				</div>
			`;
		},
	},
};