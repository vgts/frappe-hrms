// Copyright (c) 2026, VGTS and contributors
// Desk dashboard: unified HR requests with cards + quick approve/reject

frappe.pages["vgts-hr-requests"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("HR Requests"),
		single_column: true,
	});

	frappe.vgts_hr_req_dashboard.make(page);

	$(wrapper).bind("show", () => {
		frappe.breadcrumbs.add("HR");
		frappe.vgts_hr_req_dashboard.refresh();
	});

	if (frappe.model.can_read("VGTS HR Request")) {
		page.add_menu_item(__("Table view (VGTS HR Request)"), () => {
			frappe.set_route("List", "VGTS HR Request");
		});
	}
};

frappe.vgts_hr_req_dashboard = {
	page: null,
	start: 0,
	statusFilter: "all",
	needsMyActionOnly: false,
	searchText: "",
	allLoadedRows: [],

	TYPE_META: {
		"Leave Application": { short: "LA", cls: "vgts-req-type--leave" },
		"Attendance Regularization": { short: "AR", cls: "vgts-req-type--reg" },
		"Employee Permission": { short: "EP", cls: "vgts-req-type--perm" },
		"Compensatory Leave Request": { short: "CLR", cls: "vgts-req-type--clr" },
		"Attendance Request": { short: "ATR", cls: "vgts-req-type--atr" },
	},

	injectStyles() {
		if (document.getElementById("vgts-req-dash-styles")) return;
		const style = document.createElement("style");
		style.id = "vgts-req-dash-styles";
		style.textContent = `
			.vgts-req-dash-toolbar {
				display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
				margin-bottom: 16px; padding: 12px 4px; border-bottom: 1px solid var(--border-color);
			}
			.vgts-req-dash-toolbar .form-control { max-width: 220px; }
			.vgts-req-dash-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
			.vgts-req-dash-chips .btn { border-radius: 20px; }
			.vgts-req-dash-chips .btn.active { font-weight: 600; }
			.vgts-req-dash-table-wrap { border: 1px solid var(--border-color); border-radius: 8px; overflow: auto; }
			.vgts-req-dash-table { width: 100%; border-collapse: collapse; min-width: 1100px; }
			.vgts-req-dash-table th, .vgts-req-dash-table td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); font-size: 12px; }
			.vgts-req-dash-table th { background: var(--subtle-fg); text-align: left; font-weight: 600; position: sticky; top: 0; z-index: 1; }
			.vgts-req-row-actions { display: flex; gap: 6px; white-space: nowrap; }
			.vgts-req-id { font-family: var(--font-stack-monospace); font-size: 11px; }
			.vgts-req-dash-empty { padding: 48px; text-align: center; color: var(--text-muted); }
		`;
		document.head.appendChild(style);
	},

	make(page) {
		this.injectStyles();
		this.page = page;
		this.toolbar = $(`<div class="vgts-req-dash-toolbar"></div>`).appendTo(this.page.main);

		const search = $(
			`<input type="search" class="form-control" placeholder="${__(
				"Search name, ID, reason…",
			)}">`,
		);
		search.on(
			"input",
			frappe.utils.debounce(() => {
				this.searchText = (search.val() || "").toLowerCase();
				this.renderCards();
			}, 200),
		);

		this.chipsWrap = $(`<div class="vgts-req-dash-chips"></div>`);
		const chips = [
			["all", __("All")],
			["pending_mine", __("Awaiting my approval")],
			["Open", __("Open")],
			["Approved", __("Approved")],
			["Rejected", __("Rejected")],
			["Submitted", __("Submitted")],
		];
		chips.forEach(([key, label]) => {
			const btn = $(`<button type="button" class="btn btn-xs btn-default">${label}</button>`);
			btn.on("click", () => {
				this.chipsWrap.find("button").removeClass("btn-primary active").addClass("btn-default");
				btn.removeClass("btn-default").addClass("btn-primary active");
				if (key === "pending_mine") {
					this.needsMyActionOnly = true;
					this.statusFilter = "all";
				} else {
					this.needsMyActionOnly = false;
					this.statusFilter = key;
				}
				this.refresh();
			});
			this.chipsWrap.append(btn);
		});
		this.chipsWrap.find("button").first().removeClass("btn-default").addClass("btn-primary active");

		this.toolbar.append(search, this.chipsWrap);

		this.cardsWrap = $(`<div class="vgts-req-dash-table-wrap"></div>`).appendTo(this.page.main);
		this.moreWrap = $(`<div class="text-center" style="padding:16px;"></div>`).appendTo(this.page.main);
		this.moreBtn = $(
			`<button type="button" class="btn btn-default btn-sm">${__("Load more")}</button>`,
		).appendTo(this.moreWrap);
		this.moreBtn.on("click", () => this.fetch(true));
	},

	refresh() {
		this.start = 0;
		this.allLoadedRows = [];
		this.cardsWrap.empty();
		this.fetch(false);
	},

	fetch(append) {
		const limit = this.needsMyActionOnly ? 200 : 60;
		if (!append) {
			this.start = 0;
		}
		const offset = append ? this.start : 0;
		frappe.call({
			method: "hrms.hr.doctype.vgts_hr_request.vgts_hr_request.get_dashboard_data",
			args: {
				limit_start: offset,
				limit_page_length: limit,
				status_filter: this.needsMyActionOnly ? "all" : this.statusFilter,
			},
			freeze: !append,
			freeze_message: __("Loading…"),
			callback: (r) => {
				const rows = r.message || [];
				if (append) {
					this.allLoadedRows = this.allLoadedRows.concat(rows);
					this.start += rows.length;
				} else {
					this.allLoadedRows = rows;
					this.start = rows.length;
				}
				this.moreBtn.toggle(rows.length >= limit && !this.needsMyActionOnly);
				this.renderCards();
			},
		});
	},

	rowToMinimalDoc(row) {
		const d = {
			name: row.reference_name,
			docstatus: row.docstatus,
			status: row.status,
			leave_approver: row.leave_approver,
			custom_secondary_leave_approver: row.custom_secondary_leave_approver,
			custom_approval_stage: row.approval_stage,
		};
		if (row.reference_doctype === "Attendance Request") {
			d.approver = row.leave_approver;
		}
		return d;
	},

	getLeaveActionType(doc) {
		if (frappe.utils.cint(doc.docstatus) !== 0) return null;
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
		if (hasSecondary && stage === "Pending Project Reporting Approval" && user === doc.leave_approver) {
			return "primary";
		}
		return null;
	},

	getTwoLevelActionType(doc) {
		if (frappe.utils.cint(doc.docstatus) !== 0) return null;
		const user = frappe.session.user;
		const hasSecondary = !!doc.custom_secondary_leave_approver;
		const stage = doc.custom_approval_stage;
		const isPrimary = user === doc.leave_approver;
		const isSecondary = user === doc.custom_secondary_leave_approver;
		if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimary) {
			return "primary_two_level";
		}
		if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
			return "secondary";
		}
		if (!hasSecondary && isPrimary && doc.status === "Open") return "primary_single";
		return null;
	},

	getAttendanceRequestActionType(doc) {
		if (frappe.utils.cint(doc.docstatus) !== 0) return null;
		const user = frappe.session.user;
		const hasSecondary = !!doc.custom_secondary_leave_approver;
		const stage = doc.custom_approval_stage;
		const isPrimary = user === doc.approver;
		const isSecondary = user === doc.custom_secondary_leave_approver;
		if (hasSecondary && stage === "Pending Project Reporting Approval" && isPrimary) {
			return "primary_two_level";
		}
		if (hasSecondary && stage === "Pending Secondary Reporting Approval" && isSecondary) {
			return "secondary";
		}
		if (!hasSecondary && isPrimary && doc.status === "Open") return "primary_single";
		return null;
	},

	getActionType(row) {
		const d = this.rowToMinimalDoc(row);
		switch (row.reference_doctype) {
			case "Leave Application":
				return this.getLeaveActionType(d);
			case "Attendance Regularization":
			case "Employee Permission":
				return this.getTwoLevelActionType(d);
			case "Attendance Request":
				return this.getAttendanceRequestActionType(d);
			default:
				return null;
		}
	},

	filterRows(rows) {
		let out = rows;
		if (this.needsMyActionOnly) {
			out = out.filter((r) => !!this.getActionType(r));
		}
		if (!this.searchText) return out;
		const q = this.searchText;
		return out.filter((r) => {
			const blob = [
				r.reference_name,
				r.employee_name,
				r.request_type,
				r.reason,
				r.approver_name,
				r.pending_with,
				r.approval_stage,
				r.status,
			]
				.filter(Boolean)
				.join(" ")
				.toLowerCase();
			return blob.includes(q);
		});
	},

	renderCards() {
		this.cardsWrap.empty();
		const rows = this.filterRows(this.allLoadedRows);
		if (!rows.length) {
			this.cardsWrap.append(
				`<div class="vgts-req-dash-empty">${__("No requests match this view.")}</div>`,
			);
			return;
		}
		const $table = $(`<table class="vgts-req-dash-table">
			<thead>
				<tr>
					<th>${__("Employee Name")}</th>
					<th>${__("Status")}</th>
					<th>${__("From Date")}</th>
					<th>${__("Leave Type")}</th>
					<th>${__("Total Days")}</th>
					<th>${__("Approval Stage")}</th>
					<th>${__("Pending With")}</th>
					<th>${__("ID")}</th>
					<th>${__("Actions")}</th>
				</tr>
			</thead>
			<tbody></tbody>
		</table>`);
		const $tbody = $table.find("tbody");
		rows.forEach((row) => $tbody.append(this.buildCard(row)));
		this.cardsWrap.append($table);
	},

	statusColor(status) {
		const s = status || "";
		if (s === "Open") return "orange";
		if (s === "Approved") return "green";
		if (s === "Rejected") return "red";
		if (s === "Submitted") return "blue";
		return "gray";
	},

	buildCard(row) {
		const actionType = this.getActionType(row);
		const esc = frappe.utils.escape_html;
		const adate = row.request_date ? frappe.datetime.str_to_user(row.request_date) : "";
		const pendingWith = row.pending_with || "-";
		const total = row.total_leave_days == null ? "-" : row.total_leave_days;

		const $actions = $(`<div class="vgts-req-row-actions"></div>`);
		$actions.append(
			$(`<button class="btn btn-xs btn-primary">${__("Open")}</button>`).on("click", () => {
				frappe.set_route("Form", row.reference_doctype, row.reference_name);
			}),
		);

		if (actionType) {
			$actions.append(
				$(`<button class="btn btn-xs btn-success">${__("Approve")}</button>`).on("click", () => {
					this.runApprove(row);
				}),
			);
			$actions.append(
				$(`<button class="btn btn-xs btn-danger">${__("Reject")}</button>`).on("click", () => {
					this.runReject(row);
				}),
			);
		}
		return $(`<tr>
			<td>${esc(row.employee_name || "")}</td>
			<td><span class="indicator-pill ${this.statusColor(row.status)}">${esc(row.status || "")}</span></td>
			<td>${esc(adate)}</td>
			<td>${esc(row.reason || "")}</td>
			<td>${esc(String(total))}</td>
			<td>${esc(row.approval_stage || "-")}</td>
			<td>${esc(pendingWith)}</td>
			<td class="vgts-req-id">${esc(row.reference_name || "")}</td>
			<td></td>
		</tr>`).find("td:last").append($actions).end();
	},

	runApprove(row) {
		frappe.call({
			method: "frappe.client.get",
			args: { doctype: row.reference_doctype, name: row.reference_name },
			freeze: true,
			callback: (r) => {
				const doc = r.message;
				if (!doc) return;
				this.dispatchApprove(doc);
			},
		});
	},

	runReject(row) {
		frappe.call({
			method: "frappe.client.get",
			args: { doctype: row.reference_doctype, name: row.reference_name },
			freeze: true,
			callback: (r) => {
				const doc = r.message;
				if (!doc) return;
				this.dispatchReject(doc);
			},
		});
	},

	dispatchApprove(doc) {
		const dt = doc.doctype;
		const refresh = () => frappe.vgts_hr_req_dashboard.refresh();

		if (dt === "Leave Application") {
			const t = this.getLeaveActionType(doc);
			if (!t) return;
			if (t === "primary") {
				frappe.confirm(__("Approve and forward to secondary approver?"), () => {
					frappe.call({
						method: "frappe.client.set_value",
						args: { doctype: dt, name: doc.name, fieldname: "status", value: "Approved" },
						freeze: true,
						callback: (r) => {
							if (!r.exc) {
								frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
								refresh();
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
					callback: (r) => {
						if (r.message && r.message.status === "success") {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							refresh();
						}
					},
				});
			});
			return;
		}

		if (dt === "Attendance Regularization") {
			const t = this.getTwoLevelActionType(doc);
			if (!t) return;
			if (t === "primary_two_level") {
				frappe.confirm(__("Approve and forward to secondary approver?"), () => {
					frappe.call({
						method: "frappe.client.set_value",
						args: { doctype: dt, name: doc.name, fieldname: "status", value: "Approved" },
						freeze: true,
						callback: (r2) => {
							if (!r2.exc) {
								frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
								refresh();
							}
						},
					});
				});
				return;
			}
			const method =
				t === "secondary"
					? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_approve"
					: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_approve_submit";
			frappe.confirm(__("Approve and submit this Attendance Regularization?"), () => {
				frappe.call({
					method,
					args: { attendance_regularization: doc.name },
					freeze: true,
					callback: (r2) => {
						if (r2.message && r2.message.status === "success") {
							frappe.show_alert({ message: r2.message.message, indicator: "green" });
							refresh();
						}
					},
				});
			});
			return;
		}

		if (dt === "Employee Permission") {
			const t = this.getTwoLevelActionType(doc);
			if (!t) return;
			if (t === "primary_two_level") {
				frappe.confirm(__("Approve and forward to secondary approver?"), () => {
					frappe.call({
						method: "frappe.client.set_value",
						args: { doctype: dt, name: doc.name, fieldname: "status", value: "Approved" },
						freeze: true,
						callback: (r2) => {
							if (!r2.exc) {
								frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
								refresh();
							}
						},
					});
				});
				return;
			}
			if (t === "secondary") {
				frappe.confirm(__("Approve and submit this Permission Request?"), () => {
					frappe.call({
						method: "hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_approve",
						args: { employee_permission: doc.name },
						freeze: true,
						callback: (r2) => {
							if (r2.message && r2.message.status === "success") {
								frappe.show_alert({ message: r2.message.message, indicator: "green" });
								refresh();
							}
						},
					});
				});
				return;
			}
			frappe.confirm(__("Approve and submit this Permission Request?"), () => {
				frappe.call({
					method: "hrms.hr.doctype.employee_permission.employee_permission.permission_primary_approve_submit",
					args: { employee_permission: doc.name },
					freeze: true,
					callback: (r2) => {
						if (r2.message && r2.message.status === "success") {
							frappe.show_alert({ message: r2.message.message, indicator: "green" });
							refresh();
						}
					},
				});
			});
			return;
		}

		if (dt === "Attendance Request") {
			const t = this.getAttendanceRequestActionType(doc);
			if (!t) return;
			if (t === "primary_two_level") {
				frappe.confirm(__("Approve and forward to secondary approver?"), () => {
					frappe.call({
						method: "frappe.client.set_value",
						args: { doctype: dt, name: doc.name, fieldname: "status", value: "Approved" },
						freeze: true,
						callback: (r2) => {
							if (!r2.exc) {
								frappe.show_alert({ message: __("Forwarded for secondary approval"), indicator: "blue" });
								refresh();
							}
						},
					});
				});
				return;
			}
			if (t === "secondary") {
				frappe.confirm(__("Approve and submit this Attendance Request?"), () => {
					frappe.call({
						method: "hrms.hr.two_level_approval.secondary_approve",
						args: { doctype: dt, docname: doc.name },
						freeze: true,
						callback: (r2) => {
							if (r2.message && r2.message.status === "success") {
								frappe.show_alert({ message: r2.message.message, indicator: "green" });
								refresh();
							}
						},
					});
				});
				return;
			}
			frappe.confirm(__("Approve and submit this Attendance Request?"), () => {
				frappe.call({
					method: "hrms.hr.doctype.attendance_request.attendance_request.attendance_request_approve_submit",
					args: { attendance_request: doc.name },
					freeze: true,
					callback: (r2) => {
						if (r2.message && r2.message.status === "success") {
							frappe.show_alert({ message: r2.message.message, indicator: "green" });
							refresh();
						}
					},
				});
			});
		}
	},

	dispatchReject(doc) {
		const refresh = () => frappe.vgts_hr_req_dashboard.refresh();
		const reasonDialog = (title, method, argsBuilder) => {
			const d = new frappe.ui.Dialog({
				title,
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
						args: argsBuilder(values.reason),
						freeze: true,
						freeze_message: __("Rejecting…"),
						callback: (r) => {
							if (!r.exc && r.message && r.message.status === "success") {
								frappe.show_alert({ message: r.message.message, indicator: "red" });
								refresh();
							}
						},
					});
				},
			});
			d.show();
		};

		if (doc.doctype === "Leave Application") {
			const t = this.getLeaveActionType(doc);
			if (!t) return;
			const method =
				t === "secondary"
					? "hrms.hr.doctype.leave_application.leave_application.secondary_reject"
					: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject";
			reasonDialog(__("Reject Leave Application"), method, (reason) => ({
				leave_application: doc.name,
				reason,
			}));
			return;
		}

		if (doc.doctype === "Attendance Regularization") {
			const t = this.getTwoLevelActionType(doc);
			if (!t) return;
			const method =
				t === "secondary"
					? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_reject"
					: t === "primary_two_level"
						? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_project_reporting_reject"
						: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_reject_submit";
			reasonDialog(__("Reject Attendance Regularization"), method, (reason) => ({
				attendance_regularization: doc.name,
				reason,
			}));
			return;
		}

		if (doc.doctype === "Employee Permission") {
			const t = this.getTwoLevelActionType(doc);
			if (!t) return;
			if (t === "primary_two_level") {
				reasonDialog(
					__("Reject Permission Request"),
					"hrms.hr.doctype.employee_permission.employee_permission.permission_project_reporting_reject",
					(reason) => ({ employee_permission: doc.name, reason }),
				);
				return;
			}
			if (t === "secondary") {
				reasonDialog(
					__("Reject Permission Request"),
					"hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_reject",
					(reason) => ({ employee_permission: doc.name, reason }),
				);
				return;
			}
			reasonDialog(
				__("Reject Permission Request"),
				"hrms.hr.doctype.employee_permission.employee_permission.permission_primary_reject_submit",
				(reason) => ({ employee_permission: doc.name, reason }),
			);
			return;
		}

		if (doc.doctype === "Attendance Request") {
			const t = this.getAttendanceRequestActionType(doc);
			if (!t) return;
			if (t === "primary_two_level") {
				reasonDialog(
					__("Reject Attendance Request"),
					"hrms.hr.two_level_approval.primary_reject",
					(reason) => ({ doctype: doc.doctype, docname: doc.name, reason }),
				);
				return;
			}
			if (t === "secondary") {
				reasonDialog(
					__("Reject Attendance Request"),
					"hrms.hr.two_level_approval.secondary_reject",
					(reason) => ({ doctype: doc.doctype, docname: doc.name, reason }),
				);
				return;
			}
			reasonDialog(
				__("Reject Attendance Request"),
				"hrms.hr.doctype.attendance_request.attendance_request.attendance_request_reject_submit",
				(reason) => ({ attendance_request: doc.name, reason }),
			);
		}
	},
};