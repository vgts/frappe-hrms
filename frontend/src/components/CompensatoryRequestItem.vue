<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<FeatherIcon name="gift" class="h-5 w-5 text-yellow-600" />
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ props.doc.display_date || formatDate(props.doc.work_from_date) }}
					<span v-if="props.doc.half_day" class="text-xs text-gray-500"> &middot; Half Day</span>
				</div>
				<div class="text-xs font-normal text-gray-500">
					{{ props.doc.leave_type || __("Compensatory Off") }}
					<template v-if="props.doc.reason">
						<span class="whitespace-pre"> &middot; </span>
						<span>{{ props.doc.reason }}</span>
					</template>
				</div>
			</div>
		</template>
		<template #right>
			<div class="flex flex-col items-end gap-1">
				<Badge
					variant="outline"
					:theme="colorMap[props.doc.status] || 'orange'"
					:label="__(props.doc.status || 'Open', null, 'Compensatory Leave Request')"
					size="md"
				/>
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

const colorMap = {
	Approved: "green",
	Rejected: "red",
	Open: "orange",
}

const showApprovalStage = computed(() => {
	return (
		props.doc.custom_approval_stage &&
		props.doc.custom_secondary_leave_approver &&
		!["Pending Project Reporting Approval", "Approved", "Rejected"].includes(
			props.doc.custom_approval_stage
		)
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
