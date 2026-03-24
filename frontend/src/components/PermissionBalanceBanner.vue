<template>
	<div
		v-if="balance"
		class="w-full bg-white rounded-xl shadow-sm border border-gray-100 p-4 mt-4"
	>
		<!-- Header -->
		<div class="flex items-center justify-between mb-3">
			<div class="flex items-center gap-2">
				<FeatherIcon name="clock" class="h-4 w-4 text-blue-600" />
				<span class="text-sm font-semibold text-gray-800">
					{{ __("Monthly Permission Balance") }}
				</span>
			</div>
			<span class="text-xs text-gray-400 font-medium">
				{{ currentMonthLabel }}
			</span>
		</div>

		<!-- Main balance display -->
		<div class="flex items-end gap-1 mb-3">
			<span class="text-3xl font-bold" :class="availableColor">
				{{ balance.formatted_available }}
			</span>
			<span class="text-sm text-gray-500 mb-1">
				/ {{ balance.monthly_limit }}h {{ __("available") }}
			</span>
		</div>

		<!-- Progress bar -->
		<div class="w-full bg-gray-100 rounded-full h-2 mb-3 overflow-hidden">
			<!-- Approved portion -->
			<div
				class="h-2 rounded-full transition-all duration-500 float-left"
				:style="{ width: approvedPct + '%' }"
				:class="approvedPct > 0 ? 'bg-green-500' : ''"
			></div>
			<!-- Pending portion -->
			<div
				class="h-2 transition-all duration-500 float-left"
				:style="{ width: pendingPct + '%' }"
				:class="pendingPct > 0 ? 'bg-yellow-400' : ''"
			></div>
		</div>

		<!-- Breakdown row -->
		<div class="flex gap-4 mt-1">
			<div class="flex items-center gap-1.5">
				<span class="h-2.5 w-2.5 rounded-full bg-green-500 flex-shrink-0"></span>
				<span class="text-xs text-gray-600">
					{{ __("Approved") }}: <strong>{{ balance.formatted_approved }}</strong>
				</span>
			</div>
			<div v-if="balance.pending_hours > 0" class="flex items-center gap-1.5">
				<span class="h-2.5 w-2.5 rounded-full bg-yellow-400 flex-shrink-0"></span>
				<span class="text-xs text-gray-600">
					{{ __("Pending") }}: <strong>{{ balance.formatted_pending }}</strong>
				</span>
			</div>
			<div class="flex items-center gap-1.5 ml-auto">
				<span class="text-xs text-gray-400">
					{{ __("Limit: {0}h/month", [balance.monthly_limit]) }}
				</span>
			</div>
		</div>

		<!-- Rules hint -->
		<div class="flex gap-3 mt-3 pt-3 border-t border-gray-100">
			<div class="flex items-center gap-1">
				<FeatherIcon name="info" class="h-3 w-3 text-gray-400" />
				<span class="text-xs text-gray-400">
					{{ __("Min: 30 min · Max: 2 hrs per request") }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { FeatherIcon } from "frappe-ui"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const props = defineProps({
	balance: {
		type: Object,
		default: null,
	},
})

const currentMonthLabel = computed(() => {
	return dayjs().format("MMMM YYYY")
})

const approvedPct = computed(() => {
	if (!props.balance) return 0
	return Math.min(Math.round((props.balance.approved_hours / props.balance.monthly_limit) * 100), 100)
})

const pendingPct = computed(() => {
	if (!props.balance) return 0
	return Math.min(Math.round((props.balance.pending_hours / props.balance.monthly_limit) * 100), 100 - approvedPct.value)
})

const availableColor = computed(() => {
	if (!props.balance) return "text-gray-800"
	const avail = props.balance.available_hours
	if (avail <= 0) return "text-red-600"
	if (avail <= 1) return "text-orange-500"
	return "text-blue-600"
})
</script>
