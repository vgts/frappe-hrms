<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Attendance Regularization"
				v-model="regularization"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:showFormButton="!showApprovalActions"
				@validateForm="validateForm"
			>
				<template #formButton v-if="showApprovalActions">
					<div class="flex flex-col gap-3 w-full">
						<ApprovalStageTracker
							v-if="approvalDetails?.data && regularization.custom_secondary_leave_approver"
							:doc="regularization"
							:approvalDetails="approvalDetails"
						/>

						<!-- Project Reporting approver buttons -->
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

						<div
							v-else-if="isPendingSecondaryByOther"
							class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3"
						>
							{{ __("Forwarded to {0} for secondary approval", [regularization.custom_secondary_approver_name || regularization.custom_secondary_leave_approver]) }}
						</div>

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

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: { type: String, required: false },
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const regularization = ref({})

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Attendance Regularization" },
	transform(data) {
		const excludeFields = [
			"naming_series",
			"approval_section",
			"custom_secondary_leave_approver",
			"custom_secondary_approver_name",
			"column_break_approval",
			"custom_approval_stage",
			"column_break_4",
			"column_break_reg",
			"column_break_desc",
			"regularization_details_section",
			"leave_approver",
			"leave_approver_name",
			"company",
			"department",
			"total_hours",
		]

		const employeeFields = ["employee", "employee_name", "status"]
		if (!props.id) excludeFields.push(...employeeFields)

		let fields = data.filter((field) => !excludeFields.includes(field.fieldname))

		// Set default date
		const dateField = fields.find(f => f.fieldname === "attendance_date")
		if (dateField) dateField.default = today

		return fields
	},
})
formFields.reload()

const approvalDetails = createResource({
	url: "hrms.hr.doctype.attendance_regularization.attendance_regularization.get_regularization_approval_details",
	params: { attendance_regularization: props.id },
	auto: !!props.id,
})

// Auto-fetch approver details for new requests
const approvalInfo = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: currEmployee.value },
	auto: !props.id,
	onSuccess(data) {
		if (!props.id) {
			regularization.value.leave_approver = data.leave_approver
			regularization.value.leave_approver_name = data.leave_approver_name
			if (data.secondary_leave_approver) {
				regularization.value.custom_secondary_leave_approver = data.secondary_leave_approver
				regularization.value.custom_secondary_approver_name = data.secondary_approver_name
			}
		}
	},
})

const isSecondaryApproverPending = computed(() => {
	return (
		regularization.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id === regularization.value.custom_secondary_leave_approver &&
		regularization.value.docstatus === 0
	)
})

const isPendingSecondaryByOther = computed(() => {
	return (
		regularization.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id !== regularization.value.custom_secondary_leave_approver &&
		regularization.value.docstatus === 0 &&
		regularization.value.custom_secondary_leave_approver
	)
})

const isProjectReportingPending = computed(() => {
	return (
		props.id &&
		regularization.value.custom_secondary_leave_approver &&
		regularization.value.custom_approval_stage === "Pending Project Reporting Approval" &&
		regularization.value.status === "Open" &&
		regularization.value.docstatus === 0 &&
		sessionEmployee.data?.user_id === regularization.value.leave_approver
	)
})

const showApprovalActions = computed(() => {
	return (
		props.id &&
		regularization.value.custom_secondary_leave_approver &&
		(regularization.value.custom_approval_stage === "Pending Secondary Reporting Approval" ||
		isProjectReportingPending.value) &&
		regularization.value.docstatus === 0
	)
})

const showRejectReason = ref(false)
const rejectReason = ref("")
const showPrimaryRejectReason = ref(false)
const primaryRejectReason = ref("")

function handleSecondaryAction(action) {
	const method = action === "approve"
		? "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_approve"
		: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_reject"

	let params = { attendance_regularization: props.id }
	if (action === "reject") {
		if (!rejectReason.value?.trim()) return
		params.reason = rejectReason.value.trim()
	}

	createResource({
		url: method, params, auto: true,
		onSuccess(data) {
			toast({ title: __("Success"), text: data.message, icon: "check-circle", position: "bottom-center", iconClasses: action === "approve" ? "text-green-500" : "text-red-500" })
			router.back()
		},
		onError() {
			toast({ title: __("Error"), text: __("Action failed."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
		},
	})
}

function handlePrimaryReject() {
	if (!primaryRejectReason.value?.trim()) return
	createResource({
		url: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_project_reporting_reject",
		params: { attendance_regularization: props.id, reason: primaryRejectReason.value.trim() },
		auto: true,
		onSuccess(data) {
			toast({ title: __("Success"), text: data.message, icon: "check-circle", position: "bottom-center", iconClasses: "text-red-500" })
			router.back()
		},
		onError() {
			toast({ title: __("Error"), text: __("Action failed."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
		},
	})
}

function handlePrimaryApprove() {
	createResource({
		url: "frappe.client.set_value",
		params: { doctype: "Attendance Regularization", name: props.id, fieldname: "status", value: "Approved" },
		auto: true,
		onSuccess() {
			toast({ title: __("Success"), text: __("Regularization approved."), icon: "check-circle", position: "bottom-center", iconClasses: "text-green-500" })
			router.back()
		},
		onError() {
			toast({ title: __("Error"), text: __("Approval failed."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
		},
	})
}

watch(
	() => regularization.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== currEmployee.value) {
			formFields.data?.forEach((field) => (field.read_only = true))
		}
		currEmployee.value = employee_id
		if (!props.id) {
			approvalInfo.fetch({ employee: employee_id })
		}
	}
)

function validateForm() {
	regularization.value.employee = currEmployee.value
	if (!regularization.value.attendance_date) {
		regularization.value.attendance_date = today
	}
	// Ensure approvers are set from fetched data
	if (approvalInfo.data) {
		if (!regularization.value.leave_approver) {
			regularization.value.leave_approver = approvalInfo.data.leave_approver
			regularization.value.leave_approver_name = approvalInfo.data.leave_approver_name
		}
		if (!regularization.value.custom_secondary_leave_approver && approvalInfo.data.secondary_leave_approver) {
			regularization.value.custom_secondary_leave_approver = approvalInfo.data.secondary_leave_approver
			regularization.value.custom_secondary_approver_name = approvalInfo.data.secondary_approver_name
		}
	}
}
</script>
