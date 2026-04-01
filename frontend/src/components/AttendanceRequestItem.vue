<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
		>
		<template #left>
			<AttendanceIcon class="h-5 w-5 text-gray-500" />
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ props.doc.reason }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					<span>{{ props.doc.attendance_dates || getDates(props.doc) }}</span>
					<span v-if="props.doc.to_date">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{ __("{0}d", [props.doc.total_attendance_days]) }}</span>
					</span>
				</div>
			</div>
		</template>
		<template #right>
			<div class="flex flex-col items-end gap-1">
				<Badge variant="outline" :theme="colorMap[status]" :label="__(status)" size="md" />
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
import { Badge, FeatherIcon } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import { getDates, getTotalDays } from "@/data/attendance"

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
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return props.doc.status || "Open"
})

const showApprovalStage = computed(() => {
	return (
		props.doc.custom_approval_stage &&
		props.doc.custom_secondary_leave_approver &&
		!["Pending Project Reporting Approval", "Approved", "Rejected"].includes(props.doc.custom_approval_stage)
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
	Open: "orange",
	Approved: "green",
	Rejected: "red",
}

const stageColorMap = {
	"Pending Secondary Reporting Approval": "orange",
	"Approved": "green",
	"Rejected": "red",
}
</script>
