frappe.listview_settings["VGTS HR Request"] = {
	add_fields: [
		"request_type",
		"reference_doctype",
		"reference_name",
		"employee_name",
		"status",
		"request_date",
		"reason",
		"approval_stage",
		"approver_name",
	],

	onload(listview) {
		if (!document.getElementById("vgts-hr-requests-action-styles")) {
			const style = document.createElement("style");
			style.id = "vgts-hr-requests-action-styles";
			style.textContent = `
				.list-row .inner-group-button[data-label="Actions"] {
					min-width: 100px;
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
				get_label: __("Open"),
				get_description: (doc) =>
					__("Open {0}", [doc.reference_doctype || doc.request_type || "Document"]),
				show: () => true,
				action: (doc) => {
					if (doc.reference_doctype && doc.reference_name) {
						frappe.set_route("Form", doc.reference_doctype, doc.reference_name);
					}
				},
			},
		],
	},
};

