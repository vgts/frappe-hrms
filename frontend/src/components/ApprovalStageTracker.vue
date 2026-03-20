<template>
	<div v-if="approvalDetails?.data" class="w-full bg-gray-50 rounded-lg p-4">
		<div class="flex items-center justify-between gap-2">
			<!-- Leave Approver -->
			<div class="flex flex-col items-center gap-2 min-w-[72px]">
				<div class="relative">
					<img
						v-if="approvalDetails.data.leave_approver_image"
						:src="approvalDetails.data.leave_approver_image"
						class="w-10 h-10 rounded-full object-cover border-2"
						:class="approverBorderColor"
					/>
					<div
						v-else
						class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold border-2"
						:class="[approverBorderColor, approverBgColor]"
					>
						{{ getInitials(approvalDetails.data.leave_approver_name) }}
					</div>
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

			<!-- Connecting Line -->
			<div class="flex-1 flex items-center px-1">
				<div class="h-0.5 w-full rounded" :class="lineColor"></div>
				<FeatherIcon name="chevron-right" class="w-4 h-4 -ml-1 flex-shrink-0" :class="lineIconColor" />
			</div>

			<!-- Secondary Approver -->
			<div class="flex flex-col items-center gap-2 min-w-[72px]">
				<div class="relative">
					<img
						v-if="approvalDetails.data.secondary_approver_image"
						:src="approvalDetails.data.secondary_approver_image"
						class="w-10 h-10 rounded-full object-cover border-2"
						:class="secondaryBorderColor"
					/>
					<div
						v-else
						class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold border-2"
						:class="[secondaryBorderColor, secondaryBgColor]"
					>
						{{ getInitials(approvalDetails.data.secondary_approver_name) }}
					</div>
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
import { FeatherIcon } from "frappe-ui"

const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object, required: true },
	approvalDetails: { type: Object, required: true },
})

const stage = computed(() => props.doc?.custom_approval_stage || "")

function getInitials(name) {
	if (!name) return "?"
	return name.split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase()
}

// Approver (Level 1) styles
const approverBorderColor = computed(() => {
	if (stage.value === "Pending Leave Approver") return "border-yellow-400"
	return "border-green-500"
})
const approverBgColor = computed(() => {
	if (stage.value === "Pending Leave Approver") return "bg-yellow-50 text-yellow-700"
	return "bg-green-50 text-green-700"
})
const approverBadgeColor = computed(() => {
	if (stage.value === "Pending Leave Approver") return "bg-yellow-400"
	return "bg-green-500"
})
const approverIcon = computed(() => {
	if (stage.value === "Pending Leave Approver") return "…"
	return "✓"
})

// Secondary (Level 2) styles
const secondaryBorderColor = computed(() => {
	if (stage.value === "Fully Approved") return "border-green-500"
	if (stage.value === "Rejected by Secondary Approver") return "border-red-500"
	if (stage.value === "Pending Secondary Approver") return "border-yellow-400"
	return "border-gray-300"
})
const secondaryBgColor = computed(() => {
	if (stage.value === "Fully Approved") return "bg-green-50 text-green-700"
	if (stage.value === "Rejected by Secondary Approver") return "bg-red-50 text-red-700"
	if (stage.value === "Pending Secondary Approver") return "bg-yellow-50 text-yellow-700"
	return "bg-gray-100 text-gray-400"
})
const secondaryBadgeColor = computed(() => {
	if (stage.value === "Fully Approved") return "bg-green-500"
	if (stage.value === "Rejected by Secondary Approver") return "bg-red-500"
	if (stage.value === "Pending Secondary Approver") return "bg-yellow-400"
	return "bg-gray-300"
})
const secondaryIcon = computed(() => {
	if (stage.value === "Fully Approved") return "✓"
	if (stage.value === "Rejected by Secondary Approver") return "✗"
	if (stage.value === "Pending Secondary Approver") return "…"
	return "○"
})

// Connecting line
const lineColor = computed(() => {
	if (stage.value === "Fully Approved") return "bg-green-400"
	if (stage.value === "Rejected by Secondary Approver") return "bg-red-400"
	if (stage.value === "Pending Secondary Approver") return "bg-yellow-400"
	return "bg-gray-300"
})
const lineIconColor = computed(() => {
	if (stage.value === "Fully Approved") return "text-green-400"
	if (stage.value === "Rejected by Secondary Approver") return "text-red-400"
	if (stage.value === "Pending Secondary Approver") return "text-yellow-400"
	return "text-gray-300"
})

// Stage label
const stageLabel = computed(() => {
	const map = {
		"Pending Leave Approver": { text: "Pending Leave Approver", class: "bg-yellow-100 text-yellow-800" },
		"Pending Secondary Approver": { text: "Pending Secondary Approval", class: "bg-yellow-100 text-yellow-800" },
		"Fully Approved": { text: "Fully Approved", class: "bg-green-100 text-green-800" },
		"Rejected by Secondary Approver": { text: "Rejected by Secondary Approver", class: "bg-red-100 text-red-800" },
	}
	return map[stage.value] || { text: stage.value || "Unknown", class: "bg-gray-100 text-gray-600" }
})
</script>
