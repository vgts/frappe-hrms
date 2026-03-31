<template>
	<div class="flex flex-col w-full gap-5" v-if="calendarEvents.data">
		<div class="text-lg text-gray-800 font-bold">{{ __("Attendance Calendar") }}</div>

		<div class="flex flex-col gap-6 bg-white py-6 px-3.5 rounded-lg border-none">
			<!-- Month Change -->
			<div class="flex flex-row justify-between items-center px-4">
				<Button
					icon="chevron-left"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
				/>
				<span class="text-lg text-gray-800 font-bold">
					{{ firstOfMonth.format("MMMM") }} {{ firstOfMonth.format("YYYY") }}
				</span>
				<Button
					icon="chevron-right"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
				/>
			</div>

			<!-- Calendar -->
			<div class="grid grid-cols-7 gap-y-3">
				<!-- Day headers: highlight Sun (0) and Sat (6) -->
				<div
					v-for="(day, i) in DAYS"
					:key="day + i"
					class="flex justify-center text-sm font-medium leading-6"
					:class="i === 0 || i === 6 ? 'text-orange-400' : 'text-gray-600'"
				>
					{{ day }}
				</div>

				<!-- Empty cells for offset -->
				<div v-for="_ in firstOfMonth.get('d')" />

				<!-- Day cells -->
				<div v-for="index in firstOfMonth.endOf('M').get('D')" :key="index">
					<div
						class="h-8 w-8 flex rounded-full mx-auto"
						:class="getCellClass(index)"
					>
						<span
							class="text-sm font-medium m-auto"
							:class="isWeekend(index) && !getEventOnDate(index) ? 'text-orange-400' : 'text-gray-800'"
						>
							{{ index }}
						</span>
					</div>
				</div>
			</div>

			<hr />

			<!-- Summary -->
			<div class="grid grid-cols-4 mx-2">
				<div v-for="status in summaryStatuses" class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="rounded full h-3 w-3" :class="colorMap[status]" />
						<span class="text-gray-600 text-sm font-medium leading-5"> {{ __(status) }} </span>
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6 mx-auto">
						{{ summary[status] || 0 }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { createResource } from "frappe-ui"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))

const colorMap = {
	Present: "bg-green-300",
	"Work From Home": "bg-green-300",
	"Half Day": "bg-yellow-200",
	Absent: "bg-red-200",
	"On Leave": "bg-blue-300",
	Holiday: "bg-gray-300",
	Weekend: "bg-orange-100",
}

// __("Present"), __("Half Day"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Half Day", "Absent", "On Leave"]

const summary = computed(() => {
	const summary = {}

	for (const status of Object.values(calendarEvents.data)) {
		let updatedStatus = status === "Work From Home" ? "Present" : status
		if (updatedStatus in summary) {
			summary[updatedStatus] += 1
		} else {
			summary[updatedStatus] = 1
		}
	}

	return summary
})

watch(
	() => firstOfMonth.value,
	() => {
		calendarEvents.fetch()
	}
)

const getEventOnDate = (date) => {
	return calendarEvents.data[firstOfMonth.value.date(date).format("YYYY-MM-DD")]
}

// Returns day-of-week (0=Sun, 6=Sat) for day number `index` in current month
const getDayOfWeek = (index) => {
	return (firstOfMonth.value.get("d") + index - 1) % 7
}

const isWeekend = (index) => {
	const dow = getDayOfWeek(index)
	return dow === 0 || dow === 6
}

const getCellClass = (index) => {
	const event = getEventOnDate(index)
	if (event) return colorMap[event]
	if (isWeekend(index)) return colorMap["Weekend"]
	return ""
}

const getFirstLetter = (s) => Array.from(s.trim())[0] // Unicode

const DAYS = [
	getFirstLetter(__("Sunday")),
	getFirstLetter(__("Monday")),
	getFirstLetter(__("Tuesday")),
	getFirstLetter(__("Wednesday")),
	getFirstLetter(__("Thursday")),
	getFirstLetter(__("Friday")),
	getFirstLetter(__("Saturday")),
]

//resources
const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: "hrms:attendance_calendar_events",
	makeParams() {
		return {
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>
