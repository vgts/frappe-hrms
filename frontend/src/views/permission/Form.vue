<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Employee Permission"
				v-model="permissionRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:showFormButton="!showApprovalActions"
				@validateForm="validateForm"
			>
				<!-- Monthly balance banner shown when creating a new request -->
				<template #aboveForm v-if="!props.id">
					<PermissionBalanceBanner :balance="availableHours.data" />
				</template>

				<template #formButton v-if="showApprovalActions">
					<div class="flex flex-col gap-3 w-full">
						<!-- Approval Stage Tracker -->
						<ApprovalStageTracker
							v-if="approvalDetails?.data && permissionRequest.custom_secondary_leave_approver"
							:doc="permissionRequest"
							:approvalDetails="approvalDetails"
						/>

						<!-- Project Reporting (Primary) approver buttons -->
						<template v-if="isProjectReportingPending">
							<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
								{{ __("Waiting for your approval") }}
							</div>
							<div v-if="showPrimaryRejectReason" class="w-full mb-2">
								<label class="text-sm text-gray-600 mb-1 block">{{ __("Reason for Rejection") }} *</label>
								<textarea
									v-model="primaryRejectReason"
									class="w-full border rounded-lg p-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-red-300"
									:placeholder="__('Enter reason for rejection...')"
								></textarea>
							</div>
							<div class="flex flex-row gap-3">
								<Button
									v-if="!showPrimaryRejectReason"
									@click="showPrimaryRejectReason = true"
									class="w-full py-5"
									variant="subtle"
									theme="red"
								>
									{{ __("Reject") }}
								</Button>
								<Button
									v-else
									@click="handlePrimaryReject"
									class="w-full py-5"
									variant="subtle"
									theme="red"
									:disabled="!primaryRejectReason?.trim()"
								>
									{{ __("Confirm Reject") }}
								</Button>
								<Button
									@click="handlePrimaryApprove"
									class="w-full py-5"
									variant="solid"
									theme="green"
								>
									{{ __("Approve") }}
								</Button>
							</div>
						</template>

						<!-- Waiting message for non-secondary users -->
						<div
							v-else-if="isPendingSecondaryByOther"
							class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3"
						>
							{{ __("Forwarded to {0} for secondary approval", [permissionRequest.custom_secondary_approver_name || permissionRequest.custom_secondary_leave_approver]) }}
						</div>

						<!-- Secondary approver buttons -->
						<template v-else-if="isSecondaryApproverPending">
							<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
								{{ __("Waiting for your approval") }}
							</div>
							<div v-if="showRejectReason" class="w-full mb-2">
								<label class="text-sm text-gray-600 mb-1 block">{{ __("Reason for Rejection") }} *</label>
								<textarea
									v-model="rejectReason"
									class="w-full border rounded-lg p-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-red-300"
									:placeholder="__('Enter reason for rejection...')"
								></textarea>
							</div>
							<div class="flex flex-row gap-3">
								<Button
									v-if="!showRejectReason"
									@click="showRejectReason = true"
									class="w-full py-5"
									variant="subtle"
									theme="red"
								>
									{{ __("Reject") }}
								</Button>
								<Button
									v-else
									@click="handleSecondaryAction('reject')"
									class="w-full py-5"
									variant="subtle"
									theme="red"
									:disabled="!rejectReason?.trim()"
								>
									{{ __("Confirm Reject") }}
								</Button>
								<Button
									@click="handleSecondaryAction('approve')"
									class="w-full py-5"
									variant="solid"
									theme="green"
								>
									{{ __("Approve & Submit") }}
								</Button>
							</div>
						</template>
					</div>
				</template>
			</FormView>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource, toast } from "frappe-ui"
import { ref, watch, inject, computed } from "vue"
import { useRouter } from "vue-router"

import FormView from "@/components/FormView.vue"
import ApprovalStageTracker from "@/components/ApprovalStageTracker.vue"
import PermissionBalanceBanner from "@/components/PermissionBalanceBanner.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)

const permissionRequest = ref({})

// Fetch available permission hours
const availableHours = createResource({
	url: "hrms.hr.doctype.employee_permission.employee_permission.get_available_permission_hours",
	params: { employee: currEmployee.value, date: today },
	auto: true,
})

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Employee Permission" },
	transform(data) {
		// Fields to completely remove
		const excludeFields = [
			"naming_series",
			// Remove secondary approval section entirely
			"secondary_approval_section",
			"custom_secondary_leave_approver",
			"custom_secondary_approver_name",
			"column_break_16",
			"custom_approval_stage",
			// Remove auto-computed duration (shown in balance banner)
			"duration",
			// Remove column breaks for cleaner mobile layout
			"column_break_3",
			"column_break_10",
			"permission_details_section",
			// Remove leave approver fields (handled by backend)
			"leave_approver",
			"leave_approver_name",
			"company",
			"department",
		]

		const employeeFields = [
			"employee",
			"employee_name",
			"status",
		]

		if (!props.id) excludeFields.push(...employeeFields)

		let fields = data.filter((field) => !excludeFields.includes(field.fieldname))

		// Set default date
		const dateField = fields.find(f => f.fieldname === "permission_date")
		if (dateField) dateField.default = today

		return fields
	},
	onSuccess() {
		availableHours.reload()
	},
})
formFields.reload()

// Fetch approval details for existing docs
const approvalDetails = createResource({
	url: "hrms.hr.doctype.employee_permission.employee_permission.get_permission_approval_details",
	params: { employee_permission: props.id },
	auto: !!props.id,
})

// Two-level approval computed
const isSecondaryApproverPending = computed(() => {
	return (
		permissionRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id === permissionRequest.value.custom_secondary_leave_approver &&
		permissionRequest.value.docstatus === 0
	)
})

const isPendingSecondaryByOther = computed(() => {
	return (
		permissionRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id !== permissionRequest.value.custom_secondary_leave_approver &&
		permissionRequest.value.docstatus === 0 &&
		permissionRequest.value.custom_secondary_leave_approver
	)
})

const isProjectReportingPending = computed(() => {
	return (
		props.id &&
		permissionRequest.value.custom_secondary_leave_approver &&
		permissionRequest.value.custom_approval_stage === "Pending Project Reporting Approval" &&
		permissionRequest.value.status === "Open" &&
		permissionRequest.value.docstatus === 0 &&
		sessionEmployee.data?.user_id === permissionRequest.value.leave_approver
	)
})

const showApprovalActions = computed(() => {
	return (
		props.id &&
		permissionRequest.value.custom_secondary_leave_approver &&
		(permissionRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" ||
		isProjectReportingPending.value) &&
		permissionRequest.value.docstatus === 0
	)
})

const showRejectReason = ref(false)
const rejectReason = ref("")
const showPrimaryRejectReason = ref(false)
const primaryRejectReason = ref("")

function handleSecondaryAction(action) {
	const method = action === "approve"
		? "hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_approve"
		: "hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_reject"

	let params = { employee_permission: props.id }
	if (action === "reject") {
		if (!rejectReason.value?.trim()) return
		params.reason = rejectReason.value.trim()
	}

	createResource({
		url: method,
		params: params,
		auto: true,
		onSuccess(data) {
			toast({
				title: __("Success"),
				text: data.message,
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: action === "approve" ? "text-green-500" : "text-red-500",
			})
			router.back()
		},
		onError() {
			toast({
				title: __("Error"),
				text: __("Action failed. Please try again."),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
		},
	})
}

function handlePrimaryReject() {
	if (!primaryRejectReason.value?.trim()) return

	createResource({
		url: "hrms.hr.doctype.employee_permission.employee_permission.permission_project_reporting_reject",
		params: {
			employee_permission: props.id,
			reason: primaryRejectReason.value.trim(),
		},
		auto: true,
		onSuccess(data) {
			toast({
				title: __("Success"),
				text: data.message,
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			router.back()
		},
		onError() {
			toast({
				title: __("Error"),
				text: __("Action failed. Please try again."),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
		},
	})
}

function handlePrimaryApprove() {
	createResource({
		url: "frappe.client.set_value",
		params: {
			doctype: "Employee Permission",
			name: props.id,
			fieldname: "status",
			value: "Approved",
		},
		auto: true,
		onSuccess() {
			toast({
				title: __("Success"),
				text: __("Permission Request approved and forwarded for secondary approval."),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
			router.back()
		},
		onError() {
			toast({
				title: __("Error"),
				text: __("Approval failed. Please try again."),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
		},
	})
}

// Set defaults for new form
watch(
	() => permissionRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== currEmployee.value) {
			setFormReadOnly()
		}
		currEmployee.value = employee_id
		// Reload available hours for this employee
		availableHours.fetch({ employee: employee_id, date: today })
	}
)

// Reload available hours when date changes
watch(
	() => permissionRequest.value.permission_date,
	(date) => {
		if (date) {
			availableHours.fetch({ employee: currEmployee.value, date: date })
		}
	}
)

function setFormReadOnly() {
	if (permissionRequest.value.leave_approver === sessionEmployee.data.user_id) return
	if (permissionRequest.value.custom_secondary_leave_approver === sessionEmployee.data.user_id) return
	formFields.data?.map((field) => (field.read_only = true))
}

function validateForm() {
	permissionRequest.value.employee = currEmployee.value
	if (!permissionRequest.value.permission_date) {
		permissionRequest.value.permission_date = today
	}
}
</script>
