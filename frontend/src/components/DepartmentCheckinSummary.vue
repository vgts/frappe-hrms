<template>
	<div v-if="deptCheckins.data?.length" class="w-full bg-white rounded-xl shadow-sm border border-gray-100 lg:h-full lg:flex lg:flex-col">

		<!-- Header -->
		<div class="flex items-center justify-between px-4 pt-4 pb-3 lg:px-5 lg:pt-5">
			<div class="text-base font-bold text-gray-800 lg:text-lg">{{ __("Team Check-ins") }}</div>
			<router-link :to="{ name: 'AttendanceDashboard' }" class="text-xs text-blue-600 font-medium hover:text-blue-700 transition-colors">
				{{ __("View All") }}
			</router-link>
		</div>

		<!-- Summary chips -->
		<div class="flex gap-2 flex-wrap px-4 pb-4 lg:px-5 lg:flex-1 lg:items-start">
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

		<!-- Desktop: total footer -->
		<div class="hidden lg:block border-t border-gray-100 px-5 py-3">
			<div class="flex items-center justify-between text-xs text-gray-500">
				<span>{{ __("Department members") }}</span>
				<span class="font-semibold text-gray-700">{{ deptCheckins.data.length }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted } from "vue"
import { createResource } from "frappe-ui"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const deptCheckins = createResource({
	url: "hrms.api.get_department_checkins",
	params: { date: dayjs().format("YYYY-MM-DD") },
	auto: true,
	cache: "hrms:dept_checkins",
})

function onVisibilityChange() {
	if (document.visibilityState === "visible") {
		deptCheckins.reload()
	}
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
</script>
