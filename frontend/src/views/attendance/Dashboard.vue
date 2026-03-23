<template>
	<BaseLayout pageTitle="Attendance">
		<template #body>
			<div class="flex flex-col mt-4 mb-7 p-4 gap-5">
				<!-- Tab Buttons -->
				<TabButtons :buttons="TAB_BUTTONS" v-model="activeTab" />

				<!-- My Attendance Tab -->
				<div v-if="activeTab === 'My Attendance'" class="flex flex-col gap-7">
					<AttendanceCalendar />
					<div class="w-full">
						<router-link :to="{ name: 'AttendanceRequestFormView' }" v-slot="{ navigate }">
							<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
								{{ __("Request Attendance") }}
							</Button>
						</router-link>
					</div>
					<div>
						<div class="text-lg text-gray-800 font-bold">{{ __("Recent Attendance Requests") }}</div>
						<RequestList
							:component="markRaw(AttendanceRequestItem)"
							:items="myAttendanceRequests?.data?.slice(0, 5)"
							:addListButton="true"
							:listButtonRoute="__('AttendanceRequestListView')"
						/>
					</div>
					<div>
						<div class="text-lg text-gray-800 font-bold">{{ __("Upcoming Shifts") }}</div>
						<RequestList
							:component="markRaw(ShiftAssignmentItem)"
							:items="upcomingShifts"
							:addListButton="true"
							listButtonRoute="ShiftAssignmentListView"
							:emptyStateMessage="__('You have no upcoming shifts')"
						/>
					</div>
					<div class="w-full">
						<router-link :to="{ name: 'ShiftRequestFormView' }" v-slot="{ navigate }">
							<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
								{{ __("Request a Shift") }}
							</Button>
						</router-link>
					</div>
					<div>
						<div class="text-lg text-gray-800 font-bold">{{ __("Recent Shift Requests") }}</div>
						<RequestList
							:component="markRaw(ShiftRequestItem)"
							:items="myShiftRequests?.data?.slice(0, 5)"
							:addListButton="true"
							listButtonRoute="ShiftRequestListView"
						/>
					</div>
				</div>

				<!-- Team Attendance Tab -->
				<div v-else-if="activeTab === 'Team Attendance'" class="flex flex-col gap-4">
					<!-- Breadcrumb for nested navigation -->
					<div v-if="breadcrumb.length > 1" class="flex items-center gap-1 text-sm overflow-x-auto">
						<template v-for="(crumb, idx) in breadcrumb" :key="crumb.employee">
							<span
								v-if="idx > 0"
								class="text-gray-400 flex-shrink-0"
							>/</span>
							<span
								@click="navigateTo(idx)"
								class="cursor-pointer flex-shrink-0"
								:class="idx === breadcrumb.length - 1 ? 'text-gray-900 font-medium' : 'text-blue-600'"
							>
								{{ crumb.name }}
							</span>
						</template>
					</div>

					<!-- Summary Chips -->
					<div v-if="teamData.data?.length" class="flex gap-2 flex-wrap">
						<div class="flex items-center gap-1.5 bg-green-50 text-green-700 rounded-full px-3 py-1.5 text-xs font-medium">
							<div class="w-2 h-2 rounded-full bg-green-500"></div>
							{{ checkedInCount }} {{ __("In") }}
						</div>
						<div class="flex items-center gap-1.5 bg-blue-50 text-blue-700 rounded-full px-3 py-1.5 text-xs font-medium">
							<div class="w-2 h-2 rounded-full bg-blue-500"></div>
							{{ checkedOutCount }} {{ __("Out") }}
						</div>
						<div class="flex items-center gap-1.5 bg-gray-100 text-gray-600 rounded-full px-3 py-1.5 text-xs font-medium">
							<div class="w-2 h-2 rounded-full bg-gray-400"></div>
							{{ notCheckedInCount }} {{ __("Absent") }}
						</div>
					</div>

					<!-- Team Members List -->
					<div v-if="teamData.data?.length" class="flex flex-col bg-white rounded-lg overflow-hidden">
						<div
							v-for="member in teamData.data"
							:key="member.employee"
							class="flex items-center gap-3 p-3 border-b last:border-b-0 cursor-pointer"
							@click="member.has_reports ? drillDown(member) : null"
						>
							<Avatar
								:label="member.employee_name"
								:image="member.image"
								size="lg"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-medium text-gray-900 truncate">
									{{ member.employee_name }}
								</div>
								<div class="text-xs text-gray-500 truncate">
									{{ member.designation || member.department }}
								</div>
							</div>
							<div class="flex flex-col items-end gap-1">
								<Badge
									:theme="statusTheme(member.status)"
									:label="statusLabel(member.status)"
									variant="subtle"
									size="sm"
								/>
								<div v-if="member.first_in" class="text-[10px] text-gray-500">
									<span class="text-green-600">{{ formatTime(member.first_in) }}</span>
									<span v-if="member.last_out" class="mx-0.5">-</span>
									<span v-if="member.last_out" class="text-blue-600">{{ formatTime(member.last_out) }}</span>
								</div>
							</div>
							<!-- Drill-down arrow for members with reports -->
							<FeatherIcon
								v-if="member.has_reports"
								name="chevron-right"
								class="h-4 w-4 text-gray-400 flex-shrink-0"
							/>
						</div>
					</div>

					<EmptyState
						v-else
						:message="teamData.loading ? __('Loading...') : __('No team members found')"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw, ref, reactive } from "vue"
import { createResource, Avatar, Badge, FeatherIcon } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import TabButtons from "@/components/TabButtons.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import RequestList from "@/components/RequestList.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"
import EmptyState from "@/components/EmptyState.vue"

import {
	getShiftDates,
	getTotalShiftDays,
	getShiftTiming,
	myAttendanceRequests,
	myShiftRequests,
} from "@/data/attendance"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const employee = inject("$employee")

const activeTab = ref("My Attendance")
const TAB_BUTTONS = ["My Attendance", "Team Attendance"]

// Current manager being viewed (for nested drill-down)
const currentManager = ref(null)
const breadcrumb = reactive([
	{ employee: null, name: employee.data?.employee_name || "My Team" },
])

// Team checkin data
const teamData = createResource({
	url: "hrms.api.get_team_checkins",
	params: {
		date: dayjs().format("YYYY-MM-DD"),
		manager: currentManager.value,
	},
	auto: true,
	cache: "hrms:team_checkins",
})

// Drill down into a team member's reports
function drillDown(member) {
	currentManager.value = member.employee
	breadcrumb.push({ employee: member.employee, name: member.employee_name })
	teamData.fetch({ date: dayjs().format("YYYY-MM-DD"), manager: member.employee })
}

// Navigate back in breadcrumb
function navigateTo(idx) {
	if (idx === breadcrumb.length - 1) return
	const crumb = breadcrumb[idx]
	currentManager.value = crumb.employee
	breadcrumb.splice(idx + 1)
	teamData.fetch({ date: dayjs().format("YYYY-MM-DD"), manager: crumb.employee })
}

// Summary counts
const checkedInCount = computed(() =>
	(teamData.data || []).filter(m => m.status === "Checked In").length
)
const checkedOutCount = computed(() =>
	(teamData.data || []).filter(m => m.status === "Checked Out").length
)
const notCheckedInCount = computed(() =>
	(teamData.data || []).filter(m => m.status === "Not Checked In").length
)

const formatTime = (datetime) => {
	if (!datetime) return ""
	return dayjs(datetime).format("hh:mm A")
}

const statusTheme = (status) => {
	if (status === "Checked In") return "green"
	if (status === "Checked Out") return "blue"
	return "gray"
}

const statusLabel = (status) => {
	if (status === "Checked In") return __("In")
	if (status === "Checked Out") return __("Out")
	return __("Absent")
}

// Shifts data (for My Attendance tab)
const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	transform: (data) => {
		return data.map((assignment) => {
			assignment.doctype = "Shift Assignment"
			assignment.is_upcoming = !assignment.end_date || dayjs(assignment.end_date).isAfter(dayjs())
			assignment.shift_dates = getShiftDates(assignment)
			assignment.total_shift_days = getTotalShiftDays(assignment)
			assignment.shift_timing = getShiftTiming(assignment)
			return assignment
		})
	},
})

const upcomingShifts = computed(() => {
	return shifts.data?.filter((shift) => shift.is_upcoming)?.slice(0, 5)
})
</script>
