<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<LeaveIcon class="h-5 w-5 text-gray-500" />
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ __(props.doc.leave_type, null, "Leave Type") }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					<span>{{ props.doc.leave_dates || getLeaveDates(props.doc) }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span class="whitespace-nowrap">{{ __("{0}d", [props.doc.total_leave_days]) }}</span>
				</div>
			</div>
		</template>
		<template #right>
			<div class="flex flex-col items-end gap-1">
				<Badge variant="outline" :theme="colorMap[status]" :label="__(status, null, 'Leave Application')" size="md" />
				<Badge
					v-if="showApprovalStage"
					variant="subtle"
					:theme="stageColorMap[props.doc.custom_approval_stage] || 'gray'"
					:label="stageLabel"
					size="sm"
				/>
			</div>
			<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"
import { FeatherIcon, Badge } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import { getLeaveDates } from "@/data/leaves"

const __ = inject("$translate")

const props = defineProps({
	doc: {
		type: Object,
	},
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
	workflowStateField: {
		type: String,
		required: false,
	},
})

const status = computed(() => {
	return props.workflowStateField ? props.doc[props.workflowStateField] : props.doc.status
})

const showApprovalStage = computed(() => {
	return (
		props.doc.custom_approval_stage &&
		props.doc.custom_approval_stage !== "Pending Project Reporting Approval" &&
		props.doc.custom_secondary_leave_approver
	)
})

const stageLabel = computed(() => {
	const map = {
		"Pending Secondary Reporting Approval": __("Pending 2nd Approval"),
		"Approved": __("Approved"),
		"Rejected": __("Rejected by 2nd"),
	}
	return map[props.doc.custom_approval_stage] || props.doc.custom_approval_stage
})

const colorMap = {
	Approved: "green",
	Rejected: "red",
	Open: "orange",
}

const stageColorMap = {
	"Pending Secondary Reporting Approval": "orange",
	"Approved": "green",
	"Rejected": "red",
}
</script>
