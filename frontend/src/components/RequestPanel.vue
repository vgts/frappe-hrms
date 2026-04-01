<template>
	<div class="w-full">

		<!-- Mobile: tabs (one column at a time) -->
		 
		<div class="lg:hidden">
			<TabButtons :buttons="TAB_BUTTONS" v-model="activeTab" />

			<div v-if="activeTab == 'My Requests'" class="flex flex-col gap-4 mt-2">
				<RequestSection :title="__('Leave Requests')"      :items="myLeaveItems"         :component="LeaveRequestItem"         listRoute="LeaveApplicationListView" />
				<RequestSection :title="__('Attendance / OnDuty')" :items="myAttendanceItems"     :component="AttendanceRequestItem"    listRoute="AttendanceRequestListView" />
				<RequestSection :title="__('Regularization')"      :items="myRegularizationItems" :component="RegularizationRequestItem" listRoute="RegularizationListView" />
				<RequestSection :title="__('Permission')"           :items="myPermissionItems"     :component="PermissionRequestItem"    listRoute="PermissionListView" />
				<RequestSection :title="__('Shift Requests')"       :items="myShiftItems"          :component="ShiftRequestItem"         listRoute="ShiftRequestListView" />
				<RequestSection :title="__('Expense Claims')"       :items="myClaimItems"          :component="ExpenseClaimItem"         listRoute="ExpenseClaimListView" />
			</div>

			<div v-else-if="activeTab == 'Team Requests'" class="flex flex-col gap-4 mt-2">
				<RequestSection :title="__('Leave Requests')"      :items="teamLeaveItems"         :component="LeaveRequestItem"         :teamRequests="true" listRoute="LeaveApplicationListView" />
				<RequestSection :title="__('Attendance / OnDuty')" :items="teamAttendanceItems"    :component="AttendanceRequestItem"    :teamRequests="true" listRoute="AttendanceRequestListView" />
				<RequestSection :title="__('Regularization')"      :items="teamRegularizationItems" :component="RegularizationRequestItem" :teamRequests="true" listRoute="RegularizationListView" />
				<RequestSection :title="__('Permission')"           :items="teamPermissionItems"    :component="PermissionRequestItem"    :teamRequests="true" listRoute="PermissionListView" />
				<RequestSection :title="__('Shift Requests')"       :items="teamShiftItems"         :component="ShiftRequestItem"         :teamRequests="true" listRoute="ShiftRequestListView" />
				<RequestSection :title="__('Expense Claims')"       :items="teamClaimItems"         :component="ExpenseClaimItem"         :teamRequests="true" listRoute="ExpenseClaimListView" />
			</div>
		</div>

		<!-- Desktop: My Requests + Team Requests side-by-side -->
		<div class="hidden lg:grid lg:grid-cols-2 lg:gap-6 lg:items-start">

			<!-- My Requests card -->
			<div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
				<div class="px-4 py-3 border-b border-gray-100 bg-gray-50">
					<span class="text-sm font-bold text-gray-700">{{ __("My Requests") }}</span>
				</div>
				<div class="flex flex-col gap-3 p-4">
					<RequestSection :title="__('Leave Requests')"      :items="myLeaveItems"         :component="LeaveRequestItem"         listRoute="LeaveApplicationListView" />
					<RequestSection :title="__('Attendance / OnDuty')" :items="myAttendanceItems"     :component="AttendanceRequestItem"    listRoute="AttendanceRequestListView" />
					<RequestSection :title="__('Regularization')"      :items="myRegularizationItems" :component="RegularizationRequestItem" listRoute="RegularizationListView" />
					<RequestSection :title="__('Permission')"           :items="myPermissionItems"     :component="PermissionRequestItem"    listRoute="PermissionListView" />
					<RequestSection :title="__('Shift Requests')"       :items="myShiftItems"          :component="ShiftRequestItem"         listRoute="ShiftRequestListView" />
					<RequestSection :title="__('Expense Claims')"       :items="myClaimItems"          :component="ExpenseClaimItem"         listRoute="ExpenseClaimListView" />
					<p v-if="!hasMyRequests" class="text-sm text-gray-400 text-center py-6">{{ __("No pending requests") }}</p>
				</div>
			</div>

			<!-- Team Requests card -->
			<div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
				<div class="px-4 py-3 border-b border-gray-100 bg-gray-50">
					<span class="text-sm font-bold text-gray-700">{{ __("Team Requests") }}</span>
				</div>
				<div class="flex flex-col gap-3 p-4">
					<RequestSection :title="__('Leave Requests')"      :items="teamLeaveItems"         :component="LeaveRequestItem"         :teamRequests="true" listRoute="LeaveApplicationListView" />
					<RequestSection :title="__('Attendance / OnDuty')" :items="teamAttendanceItems"    :component="AttendanceRequestItem"    :teamRequests="true" listRoute="AttendanceRequestListView" />
					<RequestSection :title="__('Regularization')"      :items="teamRegularizationItems" :component="RegularizationRequestItem" :teamRequests="true" listRoute="RegularizationListView" />
					<RequestSection :title="__('Permission')"           :items="teamPermissionItems"    :component="PermissionRequestItem"    :teamRequests="true" listRoute="PermissionListView" />
					<RequestSection :title="__('Shift Requests')"       :items="teamShiftItems"         :component="ShiftRequestItem"         :teamRequests="true" listRoute="ShiftRequestListView" />
					<RequestSection :title="__('Expense Claims')"       :items="teamClaimItems"         :component="ExpenseClaimItem"         :teamRequests="true" listRoute="ExpenseClaimListView" />
					<p v-if="!hasTeamRequests" class="text-sm text-gray-400 text-center py-6">{{ __("No pending team requests") }}</p>
				</div>
			</div>
		</div>

	</div>
</template>

<script setup>
import { ref, inject, onMounted, onUnmounted, computed, markRaw } from "vue"

import TabButtons from "@/components/TabButtons.vue"
import RequestSection from "@/components/RequestSection.vue"

import { myAttendanceRequests, myShiftRequests, teamShiftRequests, teamAttendanceRequests } from "@/data/attendance"
import { myClaims, teamClaims } from "@/data/claims"
import { myLeaves, teamLeaves } from "@/data/leaves"
import { myPermissions, teamPermissions } from "@/data/permissions"
import { myRegularizations, teamRegularizations } from "@/data/regularization"

import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import PermissionRequestItem from "@/components/PermissionRequestItem.vue"
import RegularizationRequestItem from "@/components/RegularizationRequestItem.vue"

import { useListUpdate } from "@/composables/realtime"

const __ = inject("$translate")
const activeTab = ref("My Requests")
const socket = inject("$socket")

const TAB_BUTTONS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")

// My requests - separated by type
const myLeaveItems = computed(() => (myLeaves?.data || []).slice(0, 5))
const myAttendanceItems = computed(() => (myAttendanceRequests?.data || []).slice(0, 5))
const myShiftItems = computed(() => (myShiftRequests?.data || []).slice(0, 5))
const myClaimItems = computed(() => (myClaims?.data || []).slice(0, 5))
const myPermissionItems = computed(() => (myPermissions?.data || []).slice(0, 5))
const myRegularizationItems = computed(() => (myRegularizations?.data || []).slice(0, 5))

// Team requests - separated by type
const teamLeaveItems = computed(() => (teamLeaves?.data || []).slice(0, 5))
const teamAttendanceItems = computed(() => (teamAttendanceRequests?.data || []).slice(0, 5))
const teamShiftItems = computed(() => (teamShiftRequests?.data || []).slice(0, 5))
const teamClaimItems = computed(() => (teamClaims?.data || []).slice(0, 5))
const teamPermissionItems = computed(() => (teamPermissions?.data || []).slice(0, 5))
const teamRegularizationItems = computed(() => (teamRegularizations?.data || []).slice(0, 5))

const hasMyRequests = computed(() =>
	myLeaveItems.value.length > 0 ||
	myAttendanceItems.value.length > 0 ||
	myShiftItems.value.length > 0 ||
	myClaimItems.value.length > 0 ||
	myPermissionItems.value.length > 0 ||
	myRegularizationItems.value.length > 0
)

const hasTeamRequests = computed(() =>
	teamLeaveItems.value.length > 0 ||
	teamAttendanceItems.value.length > 0 ||
	teamShiftItems.value.length > 0 ||
	teamClaimItems.value.length > 0 ||
	teamPermissionItems.value.length > 0 ||
	teamRegularizationItems.value.length > 0
)

let pollInterval = null

function reloadTeamData() {
	teamLeaves.reload()
	teamAttendanceRequests.reload()
	teamShiftRequests.reload()
	teamClaims.reload()
	teamPermissions.reload()
	teamRegularizations.reload()
}

function onVisibilityChange() {
	if (document.visibilityState === "visible") {
		reloadTeamData()
	}
}

onMounted(() => {
	useListUpdate(socket, "Leave Application", () => teamLeaves.reload())
	useListUpdate(socket, "Expense Claim", () => teamClaims.reload())
	useListUpdate(socket, "Shift Request", () => teamShiftRequests.reload())
	useListUpdate(socket, "Attendance Request", () => teamAttendanceRequests.reload())
	useListUpdate(socket, "Employee Permission", () => teamPermissions.reload())
	useListUpdate(socket, "Attendance Regularization", () => teamRegularizations.reload())

	// Reload when app comes back to foreground (fixes iOS Safari PWA missed socket events)
	document.addEventListener("visibilitychange", onVisibilityChange)

	// Fallback polling every 30s in case Socket.IO is not connected
	pollInterval = setInterval(() => {
		if (!socket.connected) {
			reloadTeamData()
		}
	}, 30000)
})

onUnmounted(() => {
	document.removeEventListener("visibilitychange", onVisibilityChange)
	if (pollInterval) clearInterval(pollInterval)
})
</script>
