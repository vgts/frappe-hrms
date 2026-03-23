<template>
	<div class="w-full">
		<TabButtons
			:buttons="TAB_BUTTONS"
			v-model="activeTab"
		/>

		<div v-if="activeTab == 'My Requests'" class="flex flex-col gap-4 mt-2">
			<RequestSection
				:title="__('Leave Requests')"
				:items="myLeaveItems"
				:component="LeaveRequestItem"
				listRoute="LeaveApplicationListView"
			/>
			<RequestSection
				:title="__('Attendance / OnDuty')"
				:items="myAttendanceItems"
				:component="AttendanceRequestItem"
				listRoute="AttendanceRequestListView"
			/>
			<RequestSection
				:title="__('Regularization')"
				:items="myRegularizationItems"
				:component="RegularizationRequestItem"
				listRoute="RegularizationListView"
			/>
			<RequestSection
				:title="__('Permission')"
				:items="myPermissionItems"
				:component="PermissionRequestItem"
				listRoute="PermissionListView"
			/>
			<RequestSection
				:title="__('Shift Requests')"
				:items="myShiftItems"
				:component="ShiftRequestItem"
				listRoute="ShiftRequestListView"
			/>
			<RequestSection
				:title="__('Expense Claims')"
				:items="myClaimItems"
				:component="ExpenseClaimItem"
				listRoute="ExpenseClaimListView"
			/>
		</div>

		<div v-else-if="activeTab == 'Team Requests'" class="flex flex-col gap-4 mt-2">
			<RequestSection
				:title="__('Leave Requests')"
				:items="teamLeaveItems"
				:component="LeaveRequestItem"
				:teamRequests="true"
				listRoute="LeaveApplicationListView"
			/>
			<RequestSection
				:title="__('Attendance / OnDuty')"
				:items="teamAttendanceItems"
				:component="AttendanceRequestItem"
				:teamRequests="true"
				listRoute="AttendanceRequestListView"
			/>
			<RequestSection
				:title="__('Regularization')"
				:items="teamRegularizationItems"
				:component="RegularizationRequestItem"
				:teamRequests="true"
				listRoute="RegularizationListView"
			/>
			<RequestSection
				:title="__('Permission')"
				:items="teamPermissionItems"
				:component="PermissionRequestItem"
				:teamRequests="true"
				listRoute="PermissionListView"
			/>
			<RequestSection
				:title="__('Shift Requests')"
				:items="teamShiftItems"
				:component="ShiftRequestItem"
				:teamRequests="true"
				listRoute="ShiftRequestListView"
			/>
			<RequestSection
				:title="__('Expense Claims')"
				:items="teamClaimItems"
				:component="ExpenseClaimItem"
				:teamRequests="true"
				listRoute="ExpenseClaimListView"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, inject, onMounted, computed, markRaw } from "vue"

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

onMounted(() => {
	useListUpdate(socket, "Leave Application", () => teamLeaves.reload())
	useListUpdate(socket, "Expense Claim", () => teamClaims.reload())
	useListUpdate(socket, "Shift Request", () => teamShiftRequests.reload())
	useListUpdate(socket, "Attendance Request", () => teamAttendanceRequests.reload())
	useListUpdate(socket, "Employee Permission", () => teamPermissions.reload())
	useListUpdate(socket, "Attendance Regularization", () => teamRegularizations.reload())
})
</script>
