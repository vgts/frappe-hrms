<template>
	<BaseLayout @refresh="refreshAll">
		<template #body>
			<div class="p-4 pb-8 lg:p-6 lg:pb-10 lg:max-w-6xl lg:mx-auto flex flex-col gap-5 lg:gap-6">

				<!-- Mobile: single column -->
				<div class="lg:hidden flex flex-col gap-5">
					<CheckInPanel />
					<TeamCheckinSummary />
					<DepartmentCheckinSummary />
				</div>

				<!-- Desktop top row: CheckIn + Reporting Check-ins side by side -->
				<div class="hidden lg:grid lg:grid-cols-2 lg:gap-6 lg:items-start">
					<CheckInPanel />
					<div class="flex flex-col gap-4">
						<TeamCheckinSummary />
						<DepartmentCheckinSummary />
					</div>
				</div>

				<!-- Requests: stacked on mobile, side-by-side on desktop -->
				<RequestPanel ref="requestPanel" />

				<!-- Quick Links: mobile only -->
				<QuickLinks class="lg:hidden" :items="quickLinks" :title="__('Quick Links')" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, markRaw, onMounted, onUnmounted, ref } from "vue"

import CheckInPanel from "@/components/CheckInPanel.vue"
import TeamCheckinSummary from "@/components/TeamCheckinSummary.vue"
import DepartmentCheckinSummary from "@/components/DepartmentCheckinSummary.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ShiftIcon from "@/components/icons/ShiftIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"

import { myLeaves, teamLeaves } from "@/data/leaves"
import { myAttendanceRequests, myShiftRequests, teamShiftRequests, teamAttendanceRequests } from "@/data/attendance"
import { myClaims, teamClaims } from "@/data/claims"
import { myPermissions, teamPermissions, permissionBalance } from "@/data/permissions"
import { myRegularizations, teamRegularizations } from "@/data/regularization"
import { myCompensatoryRequests, teamCompensatoryRequests } from "@/data/compensatory"

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
	myCompensatoryRequests.reload()
	teamCompensatoryRequests.reload()
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
		title: __("Request"),
		route: "AttendanceRequestFormView",
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
		icon: markRaw(LeaveIcon),
		title: __("Compensatory Request"),
		route: "CompensatoryLeaveFormView",
	},
]
</script>
