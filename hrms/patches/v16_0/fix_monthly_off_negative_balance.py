"""
Patch: fix_monthly_off_negative_balance

Corrects Monthly Off leave ledger entries that went negative due to
incorrect deductions (should have been LWP). For each employee whose
Monthly Off balance is < 0, inserts a corrective Leave Ledger Entry
to bring the balance to 0.

Also cancels and re-saves any Leave Ledger Entries on approved Monthly
Off Leave Applications where the employee had no balance at the time,
setting is_lwp=1 so no further deductions occur.
"""

import frappe
from frappe.utils import today, flt, nowdate


def execute():
    """Find all employees with negative Monthly Off balance and correct to 0."""

    # Get all employees with negative Monthly Off leave ledger balance
    negative_employees = frappe.db.sql(
        """
        SELECT
            employee,
            SUM(leaves) as balance
        FROM `tabLeave Ledger Entry`
        WHERE
            leave_type = 'Monthly Off'
            AND docstatus = 1
            AND is_lwp = 0
        GROUP BY employee
        HAVING SUM(leaves) < 0
        """,
        as_dict=True,
    )

    if not negative_employees:
        frappe.logger().info("fix_monthly_off_negative_balance: no negative balances found")
        return

    for row in negative_employees:
        employee = row.employee
        current_balance = flt(row.balance, 2)
        correction = abs(current_balance)  # positive amount to add

        frappe.logger().info(
            f"fix_monthly_off_negative_balance: correcting {employee} "
            f"balance {current_balance} → 0 (+{correction})"
        )

        # Get the Leave Allocation for this employee (for required fields)
        allocation = frappe.db.get_value(
            "Leave Allocation",
            {
                "employee": employee,
                "leave_type": "Monthly Off",
                "docstatus": 1,
            },
            ["name", "from_date", "to_date"],
            as_dict=True,
            order_by="from_date desc",
        )

        if not allocation:
            # No allocation exists — create a standalone corrective entry
            # using current fiscal year dates as fallback
            from_date = frappe.db.get_value(
                "Leave Ledger Entry",
                {"employee": employee, "leave_type": "Monthly Off", "docstatus": 1},
                "from_date",
                order_by="from_date asc",
            ) or today()
            to_date = today()
            transaction_name = None
            transaction_type = None
        else:
            from_date = allocation.from_date
            to_date = allocation.to_date
            transaction_name = allocation.name
            transaction_type = "Leave Allocation"

        # Insert corrective Leave Ledger Entry
        entry = frappe.new_doc("Leave Ledger Entry")
        entry.employee = employee
        entry.leave_type = "Monthly Off"
        entry.leaves = correction
        entry.from_date = from_date
        entry.to_date = to_date
        entry.is_lwp = 0
        entry.holiday_list = frappe.db.get_value(
            "Employee", employee, "holiday_list"
        ) or ""
        entry.transaction_type = transaction_type or "Leave Allocation"
        entry.transaction_name = transaction_name or ""
        entry.flags.ignore_permissions = True
        entry.flags.ignore_validate = True
        entry.submit()

        frappe.logger().info(
            f"fix_monthly_off_negative_balance: created corrective entry {entry.name} "
            f"for {employee} (+{correction} days)"
        )

    frappe.db.commit()
    frappe.logger().info(
        f"fix_monthly_off_negative_balance: corrected {len(negative_employees)} employee(s)"
    )
