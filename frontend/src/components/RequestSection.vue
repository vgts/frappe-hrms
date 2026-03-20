<template>
	<div v-if="props.items?.length" class="w-full">
		<!-- Section Header -->
		<div
			class="flex items-center justify-between px-1 py-2 cursor-pointer"
			@click="isExpanded = !isExpanded"
		>
			<div class="flex items-center gap-2">
				<span class="text-sm font-semibold text-gray-700">{{ props.title }}</span>
				<span class="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">
					{{ props.items.length }}
				</span>
			</div>
			<FeatherIcon
				:name="isExpanded ? 'chevron-up' : 'chevron-down'"
				class="h-4 w-4 text-gray-400"
			/>
		</div>

		<!-- Section Items -->
		<div v-if="isExpanded" class="flex flex-col bg-white rounded overflow-auto">
			<div
				class="flex flex-row p-3.5 items-center justify-between border-b cursor-pointer"
				v-for="item in props.items"
				:key="item.name"
				@click="openRequestModal(item)"
			>
				<component
					:is="props.component"
					:doc="item"
					:workflowStateField="item.workflow_state_field"
					:isTeamRequest="props.teamRequests"
				/>
			</div>

			<router-link
				v-if="props.listRoute"
				:to="{ name: props.listRoute }"
				v-slot="{ navigate }"
			>
				<Button
					variant="ghost"
					@click="navigate"
					class="w-full !text-gray-600 py-4 text-xs border-none bg-white hover:bg-white"
				>
					{{ __("View All") }}
				</Button>
			</router-link>
		</div>

		<!-- Request Action Sheet Modal -->
		<ion-modal
			ref="modal"
			:is-open="isRequestModalOpen"
			@didDismiss="closeRequestModal"
			:initial-breakpoint="1"
			:breakpoints="[0, 1]"
		>
			<RequestActionSheet :fields="fieldsMap[selectedRequest?.doctype]" v-model="selectedRequest" />
		</ion-modal>
	</div>
</template>

<script setup>
import { ref, inject } from "vue"
import { FeatherIcon } from "frappe-ui"
import { IonModal } from "@ionic/vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"

import {
	LEAVE_FIELDS,
	EXPENSE_CLAIM_FIELDS,
	ATTENDANCE_REQUEST_FIELDS,
	SHIFT_REQUEST_FIELDS,
	SHIFT_FIELDS,
	EMPLOYEE_PERMISSION_FIELDS,
} from "@/data/config/requestSummaryFields"

const __ = inject("$translate")

const props = defineProps({
	title: {
		type: String,
		required: true,
	},
	items: {
		type: Array,
		default: () => [],
	},
	component: {
		type: Object,
		required: true,
	},
	teamRequests: {
		type: Boolean,
		default: false,
	},
	listRoute: {
		type: String,
		default: "",
	},
})

const isExpanded = ref(true)
const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

const fieldsMap = {
	"Leave Application": LEAVE_FIELDS,
	"Expense Claim": EXPENSE_CLAIM_FIELDS,
	"Attendance Request": ATTENDANCE_REQUEST_FIELDS,
	"Shift Request": SHIFT_REQUEST_FIELDS,
	"Shift Assignment": SHIFT_FIELDS,
	"Employee Permission": EMPLOYEE_PERMISSION_FIELDS,
}

const openRequestModal = async (request) => {
	selectedRequest.value = request
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}
</script>
