frappe.listview_settings["Leave Application"] = {
	add_fields: [
		"leave_type",
		"employee",
		"employee_name",
		"total_leave_days",
		"from_date",
		"to_date",
		"custom_approval_stage",
	],
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		// Show approval stage when pending secondary
		if (
			doc.status === "Approved" &&
			doc.custom_approval_stage === "Pending Secondary Approver" &&
			!doc.docstatus
		) {
			return [__("Pending Secondary Approver"), "yellow", "custom_approval_stage,=,Pending Secondary Approver"];
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
};
