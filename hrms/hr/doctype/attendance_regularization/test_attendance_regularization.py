# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestAttendanceRegularization(IntegrationTestCase):
	def setUp(self):
		self.employee = frappe.get_doc("Employee", {"status": "Active"})

	def test_regularization_creation(self):
		"""Test basic creation of an Attendance Regularization."""
		reg = frappe.new_doc("Attendance Regularization")
		reg.employee = self.employee.name
		reg.attendance_date = frappe.utils.today()
		reg.reason = "Forgot to Check-in"
		reg.checkin_time = "09:00:00"
		reg.insert()

		self.assertEqual(reg.status, "Open")
		self.assertEqual(reg.employee_name, self.employee.employee_name)

	def test_validate_checkin_before_checkout(self):
		"""Test that check-in time must be before check-out time."""
		reg = frappe.new_doc("Attendance Regularization")
		reg.employee = self.employee.name
		reg.attendance_date = frappe.utils.today()
		reg.reason = "Forgot Both"
		reg.checkin_time = "18:00:00"
		reg.checkout_time = "09:00:00"

		self.assertRaises(frappe.ValidationError, reg.insert)

	def test_total_hours_calculation(self):
		"""Test that total hours are calculated correctly."""
		reg = frappe.new_doc("Attendance Regularization")
		reg.employee = self.employee.name
		reg.attendance_date = frappe.utils.today()
		reg.reason = "Forgot Both"
		reg.checkin_time = "09:00:00"
		reg.checkout_time = "18:00:00"
		reg.insert()

		self.assertEqual(reg.total_hours, 9.0)

	def test_checkin_creation_on_submit(self):
		"""Test that Employee Checkin records are created on submit."""
		reg = frappe.new_doc("Attendance Regularization")
		reg.employee = self.employee.name
		reg.attendance_date = frappe.utils.today()
		reg.reason = "Forgot Both"
		reg.checkin_time = "09:00:00"
		reg.checkout_time = "18:00:00"
		reg.status = "Approved"
		reg.leave_approver = "Administrator"
		reg.insert()
		reg.submit()

		checkins = frappe.get_all(
			"Employee Checkin",
			filters={"attendance_regularization": reg.name},
			fields=["log_type"],
			order_by="time asc",
		)
		self.assertEqual(len(checkins), 2)
		self.assertEqual(checkins[0].log_type, "IN")
		self.assertEqual(checkins[1].log_type, "OUT")

	def test_checkin_deletion_on_cancel(self):
		"""Test that Employee Checkin records are deleted on cancel."""
		reg = frappe.new_doc("Attendance Regularization")
		reg.employee = self.employee.name
		reg.attendance_date = frappe.utils.today()
		reg.reason = "Forgot to Check-in"
		reg.checkin_time = "09:00:00"
		reg.status = "Approved"
		reg.leave_approver = "Administrator"
		reg.insert()
		reg.submit()

		# Verify checkin exists
		checkins = frappe.get_all(
			"Employee Checkin",
			filters={"attendance_regularization": reg.name},
		)
		self.assertTrue(len(checkins) > 0)

		# Cancel and verify deletion
		reg.cancel()
		checkins = frappe.get_all(
			"Employee Checkin",
			filters={"attendance_regularization": reg.name},
		)
		self.assertEqual(len(checkins), 0)
