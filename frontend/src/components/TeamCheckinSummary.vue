<template>
	<div v-if="teamCheckins.data?.length" class="w-full">
		<div class="flex items-center justify-between mb-3">
			<div class="text-lg text-gray-800 font-bold">{{ __("Team Check-ins") }}</div>
			<router-link :to="{ name: 'AttendanceDashboard' }" class="text-sm text-blue-600 font-medium">
				{{ __("View All") }}
			</router-link>
		</div>

		<!-- Summary Chips only -->
		<div class="flex gap-2 bg-white rounded-lg p-3">
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
			<div class="flex items-center gap-1.5 bg-gray-50 text-gray-500 rounded-full px-3 py-1.5 text-xs font-medium ml-auto">
				{{ teamCheckins.data.length }} {{ __("Total") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const teamCheckins = createResource({
	url: "hrms.api.get_team_checkins",
	params: { date: dayjs().format("YYYY-MM-DD") },
	auto: true,
	cache: "hrms:team_checkins",
})

const checkedInCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Checked In").length
)
const checkedOutCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Checked Out").length
)
const notCheckedInCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Not Checked In").length
)
</script>
