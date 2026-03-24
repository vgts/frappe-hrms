<template>
	<BaseLayout @refresh="refreshAll">
		<template #body>
			<div class="flex flex-col items-center my-7 p-4 gap-7">
				<CheckInPanel />
				<TeamCheckinSummary ref="teamSummary" />
				<RequestPanel ref="requestPanel" />
				<QuickLinks :items="quickLinks" :title="__('Quick Links')" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, markRaw, onMounted, onUnmounted, ref } from "vue"

import CheckInPanel from "@/components/CheckInPanel.vue"
import TeamCheckinSummary from "@/components/TeamCheckinSummary.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ShiftIcon from "@/components/icons/ShiftIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"

import { myLeaves, teamLeaves } from "@/data/leaves"
import { myAttendanceRequests, myShiftRequests, teamShiftRequests, teamAttendanceRequests } from "@/data/attendance"
import { myClaims, teamClaims } from "@/data/claims"
import { myPermissions, teamPermissions, permissionBalance } from "@/data/permissions"
import { myRegularizations, teamRegularizations } from "@/data/regularization"

const __ = inject("$translate")

// Reload all data resources
function refreshAll() {
	myLeaves.reload()
	teamLeaves.reload()
	myAttendanceRequests.reload()
	teamAttendanceRequests.reload()
	myShiftRequests.reload()
	teamShiftRequests.reload()
	myClaims.reload()
	teamClaims.reload()
	myPermissions.reload()
	teamPermissions.reload()
	permissionBalance.reload()
	myRegularizations.reload()
	teamRegularizations.reload()
}

// Auto-refetch when app comes back to foreground (tab focus / app resume)
function onVisibilityChange() {
	if (document.visibilityState === "visible") {
		refreshAll()
	}
}

onMounted(() => {
	document.addEventListener("visibilitychange", onVisibilityChange)
})

onUnmounted(() => {
	document.removeEventListener("visibilitychange", onVisibilityChange)
})

const quickLinks = [
	{
		icon: markRaw(AttendanceIcon),
		title: __("Request Attendance"),
		route: "AttendanceRequestFormView",
	},
	{
		icon: markRaw(ShiftIcon),
		title: __("Request a Shift"),
		route: "ShiftRequestFormView",
	},
	{
		icon: markRaw(LeaveIcon),
		title: __("Request Leave"),
		route: "LeaveApplicationFormView",
	},
	{
		icon: markRaw(ExpenseIcon),
		title: __("Claim an Expense"),
		route: "ExpenseClaimFormView",
	},
	{
		icon: markRaw(AttendanceIcon),
		title: __("Request Permission"),
		route: "PermissionFormView",
	},
	{
		icon: markRaw(AttendanceIcon),
		title: __("Regularization"),
		route: "RegularizationFormView",
	},
	{
		icon: markRaw(EmployeeAdvanceIcon),
		title: __("Request an Advance"),
		route: "EmployeeAdvanceFormView",
	},
	{
		icon: markRaw(SalaryIcon),
		title: __("View Salary Slips"),
		route: "SalarySlipsDashboard",
	},
]
</script>
