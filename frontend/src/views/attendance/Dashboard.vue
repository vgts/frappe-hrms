<template>
	<BaseLayout pageTitle="Attendance">
		<template #body>
			<div class="px-4 pt-4 pb-8 lg:px-8 lg:pt-6 lg:pb-12 lg:max-w-6xl lg:mx-auto flex flex-col gap-5">

				<!-- Tab Buttons -->
				<TabButtons :buttons="TAB_BUTTONS" v-model="activeTab" />

				<!-- ── My Attendance Tab ── -->
				<div v-if="activeTab === 'My Attendance'">

					<!-- Mobile: single column -->
					<div class="lg:hidden flex flex-col gap-7">
						<AttendanceCalendar />
						<router-link :to="{ name: 'AttendanceRequestFormView' }" v-slot="{ navigate }">
							<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
								{{ __("Request Attendance") }}
							</Button>
						</router-link>
						<div>
							<div class="section-title">{{ __("Recent Attendance Requests") }}</div>
							<RequestList
								:component="markRaw(AttendanceRequestItem)"
								:items="myAttendanceRequests?.data?.slice(0, 5)"
								:addListButton="true"
								:listButtonRoute="__('AttendanceRequestListView')"
							/>
						</div>
						<div>
							<div class="section-title">{{ __("Upcoming Shifts") }}</div>
							<RequestList
								:component="markRaw(ShiftAssignmentItem)"
								:items="upcomingShifts"
								:addListButton="true"
								listButtonRoute="ShiftAssignmentListView"
								:emptyStateMessage="__('You have no upcoming shifts')"
							/>
						</div>
						<router-link :to="{ name: 'ShiftRequestFormView' }" v-slot="{ navigate }">
							<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
								{{ __("Request a Shift") }}
							</Button>
						</router-link>
						<div>
							<div class="section-title">{{ __("Recent Shift Requests") }}</div>
							<RequestList
								:component="markRaw(ShiftRequestItem)"
								:items="myShiftRequests?.data?.slice(0, 5)"
								:addListButton="true"
								listButtonRoute="ShiftRequestListView"
							/>
						</div>
					</div>

					<!-- Desktop: two-column -->
					<div class="hidden lg:grid lg:grid-cols-2 lg:gap-8 lg:items-start">
						<!-- Left: calendar -->
						<div class="flex flex-col gap-5">
							<div class="desk-card p-5">
								<AttendanceCalendar />
							</div>
						</div>

						<!-- Right: requests & shifts -->
						<div class="flex flex-col gap-5">
							<div class="desk-card p-5 flex flex-col gap-4">
								<div class="section-title">{{ __("Attendance Requests") }}</div>
								<router-link :to="{ name: 'AttendanceRequestFormView' }" v-slot="{ navigate }">
									<Button @click="navigate" variant="solid" class="w-full py-4 text-sm">
										{{ __("+ Request Attendance") }}
									</Button>
								</router-link>
								<RequestList
									:component="markRaw(AttendanceRequestItem)"
									:items="myAttendanceRequests?.data?.slice(0, 5)"
									:addListButton="true"
									:listButtonRoute="__('AttendanceRequestListView')"
								/>
							</div>

							<div class="desk-card p-5 flex flex-col gap-4">
								<div class="section-title">{{ __("Shifts") }}</div>
								<router-link :to="{ name: 'ShiftRequestFormView' }" v-slot="{ navigate }">
									<Button @click="navigate" variant="solid" class="w-full py-4 text-sm">
										{{ __("+ Request a Shift") }}
									</Button>
								</router-link>
								<div class="text-sm font-semibold text-gray-600 mt-1">{{ __("Upcoming Shifts") }}</div>
								<RequestList
									:component="markRaw(ShiftAssignmentItem)"
									:items="upcomingShifts"
									:addListButton="true"
									listButtonRoute="ShiftAssignmentListView"
									:emptyStateMessage="__('You have no upcoming shifts')"
								/>
								<div class="text-sm font-semibold text-gray-600 mt-1">{{ __("Recent Shift Requests") }}</div>
								<RequestList
									:component="markRaw(ShiftRequestItem)"
									:items="myShiftRequests?.data?.slice(0, 5)"
									:addListButton="true"
									listButtonRoute="ShiftRequestListView"
								/>
							</div>
						</div>
					</div>
				</div>

				<!-- ── Team Attendance Tab ── -->
				<div v-else-if="activeTab === 'Team Attendance'">

					<!-- Mobile: single column -->
					<div class="lg:hidden flex flex-col gap-6">
						<div class="flex flex-col gap-4">
							<div class="section-title">{{ __("Reporting Check-ins") }}</div>
							<BreadcrumbNav :breadcrumb="breadcrumb" @navigate="navigateTo" />
							<SummaryChips :checked-in="reportingCheckedIn" :checked-out="reportingCheckedOut" :absent="reportingAbsent" />
							<MemberList :data="reportingData" @drill-down="drillDown" :format-time="formatTime" :status-theme="statusTheme" :status-label="statusLabel" />
						</div>
						<div class="border-t border-gray-200"></div>
						<div class="flex flex-col gap-4">
							<div class="section-title">{{ __("Team Check-ins") }}</div>
							<SummaryChips :checked-in="deptCheckedIn" :checked-out="deptCheckedOut" :absent="deptAbsent" />
							<MemberList :data="deptData" :format-time="formatTime" :status-theme="statusTheme" :status-label="statusLabel" />
						</div>
					</div>

					<!-- Desktop: two-column side by side -->
					<div class="hidden lg:grid lg:grid-cols-2 lg:gap-8 lg:items-start">

						<!-- Reporting Check-ins -->
						<div class="desk-card flex flex-col gap-4 p-5">
							<div class="section-title">{{ __("Reporting Check-ins") }}</div>
							<BreadcrumbNav :breadcrumb="breadcrumb" @navigate="navigateTo" />
							<SummaryChips :checked-in="reportingCheckedIn" :checked-out="reportingCheckedOut" :absent="reportingAbsent" />
							<MemberList :data="reportingData" @drill-down="drillDown" :format-time="formatTime" :status-theme="statusTheme" :status-label="statusLabel" scrollable />
						</div>

						<!-- Team Check-ins (Department) -->
						<div class="desk-card flex flex-col gap-4 p-5">
							<div class="section-title">{{ __("Team Check-ins") }}</div>
							<SummaryChips :checked-in="deptCheckedIn" :checked-out="deptCheckedOut" :absent="deptAbsent" />
							<MemberList :data="deptData" :format-time="formatTime" :status-theme="statusTheme" :status-label="statusLabel" scrollable />
						</div>
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw, ref, reactive, defineComponent, h } from "vue"
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

// ── Reporting Check-ins ───────────────────────────────────────────────────
const currentManager = ref(null)
const breadcrumb = reactive([
	{ employee: null, name: employee.data?.employee_name || "My Team" },
])

const reportingData = createResource({
	url: "hrms.api.get_team_checkins",
	params: { date: dayjs().format("YYYY-MM-DD"), manager: currentManager.value },
	auto: true,
	cache: "hrms:team_checkins",
})

function drillDown(member) {
	currentManager.value = member.employee
	breadcrumb.push({ employee: member.employee, name: member.employee_name })
	reportingData.fetch({ date: dayjs().format("YYYY-MM-DD"), manager: member.employee })
}

function navigateTo(idx) {
	if (idx === breadcrumb.length - 1) return
	const crumb = breadcrumb[idx]
	currentManager.value = crumb.employee
	breadcrumb.splice(idx + 1)
	reportingData.fetch({ date: dayjs().format("YYYY-MM-DD"), manager: crumb.employee })
}

const reportingCheckedIn  = computed(() => (reportingData.data || []).filter(m => m.status === "Checked In").length)
const reportingCheckedOut = computed(() => (reportingData.data || []).filter(m => m.status === "Checked Out").length)
const reportingAbsent     = computed(() => (reportingData.data || []).filter(m => m.status === "Not Checked In").length)

// ── Team Check-ins (Department) ───────────────────────────────────────────
const deptData = createResource({
	url: "hrms.api.get_department_checkins",
	params: { date: dayjs().format("YYYY-MM-DD") },
	auto: true,
	cache: "hrms:dept_checkins",
})

const deptCheckedIn  = computed(() => (deptData.data || []).filter(m => m.status === "Checked In").length)
const deptCheckedOut = computed(() => (deptData.data || []).filter(m => m.status === "Checked Out").length)
const deptAbsent     = computed(() => (deptData.data || []).filter(m => m.status === "Not Checked In").length)

// ── Helpers ───────────────────────────────────────────────────────────────
const formatTime = (datetime) => datetime ? dayjs(datetime).format("hh:mm A") : ""
const statusTheme = (s) => s === "Checked In" ? "green" : s === "Checked Out" ? "blue" : "gray"
const statusLabel = (s) => s === "Checked In" ? __("In") : s === "Checked Out" ? __("Out") : __("Absent")

// ── Shifts ────────────────────────────────────────────────────────────────
const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	transform: (data) => data.map((a) => ({
		...a,
		doctype: "Shift Assignment",
		is_upcoming: !a.end_date || dayjs(a.end_date).isAfter(dayjs()),
		shift_dates: getShiftDates(a),
		total_shift_days: getTotalShiftDays(a),
		shift_timing: getShiftTiming(a),
	})),
})

const upcomingShifts = computed(() => shifts.data?.filter(s => s.is_upcoming)?.slice(0, 5))

// ── Inline sub-components (avoid prop-drilling repetition) ────────────────
const BreadcrumbNav = defineComponent({
	props: ["breadcrumb"],
	emits: ["navigate"],
	setup(props, { emit }) {
		return () => props.breadcrumb.length > 1
			? h("div", { class: "flex items-center gap-1 text-sm overflow-x-auto" },
				props.breadcrumb.flatMap((crumb, idx) => {
					const isLast = idx === props.breadcrumb.length - 1
					const nodes = []
					if (idx > 0) nodes.push(h("span", { class: "text-gray-400 flex-shrink-0" }, "/"))
					nodes.push(h("span", {
						class: `cursor-pointer flex-shrink-0 ${isLast ? "text-gray-900 font-medium" : "text-blue-600"}`,
						onClick: () => emit("navigate", idx),
					}, crumb.name))
					return nodes
				})
			)
			: null
	},
})

const SummaryChips = defineComponent({
	props: ["checkedIn", "checkedOut", "absent"],
	setup(props) {
		const $__ = inject("$translate")
		return () => h("div", { class: "flex gap-2 flex-wrap" }, [
			h("div", { class: "flex items-center gap-1.5 bg-green-50 text-green-700 rounded-full px-3 py-1.5 text-xs font-medium" }, [
				h("div", { class: "w-2 h-2 rounded-full bg-green-500" }),
				`${props.checkedIn} ${$__("In")}`,
			]),
			h("div", { class: "flex items-center gap-1.5 bg-blue-50 text-blue-700 rounded-full px-3 py-1.5 text-xs font-medium" }, [
				h("div", { class: "w-2 h-2 rounded-full bg-blue-500" }),
				`${props.checkedOut} ${$__("Out")}`,
			]),
			h("div", { class: "flex items-center gap-1.5 bg-gray-100 text-gray-600 rounded-full px-3 py-1.5 text-xs font-medium" }, [
				h("div", { class: "w-2 h-2 rounded-full bg-gray-400" }),
				`${props.absent} ${$__("Absent")}`,
			]),
		])
	},
})

const MemberList = defineComponent({
	props: ["data", "formatTime", "statusTheme", "statusLabel", "scrollable"],
	emits: ["drill-down"],
	setup(props, { emit }) {
		return () => {
			if (!props.data?.data?.length) {
				return h(EmptyState, {
					message: props.data?.loading ? "Loading..." : "No members found",
				})
			}
			const listEl = h("div", {
				class: [
					"flex flex-col bg-white rounded-lg overflow-hidden border border-gray-100",
					props.scrollable ? "max-h-96 overflow-y-auto" : "",
				].join(" "),
			}, props.data.data.map(member =>
				h("div", {
					key: member.employee,
					class: [
						"flex items-center gap-3 px-4 py-3 border-b last:border-b-0 transition-colors",
						member.has_reports ? "cursor-pointer hover:bg-gray-50" : "",
					].join(" "),
					onClick: member.has_reports ? () => emit("drill-down", member) : undefined,
				}, [
					h(Avatar, { label: member.employee_name, image: member.image, size: "md" }),
					h("div", { class: "flex-1 min-w-0" }, [
						h("div", { class: "text-sm font-medium text-gray-900 truncate" }, member.employee_name),
						h("div", { class: "text-xs text-gray-500 truncate" }, member.designation || member.department),
					]),
					h("div", { class: "flex flex-col items-end gap-1 shrink-0" }, [
						h(Badge, {
							theme: props.statusTheme(member.status),
							label: props.statusLabel(member.status),
							variant: "subtle",
							size: "sm",
						}),
						member.first_in ? h("div", { class: "text-[10px] text-gray-500" }, [
							h("span", { class: "text-green-600" }, props.formatTime(member.first_in)),
							member.last_out ? h("span", { class: "mx-0.5" }, "–") : null,
							member.last_out ? h("span", { class: "text-blue-600" }, props.formatTime(member.last_out)) : null,
						]) : null,
					]),
					member.has_reports
						? h(FeatherIcon, { name: "chevron-right", class: "h-4 w-4 text-gray-400 flex-shrink-0" })
						: null,
				])
			))
			return listEl
		}
	},
})
</script>

<style scoped>
.section-title {
	font-size: 1rem;
	font-weight: 700;
	color: #1f2937;
}

.desk-card {
	background: #ffffff;
	border: 1px solid #e5e7eb;
	border-radius: 12px;
	box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
</style>
