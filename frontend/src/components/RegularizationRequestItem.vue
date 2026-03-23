<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<FeatherIcon name="refresh-cw" class="h-5 w-5 text-gray-500" />
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ __(props.doc.reason, null, "Attendance Regularization") }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					<span>{{ props.doc.display_date || formatDate(props.doc.attendance_date) }}</span>
					<template v-if="props.doc.checkin_time || props.doc.checkout_time">
						<span class="whitespace-pre"> &middot; </span>
						<span v-if="props.doc.checkin_time" class="text-green-600">{{ formatTime(props.doc.checkin_time) }}</span>
						<span v-if="props.doc.checkin_time && props.doc.checkout_time"> - </span>
						<span v-if="props.doc.checkout_time" class="text-blue-600">{{ formatTime(props.doc.checkout_time) }}</span>
					</template>
				</div>
			</div>
		</template>
		<template #right>
			<div class="flex flex-col items-end gap-1">
				<Badge variant="outline" :theme="colorMap[props.doc.status]" :label="__(props.doc.status, null, 'Attendance Regularization')" size="md" />
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
import dayjs from "@/utils/dayjs"

const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object },
	isTeamRequest: { type: Boolean, default: false },
	workflowStateField: { type: String, required: false },
})

const formatDate = (date) => dayjs(date).format("D MMM")
const formatTime = (time) => {
	if (!time) return ""
	return time.split(":").slice(0, 2).join(":")
}

const colorMap = {
	Approved: "green",
	Rejected: "red",
	Open: "orange",
}

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
	}
	return map[props.doc.custom_approval_stage] || props.doc.custom_approval_stage
})

const stageColorMap = {
	"Pending Secondary Reporting Approval": "orange",
}
</script>
