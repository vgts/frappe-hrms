<template>
	<div v-if="approvalDetails?.data" class="w-full bg-gray-50 rounded-lg p-4">
		<div class="flex items-center justify-between gap-2">
			<!-- Leave Approver (always shown) -->
			<div class="flex flex-col items-center gap-2 min-w-[72px]">
				<div class="relative">
					<Avatar
						:label="approvalDetails.data.leave_approver_name || 'Leave Approver'"
						:image="approvalDetails.data.leave_approver_image"
						size="xl"
						class="border-2 rounded-full"
						:class="approverBorderColor"
					/>
					<div
						class="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold"
						:class="approverBadgeColor"
					>
						{{ approverIcon }}
					</div>
				</div>
				<span class="text-[10px] text-gray-600 text-center leading-tight max-w-[72px] truncate">
					{{ approvalDetails.data.leave_approver_name || __("Leave Approver") }}
				</span>
			</div>

			<!-- Connecting Line + Secondary Approver (two-level flow only) -->
			<template v-if="hasSecondary">
				<div class="flex-1 flex items-center px-1">
					<div class="h-0.5 w-full rounded" :class="lineColor"></div>
					<FeatherIcon name="chevron-right" class="w-4 h-4 -ml-1 flex-shrink-0" :class="lineIconColor" />
				</div>

				<div class="flex flex-col items-center gap-2 min-w-[72px]">
					<div class="relative">
						<Avatar
							:label="approvalDetails.data.secondary_approver_name || 'Secondary Approver'"
							:image="approvalDetails.data.secondary_approver_image"
							size="xl"
							class="border-2 rounded-full"
							:class="secondaryBorderColor"
						/>
						<div
							class="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold"
							:class="secondaryBadgeColor"
						>
							{{ secondaryIcon }}
						</div>
					</div>
					<span class="text-[10px] text-gray-600 text-center leading-tight max-w-[72px] truncate">
						{{ approvalDetails.data.secondary_approver_name || __("Secondary Approver") }}
					</span>
				</div>
			</template>
		</div>

		<!-- Stage Label -->
		<div class="mt-3 text-center">
			<span
				class="text-xs font-medium px-2 py-1 rounded-full"
				:class="stageLabel.class"
			>
				{{ __(stageLabel.text) }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { Avatar, FeatherIcon } from "frappe-ui"

const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object, required: true },
	approvalDetails: { type: Object, required: true },
})

const stage = computed(() => props.doc?.custom_approval_stage || "")

// Whether this is a two-level approval (has secondary approver)
const hasSecondary = computed(() =>
	!!(approvalDetails?.data?.secondary_approver_name || props.doc?.custom_secondary_leave_approver)
)

// Derive effective status for single-approver flows where stage field is empty
const effectiveStatus = computed(() => {
	if (stage.value) return stage.value
	// Fallback to doc status for single-approver flows
	if (props.doc?.status === "Approved") return "Approved"
	if (props.doc?.status === "Rejected") return "Rejected"
	return "Pending"
})

// Approver (Level 1) styles
const approverBorderColor = computed(() => {
	const s = effectiveStatus.value
	if (s === "Pending" || s === "Pending Project Reporting Approval") return "border-yellow-400"
	if (s === "Rejected") return "border-red-500"
	return "border-green-500"
})
const approverBadgeColor = computed(() => {
	const s = effectiveStatus.value
	if (s === "Pending" || s === "Pending Project Reporting Approval") return "bg-yellow-400"
	if (s === "Rejected") return "bg-red-500"
	return "bg-green-500"
})
const approverIcon = computed(() => {
	const s = effectiveStatus.value
	if (s === "Pending" || s === "Pending Project Reporting Approval") return "…"
	if (s === "Rejected") return "✗"
	return "✓"
})

// Secondary (Level 2) styles
const secondaryBorderColor = computed(() => {
	if (stage.value === "Approved") return "border-green-500"
	if (stage.value === "Rejected") return "border-gray-300"
	if (stage.value === "Pending Secondary Reporting Approval") return "border-yellow-400"
	return "border-gray-300"
})
const secondaryBadgeColor = computed(() => {
	if (stage.value === "Approved") return "bg-green-500"
	if (stage.value === "Rejected") return "bg-gray-300"
	if (stage.value === "Pending Secondary Reporting Approval") return "bg-yellow-400"
	return "bg-gray-300"
})
const secondaryIcon = computed(() => {
	if (stage.value === "Approved") return "✓"
	if (stage.value === "Rejected") return "○"
	if (stage.value === "Pending Secondary Reporting Approval") return "…"
	return "○"
})

// Connecting line
const lineColor = computed(() => {
	if (stage.value === "Approved") return "bg-green-400"
	if (stage.value === "Rejected") return "bg-red-400"
	if (stage.value === "Pending Secondary Reporting Approval") return "bg-yellow-400"
	return "bg-gray-300"
})
const lineIconColor = computed(() => {
	if (stage.value === "Approved") return "text-green-400"
	if (stage.value === "Rejected") return "text-red-400"
	if (stage.value === "Pending Secondary Reporting Approval") return "text-yellow-400"
	return "text-gray-300"
})

// Stage label
const stageLabel = computed(() => {
	const map = {
		"Pending Project Reporting Approval": { text: "Pending Project Reporting Approval", class: "bg-yellow-100 text-yellow-800" },
		"Pending Secondary Reporting Approval": { text: "Pending Secondary Approval", class: "bg-yellow-100 text-yellow-800" },
		"Approved": { text: "Approved", class: "bg-green-100 text-green-800" },
		"Rejected": { text: "Rejected", class: "bg-red-100 text-red-800" },
		"Pending": { text: "Pending Approval", class: "bg-yellow-100 text-yellow-800" },
	}
	return map[effectiveStatus.value] || { text: effectiveStatus.value, class: "bg-gray-100 text-gray-600" }
})
</script>
