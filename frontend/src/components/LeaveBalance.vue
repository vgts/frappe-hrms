<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row justify-between items-center">
			<div class="text-lg text-gray-800 font-bold">{{ __("Leave Balance") }}</div>
			<router-link
				:to="{ name: 'LeaveApplicationListView' }"
				v-slot="{ navigate }"
				v-if="leaveBalance.data"
			>
				<div
					@click="navigate"
					class="text-sm text-gray-800 font-semibold cursor-pointer underline underline-offset-2"
				>
					{{ __("View Leave History") }}
				</div>
			</router-link>
		</div>

		<!-- Mobile: horizontal scroll cards -->
		<div
			class="flex flex-row gap-4 overflow-x-auto py-2 mt-3 lg:hidden"
			v-if="leaveBalance.data"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col bg-white border-none rounded-lg drop-shadow-md gap-2 p-4 items-start first:ml-4 shrink-0"
			>
				<SemicircleChart
					:percentage="allocation.balance_percentage"
					:colorClass="getChartColor(index)"
				/>
				<div class="text-gray-800 font-bold text-base">
					{{ `${allocation.balance_leaves}/${allocation.allocated_leaves}` }}
				</div>
				<div class="text-gray-600 font-normal text-sm w-24 leading-4">
					{{ __("{0} balance", [__(leave_type, null, "Leave Type")]) }}
				</div>
			</div>
		</div>

		<!-- Desktop: responsive grid -->
		<div
			class="hidden lg:grid lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4"
			v-if="leaveBalance.data"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col bg-gray-50 border border-gray-100 rounded-xl gap-2 p-5 items-start"
			>
				<SemicircleChart
					:percentage="allocation.balance_percentage"
					:colorClass="getChartColor(index)"
				/>
				<div class="text-gray-800 font-bold text-lg">
					{{ `${allocation.balance_leaves}/${allocation.allocated_leaves}` }}
				</div>
				<div class="text-gray-500 font-normal text-sm leading-4">
					{{ __("{0} balance", [__(leave_type, null, "Leave Type")]) }}
				</div>
			</div>
		</div>

		<EmptyState :message="__('You have no leaves allocated')" v-else />
	</div>
</template>

<script setup>
import SemicircleChart from "@/components/SemicircleChart.vue"
import { leaveBalance } from "@/data/leaves"
import { inject } from "vue"

const __ = inject("$translate")
const getChartColor = (index) => {
	const chartColors = ["text-[#fb7185]", "text-[#f472b6]", "text-[#918ef5]"]
	return chartColors[index % chartColors.length]
}
</script>
