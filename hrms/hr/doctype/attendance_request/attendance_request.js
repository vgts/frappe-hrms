// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on("Attendance Request", {
	setup(frm) {
		frm.set_query("approver", function () {
			return {
				query: "hrms.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: "Leave Application",
				},
			};
		});
		frm.set_query("employee", erpnext.queries.employee);
	},

	refresh(frm) {
		frm.trigger("show_attendance_warnings");
	},

	employee(frm) {
		frm.trigger("set_approver");
	},

	set_approver(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_leave_approver",
				args: { employee: frm.doc.employee },
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("approver", r.message);
					}
				},
			});
		}
	},

	show_attendance_warnings(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.dashboard.clear_headline();

			frm.call("get_attendance_warnings").then((r) => {
				if (r.message?.length) {
					frm.dashboard.reset();
					frm.dashboard.add_section(
						frappe.render_template("attendance_warnings", {
							warnings: r.message || [],
						}),
						__("Attendance Warnings"),
					);
					frm.dashboard.show();
				}
			});
		}
	},
});
