<template>
	<div v-if="deptCheckins.data?.length" class="w-full bg-white rounded-xl shadow-sm border border-gray-100 lg:flex lg:flex-col">

		<!-- Header -->
		<div class="flex items-center justify-between px-4 pt-4 pb-3 lg:px-5 lg:pt-5">
			<div class="text-base font-bold text-gray-800 lg:text-lg">{{ __("Team Check-ins") }}</div>
			<router-link :to="{ name: 'AttendanceDashboard' }" class="text-xs text-blue-600 font-medium hover:text-blue-700 transition-colors">
				{{ __("View All") }}
			</router-link>
		</div>

		<!-- Summary chips -->
		<div class="flex gap-2 flex-wrap px-4 pb-4 lg:px-5">
			<div class="flex items-center gap-1.5 bg-green-50 text-green-700 rounded-full px-3 py-1.5 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-green-500"></div>
				{{ checkedInCount }} {{ __("Checked In") }}
			</div>
			<div class="flex items-center gap-1.5 bg-blue-50 text-blue-700 rounded-full px-3 py-1.5 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-blue-500"></div>
				{{ checkedOutCount }} {{ __("Checked Out") }}
			</div>
			<div class="flex items-center gap-1.5 bg-orange-50 text-orange-600 rounded-full px-3 py-1.5 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-orange-400"></div>
				{{ notCheckedInCount }} {{ __("Absent") }}
			</div>
		</div>

		<!-- Desktop: member list -->
		<div class="hidden lg:block border-t border-gray-100 overflow-y-auto max-h-72">
			<div
				v-for="member in deptCheckins.data"
				:key="member.employee"
				class="flex items-center justify-between px-5 py-2.5 border-b border-gray-50 last:border-b-0 hover:bg-gray-50 transition-colors"
			>
				<div class="flex items-center gap-3 min-w-0">
					<Avatar :image="member.image" :label="member.employee_name" size="sm" />
					<div class="min-w-0">
						<div class="text-sm font-medium text-gray-800 truncate">{{ member.employee_name }}</div>
						<div class="text-xs text-gray-400 truncate">{{ member.designation || member.department }}</div>
					</div>
				</div>
				<div class="flex flex-col items-end gap-0.5 shrink-0 ml-3">
					<span
						class="text-xs font-semibold px-2 py-0.5 rounded-full"
						:class="{
							'bg-green-50 text-green-700': member.status === 'Checked In',
							'bg-blue-50 text-blue-700': member.status === 'Checked Out',
							'bg-orange-50 text-orange-600': member.status === 'Not Checked In',
						}"
					>
						{{ member.status === 'Not Checked In' ? __('Absent') : __(member.status) }}
					</span>
					<span v-if="member.first_in" class="text-[10px] text-gray-400">
						{{ formatTime(member.first_in) }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted } from "vue"
import { createResource, Avatar } from "frappe-ui"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const deptCheckins = createResource({
	url: "hrms.api.get_department_checkins",
	params: { date: dayjs().format("YYYY-MM-DD") },
	auto: true,
	cache: "hrms:dept_checkins",
})

function onVisibilityChange() {
	if (document.visibilityState === "visible") deptCheckins.reload()
}
onMounted(() => document.addEventListener("visibilitychange", onVisibilityChange))
onUnmounted(() => document.removeEventListener("visibilitychange", onVisibilityChange))

const checkedInCount = computed(() =>
	(deptCheckins.data || []).filter(m => m.status === "Checked In").length
)
const checkedOutCount = computed(() =>
	(deptCheckins.data || []).filter(m => m.status === "Checked Out").length
)
const notCheckedInCount = computed(() =>
	(deptCheckins.data || []).filter(m => m.status === "Not Checked In").length
)

function formatTime(timeStr) {
	if (!timeStr) return ""
	return dayjs(timeStr.replace(" ", "T")).format("hh:mm A")
}
</script>
