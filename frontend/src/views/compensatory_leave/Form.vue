<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Compensatory Leave Request"
				v-model="compRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showFormButton="showFormButton"
				@validateForm="validateForm"
			>
				<template #formButton v-if="showApprovalActions">
					<div class="flex flex-col gap-3 w-full">
						<!-- Approval Stage Tracker -->
						<ApprovalStageTracker
							v-if="approvalDetails?.data && compRequest.custom_secondary_leave_approver"
							:doc="compRequest"
							:approvalDetails="approvalDetails"
						/>

						<!-- Primary approver buttons -->
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
								>{{ __("Reject") }}</Button>
								<Button
									v-else
									@click="handlePrimaryReject"
									class="w-full py-5"
									variant="subtle"
									theme="red"
									:disabled="!primaryRejectReason?.trim()"
								>{{ __("Confirm Reject") }}</Button>
								<Button
									@click="handlePrimaryApprove"
									class="w-full py-5"
									variant="solid"
									theme="green"
								>
									{{ compRequest.custom_secondary_leave_approver ? __("Approve") : __("Approve & Submit") }}
								</Button>
							</div>
						</template>

						<!-- Forwarded to secondary — waiting message -->
						<div
							v-else-if="isPendingSecondaryByOther"
							class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3"
						>
							{{ __("Forwarded to {0} for secondary approval", [compRequest.custom_secondary_approver_name || compRequest.custom_secondary_leave_approver]) }}
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
								>{{ __("Reject") }}</Button>
								<Button
									v-else
									@click="handleSecondaryAction('reject')"
									class="w-full py-5"
									variant="subtle"
									theme="red"
									:disabled="!rejectReason?.trim()"
								>{{ __("Confirm Reject") }}</Button>
								<Button
									@click="handleSecondaryAction('approve')"
									class="w-full py-5"
									variant="solid"
									theme="green"
								>{{ __("Approve & Submit") }}</Button>
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
import { isDocumentOwner, isApprovalOwnerContextReady } from "@/utils/twoLevelApproval.js"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: { type: String, required: false },
})

const sessionEmployee = inject("$employee")
const compRequest = ref({})

// ── Form fields ───────────────────────────────────────────────────────────────
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Compensatory Leave Request" },
	transform(data) {
		const excludeFields = [
			"naming_series",
			"leave_allocation",
			"column_break_2",
			"column_break_4",
			"worked_on",
			"amended_from",
			// Hidden — shown via ApprovalStageTracker
			"custom_secondary_leave_approver",
			"custom_secondary_approver_name",
			"custom_approval_stage",
			"approver",
			"approver_name",
		]
		const employeeFields = ["employee", "employee_name", "department"]
		if (!props.id) excludeFields.push(...employeeFields)

		let fields = data.filter((f) => !excludeFields.includes(f.fieldname))

		// Default leave type to Compensatory Off and lock it
		const leaveTypeField = fields.find((f) => f.fieldname === "leave_type")
		if (leaveTypeField && !props.id) {
			leaveTypeField.default = "Compensatory Off"
			leaveTypeField.read_only = 1
		}

		const fromField = fields.find((f) => f.fieldname === "work_from_date")
		if (fromField && !props.id) fromField.default = today

		const toField = fields.find((f) => f.fieldname === "work_end_date")
		if (toField && !props.id) toField.default = today

		const halfDayDate = fields.find((f) => f.fieldname === "half_day_date")
		if (halfDayDate) halfDayDate.hidden = !compRequest.value.half_day

		return fields
	},
})
formFields.reload()

// ── Auto-set approver for new requests ───────────────────────────────────────
const approvalInfo = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: sessionEmployee.data.name },
	auto: !props.id,
	onSuccess(data) {
		if (!props.id) {
			compRequest.value.approver = data.leave_approver
			compRequest.value.approver_name = data.leave_approver_name
			if (data.secondary_leave_approver) {
				compRequest.value.custom_secondary_leave_approver = data.secondary_leave_approver
				compRequest.value.custom_secondary_approver_name = data.secondary_approver_name
			}
		}
	},
})

// ── Approval details for existing docs (tracker UI) ──────────────────────────
// Normalise keys so ApprovalStageTracker (which expects leave_approver_name / leave_approver_image)
// works with the compensatory API response (approver_name / approver_image).
const approvalDetails = createResource({
	url: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.get_compensatory_approval_details",
	params: { compensatory_leave_request: props.id },
	auto: !!props.id,
	transform(data) {
		// ApprovalStageTracker reads leave_approver_name / leave_approver_image
		return {
			...data,
			leave_approver_name: data.approver_name,
			leave_approver_image: data.approver_image,
		}
	},
})

// ── Two-level approval computed ───────────────────────────────────────────────
const employeeDocLoaded = computed(() => !!props.id && !!compRequest.value?.employee)

const ownerContextReady = computed(() =>
	isApprovalOwnerContextReady(sessionEmployee, approvalDetails, compRequest.value?.employee)
)

const isCurrentUserEmployee = computed(
	() => employeeDocLoaded.value && isDocumentOwner(sessionEmployee, approvalDetails, compRequest.value?.employee)
)

const isProjectReportingPending = computed(() => {
	if (!props.id || !employeeDocLoaded.value || !ownerContextReady.value || isCurrentUserEmployee.value)
		return false
	return (
		compRequest.value.status === "Open" &&
		compRequest.value.docstatus === 0 &&
		sessionEmployee.data?.user_id === compRequest.value.approver &&
		(!compRequest.value.custom_approval_stage ||
			compRequest.value.custom_approval_stage === "Pending Project Reporting Approval")
	)
})

const isSecondaryApproverPending = computed(() => {
	if (!props.id || !employeeDocLoaded.value || !ownerContextReady.value || isCurrentUserEmployee.value)
		return false
	return (
		compRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id === compRequest.value.custom_secondary_leave_approver &&
		compRequest.value.docstatus === 0
	)
})

const isPendingSecondaryByOther = computed(() => {
	if (!props.id || !employeeDocLoaded.value || !ownerContextReady.value) return false
	return (
		compRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id !== compRequest.value.custom_secondary_leave_approver &&
		compRequest.value.docstatus === 0 &&
		compRequest.value.custom_secondary_leave_approver
	)
})

const showApprovalActions = computed(() => {
	if (!props.id || compRequest.value.docstatus !== 0) return false
	return isProjectReportingPending.value || isSecondaryApproverPending.value || isPendingSecondaryByOther.value
})

const showFormButton = computed(() => {
	if (!props.id) return true
	if (!employeeDocLoaded.value || !ownerContextReady.value) return false
	return !showApprovalActions.value && !isCurrentUserEmployee.value
})

// ── Approval action state ─────────────────────────────────────────────────────
const showRejectReason = ref(false)
const rejectReason = ref("")
const showPrimaryRejectReason = ref(false)
const primaryRejectReason = ref("")

function handlePrimaryApprove() {
	if (isCurrentUserEmployee.value) return
	const hasSecondary = !!compRequest.value.custom_secondary_leave_approver

	if (hasSecondary) {
		createResource({
			url: "frappe.client.set_value",
			params: { doctype: "Compensatory Leave Request", name: props.id, fieldname: "status", value: "Approved" },
			auto: true,
			onSuccess() {
				toast({ title: __("Success"), text: __("Forwarded for secondary approval."), icon: "check-circle", position: "bottom-center", iconClasses: "text-green-500" })
				router.back()
			},
			onError() {
				toast({ title: __("Error"), text: __("Approval failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			},
		})
	} else {
		createResource({
			url: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_approve_submit",
			params: { compensatory_leave_request: props.id },
			auto: true,
			onSuccess(data) {
				toast({ title: __("Success"), text: data.message, icon: "check-circle", position: "bottom-center", iconClasses: "text-green-500" })
				router.back()
			},
			onError() {
				toast({ title: __("Error"), text: __("Approval failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			},
		})
	}
}

function handlePrimaryReject() {
	if (isCurrentUserEmployee.value) return
	if (!primaryRejectReason.value?.trim()) return
	const hasSecondary = !!compRequest.value.custom_secondary_leave_approver

	const url = hasSecondary
		? "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_project_reporting_reject"
		: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_reject_submit"

	createResource({
		url,
		params: { compensatory_leave_request: props.id, reason: primaryRejectReason.value.trim() },
		auto: true,
		onSuccess(data) {
			toast({ title: __("Success"), text: data.message, icon: "check-circle", position: "bottom-center", iconClasses: "text-red-500" })
			router.back()
		},
		onError() {
			toast({ title: __("Error"), text: __("Action failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
		},
	})
}

function handleSecondaryAction(action) {
	if (isCurrentUserEmployee.value) return
	const method = action === "approve"
		? "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_secondary_approve"
		: "hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request.compensatory_secondary_reject"

	const params = { compensatory_leave_request: props.id }
	if (action === "reject") {
		if (!rejectReason.value?.trim()) return
		params.reason = rejectReason.value.trim()
	}

	createResource({
		url: method,
		params,
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
			toast({ title: __("Error"), text: __("Action failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
		},
	})
}

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(
	() => compRequest.value.half_day,
	(half_day) => {
		if (!formFields.data) return
		const halfDayDate = formFields.data.find((f) => f.fieldname === "half_day_date")
		if (halfDayDate) {
			halfDayDate.hidden = !half_day
			halfDayDate.reqd = !!half_day
		}
	}
)

watch(
	() => compRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== sessionEmployee.data.name) {
			setFormReadOnly()
		}
	}
)

// ── Helpers ───────────────────────────────────────────────────────────────────
function setFormReadOnly() {
	const userId = sessionEmployee.data.user_id
	const isApprover =
		userId === compRequest.value.approver ||
		userId === compRequest.value.custom_secondary_leave_approver

	if (isApprover) {
		const contentFields = ["work_from_date", "work_end_date", "half_day", "half_day_date", "reason", "leave_type"]
		formFields.data?.forEach((field) => {
			if (contentFields.includes(field.fieldname)) field.read_only = true
		})
	} else {
		formFields.data?.forEach((field) => (field.read_only = true))
	}
}

function validateForm() {
	compRequest.value.employee = sessionEmployee.data.name
	if (!compRequest.value.leave_type) {
		compRequest.value.leave_type = "Compensatory Off"
	}
	if (approvalInfo.data) {
		if (!compRequest.value.approver) {
			compRequest.value.approver = approvalInfo.data.leave_approver
			compRequest.value.approver_name = approvalInfo.data.leave_approver_name
		}
		if (!compRequest.value.custom_secondary_leave_approver && approvalInfo.data.secondary_leave_approver) {
			compRequest.value.custom_secondary_leave_approver = approvalInfo.data.secondary_leave_approver
			compRequest.value.custom_secondary_approver_name = approvalInfo.data.secondary_approver_name
		}
	}
}
</script>
