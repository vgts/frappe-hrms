frappe.pages["leave-requests-live"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Leave Requests Live"),
		single_column: true,
	});

	const app = {
		start: 0,
		status: "all",
		rows: [],
	};

	if (!document.getElementById("leave-live-styles")) {
		const s = document.createElement("style");
		s.id = "leave-live-styles";
		s.textContent = `
			.leave-live-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
			.leave-live-list{display:flex;flex-direction:column;gap:10px}
			.leave-live-card{border:1px solid var(--border-color);border-radius:8px;padding:12px;background:var(--control-bg)}
			.leave-live-row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}
			.leave-live-meta{font-size:12px;color:var(--text-muted);display:flex;gap:12px;flex-wrap:wrap}
			.leave-live-actions{display:flex;gap:6px}
		`;
		document.head.appendChild(s);
	}

	const $toolbar = $("<div class='leave-live-toolbar'></div>").appendTo(page.main);
	const statuses = ["all", "Open", "Approved", "Rejected", "Submitted"];
	statuses.forEach((st, i) => {
		const b = $(`<button class='btn btn-sm ${i === 0 ? "btn-primary" : "btn-default"}'>${__(st === "all" ? "All" : st)}</button>`);
		b.on("click", () => {
			$toolbar.find("button").removeClass("btn-primary").addClass("btn-default");
			b.removeClass("btn-default").addClass("btn-primary");
			app.status = st;
			app.start = 0;
			load(false);
		});
		$toolbar.append(b);
	});

	const $list = $("<div class='leave-live-list'></div>").appendTo(page.main);
	const $moreWrap = $("<div style='text-align:center;padding:12px'></div>").appendTo(page.main);
	const $more = $(`<button class='btn btn-default btn-sm'>${__("Load more")}</button>`).appendTo($moreWrap);
	$more.on("click", () => load(true));

	function actionType(doc) {
		if (frappe.utils.cint(doc.docstatus) !== 0) return null;
		const user = frappe.session.user;
		const hasSecondary = !!doc.custom_secondary_leave_approver;
		if (hasSecondary && doc.custom_approval_stage === "Pending Secondary Reporting Approval" && user === doc.custom_secondary_leave_approver) return "secondary";
		if (hasSecondary && doc.custom_approval_stage === "Pending Project Reporting Approval" && user === doc.leave_approver) return "primary";
		return null;
	}

	function render() {
		$list.empty();
		if (!app.rows.length) {
			$list.append(`<div style='padding:40px;text-align:center;color:var(--text-muted)'>${__("No leave requests found")}</div>`);
			return;
		}
		app.rows.forEach((r) => {
			const status = frappe.utils.escape_html(r.status || "");
			const stage = frappe.utils.escape_html(r.approval_stage || "-");
			const pending = frappe.utils.escape_html(r.pending_with || "-");
			const emp = frappe.utils.escape_html(r.employee_name || "");
			const id = frappe.utils.escape_html(r.reference_name || "");
			const leaveType = frappe.utils.escape_html(r.reason || "");
			const dt = r.request_date ? frappe.datetime.str_to_user(r.request_date) : "";

			const $card = $(`<div class='leave-live-card'>
				<div class='leave-live-row'>
					<div><strong>${emp}</strong> <span class='indicator-pill ${status === "Approved" ? "green" : status === "Rejected" ? "red" : "orange"}'>${status}</span></div>
					<div class='leave-live-actions'></div>
				</div>
				<div class='leave-live-meta'>
					<span><b>${__("ID")}:</b> ${id}</span>
					<span><b>${__("Date")}:</b> ${dt}</span>
					<span><b>${__("Leave Type")}:</b> ${leaveType}</span>
					<span><b>${__("Stage")}:</b> ${stage}</span>
					<span><b>${__("Pending With")}:</b> ${pending}</span>
				</div>
			</div>`);
			const $actions = $card.find(".leave-live-actions");
			$actions.append($(`<button class='btn btn-xs btn-primary'>${__("Open")}</button>`).on("click", () => frappe.set_route("Form", "Leave Application", r.reference_name)));
			const t = actionType(r);
			if (t) {
				$actions.append($(`<button class='btn btn-xs btn-success'>${__("Approve")}</button>`).on("click", () => approve(r, t)));
				$actions.append($(`<button class='btn btn-xs btn-danger'>${__("Reject")}</button>`).on("click", () => reject(r, t)));
			}
			$list.append($card);
		});
	}

	function approve(row, t) {
		if (t === "primary") {
			frappe.call({ method: "frappe.client.set_value", args: { doctype: "Leave Application", name: row.reference_name, fieldname: "status", value: "Approved" }, callback: () => load(false) });
			return;
		}
		frappe.call({ method: "hrms.hr.doctype.leave_application.leave_application.secondary_approve", args: { leave_application: row.reference_name }, callback: () => load(false) });
	}

	function reject(row, t) {
		const d = new frappe.ui.Dialog({
			title: __("Reject Leave Application"),
			fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
			primary_action_label: __("Reject"),
			primary_action(v) {
				d.hide();
				const method = t === "secondary"
					? "hrms.hr.doctype.leave_application.leave_application.secondary_reject"
					: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject";
				frappe.call({ method, args: { leave_application: row.reference_name, reason: v.reason }, callback: () => load(false) });
			},
		});
		d.show();
	}

	function load(append) {
		const limit = 40;
		const start = append ? app.start : 0;
		frappe.call({
			method: "hrms.hr.doctype.vgts_hr_request.vgts_hr_request.get_dashboard_data",
			args: { limit_start: start, limit_page_length: limit, status_filter: app.status },
			freeze: !append,
			callback(r) {
				const rows = (r.message || []).map((x) => ({ ...x, doctype: "Leave Application" }));
				app.rows = append ? app.rows.concat(rows) : rows;
				app.start = app.rows.length;
				$more.toggle(rows.length >= limit);
				render();
			},
		});
	}

	load(false);
};
