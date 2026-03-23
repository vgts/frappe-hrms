<template>
	<div v-if="teamCheckins.data?.length" class="w-full">
		<div class="flex items-center justify-between mb-3">
			<div class="text-lg text-gray-800 font-bold">{{ __("Team Check-ins") }}</div>
			<span class="text-xs text-gray-500">{{ formattedDate }}</span>
		</div>

		<!-- Summary Chips -->
		<div class="flex gap-2 mb-4">
			<div class="flex items-center gap-1.5 bg-green-50 text-green-700 rounded-full px-3 py-1 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-green-500"></div>
				{{ checkedInCount }} {{ __("In") }}
			</div>
			<div class="flex items-center gap-1.5 bg-blue-50 text-blue-700 rounded-full px-3 py-1 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-blue-500"></div>
				{{ checkedOutCount }} {{ __("Out") }}
			</div>
			<div class="flex items-center gap-1.5 bg-gray-100 text-gray-600 rounded-full px-3 py-1 text-xs font-medium">
				<div class="w-2 h-2 rounded-full bg-gray-400"></div>
				{{ notCheckedInCount }} {{ __("Absent") }}
			</div>
		</div>

		<!-- Team Members List -->
		<div class="flex flex-col bg-white rounded-lg overflow-hidden">
			<div
				v-for="member in teamCheckins.data"
				:key="member.employee"
				class="flex items-center gap-3 p-3 border-b last:border-b-0"
			>
				<!-- Avatar -->
				<Avatar
					:label="member.employee_name"
					:image="member.image"
					size="lg"
				/>

				<!-- Employee Info -->
				<div class="flex-1 min-w-0">
					<div class="text-sm font-medium text-gray-900 truncate">
						{{ member.employee_name }}
					</div>
					<div class="text-xs text-gray-500 truncate">
						{{ member.designation || member.department }}
					</div>
				</div>

				<!-- Checkin Times & Status -->
				<div class="flex flex-col items-end gap-1">
					<Badge
						:theme="statusTheme(member.status)"
						:label="statusLabel(member.status)"
						variant="subtle"
						size="sm"
					/>
					<div v-if="member.first_in" class="text-[10px] text-gray-500">
						<span class="text-green-600">{{ __("In") }}: {{ formatTime(member.first_in) }}</span>
						<span v-if="member.last_out" class="ml-1 text-blue-600">
							{{ __("Out") }}: {{ formatTime(member.last_out) }}
						</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource, Avatar, Badge } from "frappe-ui"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const teamCheckins = createResource({
	url: "hrms.api.get_team_checkins",
	params: { date: dayjs().format("YYYY-MM-DD") },
	auto: true,
	cache: "hrms:team_checkins",
})

const formattedDate = computed(() => dayjs().format("D MMM YYYY"))

const checkedInCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Checked In").length
)
const checkedOutCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Checked Out").length
)
const notCheckedInCount = computed(() =>
	(teamCheckins.data || []).filter(m => m.status === "Not Checked In").length
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
</script>
