<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Attendance Request"
				displayName="Request"
				v-model="attendanceRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showFormButton="showFormButton"
				@validateForm="validateForm"
			>
				<template #formButton v-if="showApprovalActions || showEmployeeTracker">
					<div class="flex flex-col gap-3 w-full">
						<!-- Read-only tracker for the employee viewing their own request -->
						<template v-if="showEmployeeTracker">
							<ApprovalStageTracker
								v-if="approvalDetails?.data"
								:doc="attendanceRequest"
								:approvalDetails="approvalDetails"
							/>
							<div
								v-if="!approvalDetails?.data?.loading && !attendanceRequest.approver"
								class="text-center text-sm text-gray-500 bg-gray-50 rounded-lg p-3"
							>
								{{ __("No approver assigned for this request.") }}
							</div>
						</template>

						<!-- Primary (leave approver) Approve/Reject buttons -->
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
									{{ attendanceRequest.custom_secondary_leave_approver ? __("Approve") : __("Approve & Submit") }}
								</Button>
							</div>
						</template>

						<!-- Waiting message for non-secondary users -->
						<div
							v-else-if="isPendingSecondaryByOther"
							class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3"
						>
							{{ __("Forwarded to {0} for secondary approval", [attendanceRequest.custom_secondary_approver_name || attendanceRequest.custom_secondary_leave_approver]) }}
						</div>

						<!-- Secondary approver Approve/Reject buttons -->
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
const router = useRouter()
const sessionEmployee = inject("$employee")

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

// reactive object to store form data
const attendanceRequest = ref({})

// Auto-fetch approver details for new requests (handled in background)
const approvalInfo = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: sessionEmployee.data?.name },
	auto: !props.id,
	onSuccess(data) {
		if (!props.id) {
			attendanceRequest.value.approver = data.leave_approver
			attendanceRequest.value.approver_name = data.leave_approver_name
			if (data.secondary_leave_approver) {
				attendanceRequest.value.custom_secondary_leave_approver = data.secondary_leave_approver
				attendanceRequest.value.custom_secondary_approver_name = data.secondary_approver_name
			}
		}
	},
})

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Attendance Request" },
	auto: true,
	transform(data) {
		// Fields to always exclude from the form view
		const excludeFields = [
			"secondary_approval_section",
			"custom_secondary_leave_approver",
			"custom_secondary_approver_name",
			"custom_column_break_secondary",
			"custom_approval_stage",
			// Approver fields handled in background
			"approver",
			"approver_name",
		]

		// When creating new, also exclude employee/company/status (auto-set)
		const newOnlyExcludes = ["employee", "employee_name", "status", "company"]
		if (!props.id) excludeFields.push(...newOnlyExcludes)

		let fields = data.filter((field) => !excludeFields.includes(field.fieldname))

		// Hide half_day_date by default
		fields = fields.map((field) => {
			if (field.fieldname === "half_day_date") field.hidden = true
			return field
		})

		return fields
	},
})

// Fetch approval details for existing docs (for ApprovalStageTracker)
const approvalDetails = createResource({
	url: "hrms.hr.doctype.attendance_request.attendance_request.get_secondary_approval_details",
	params: { attendance_request: props.id },
	auto: !!props.id,
})

// ── Approval flow computed ────────────────────────────────────────────────────

// True when current user IS the employee who owns this request
const isCurrentUserEmployee = computed(() =>
	!!props.id && sessionEmployee.data?.name === attendanceRequest.value.employee
)

// Primary leave approver can approve (covers both with-secondary and without-secondary flows)
const isProjectReportingPending = computed(() => {
	if (!props.id || isCurrentUserEmployee.value) return false
	return (
		attendanceRequest.value.status === "Open" &&
		attendanceRequest.value.docstatus === 0 &&
		sessionEmployee.data?.user_id === attendanceRequest.value.approver &&
		(!attendanceRequest.value.custom_approval_stage ||
			attendanceRequest.value.custom_approval_stage === "Pending Project Reporting Approval")
	)
})

// Secondary approver can approve
const isSecondaryApproverPending = computed(() => {
	if (!props.id || isCurrentUserEmployee.value) return false
	return (
		attendanceRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id === attendanceRequest.value.custom_secondary_leave_approver &&
		attendanceRequest.value.docstatus === 0
	)
})

// Waiting message: forwarded to secondary but current user is not secondary
const isPendingSecondaryByOther = computed(() => {
	if (!props.id) return false
	return (
		attendanceRequest.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id !== attendanceRequest.value.custom_secondary_leave_approver &&
		attendanceRequest.value.docstatus === 0 &&
		attendanceRequest.value.custom_secondary_leave_approver
	)
})

// Show read-only approval tracker for the employee viewing their own pending request
const showEmployeeTracker = computed(() =>
	!!props.id && isCurrentUserEmployee.value && attendanceRequest.value.docstatus === 0
)

// Show custom approval action buttons/messages (replaces default form button)
const showApprovalActions = computed(() => {
	if (!props.id || attendanceRequest.value.docstatus !== 0) return false
	return (
		isProjectReportingPending.value ||
		isSecondaryApproverPending.value ||
		isPendingSecondaryByOther.value
	)
})

// Show default form Save/Submit button:
// - Always for new requests (no id)
// - For existing: only if no approval actions AND not employee's own request
const showFormButton = computed(() => {
	if (!props.id) return true
	return !showApprovalActions.value && !showEmployeeTracker.value
})

// ── Approval state ────────────────────────────────────────────────────────────
const showRejectReason = ref(false)
const rejectReason = ref("")
const showPrimaryRejectReason = ref(false)
const primaryRejectReason = ref("")

function handlePrimaryApprove() {
	const hasSecondary = !!attendanceRequest.value.custom_secondary_leave_approver

	if (hasSecondary) {
		// Two-level flow: set status=Approved, backend forwards to secondary
		createResource({
			url: "frappe.client.set_value",
			params: {
				doctype: "Attendance Request",
				name: props.id,
				fieldname: "status",
				value: "Approved",
			},
			auto: true,
			onSuccess() {
				toast({
					title: __("Success"),
					text: __("Request approved and forwarded for secondary approval."),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
				router.back()
			},
			onError() {
				toast({ title: __("Error"), text: __("Approval failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			},
		})
	} else {
		// Simple flow (no secondary): approve and submit in one step
		createResource({
			url: "hrms.hr.doctype.attendance_request.attendance_request.attendance_request_approve_submit",
			params: { attendance_request: props.id },
			auto: true,
			onSuccess() {
				toast({
					title: __("Success"),
					text: __("Attendance Request approved and submitted."),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
				router.back()
			},
			onError() {
				toast({ title: __("Error"), text: __("Approval failed. Please try again."), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			},
		})
	}
}

function handlePrimaryReject() {
	if (!primaryRejectReason.value?.trim()) return
	const hasSecondary = !!attendanceRequest.value.custom_secondary_leave_approver

	const url = hasSecondary
		? "hrms.hr.doctype.attendance_request.attendance_request.project_reporting_reject"
		: "hrms.hr.doctype.attendance_request.attendance_request.attendance_request_reject_submit"

	createResource({
		url,
		params: { attendance_request: props.id, reason: primaryRejectReason.value.trim() },
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
	const method =
		action === "approve"
			? "hrms.hr.doctype.attendance_request.attendance_request.secondary_approve"
			: "hrms.hr.doctype.attendance_request.attendance_request.secondary_reject"

	const params = { attendance_request: props.id }
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

// ── Form watchers ─────────────────────────────────────────────────────────────

watch(
	() => attendanceRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== sessionEmployee.data.name) {
			setFormReadOnly()
		}
	}
)

watch(
	() => attendanceRequest.value.from_date,
	(from_date) => {
		if (!attendanceRequest.value.to_date) {
			attendanceRequest.value.to_date = from_date
		}
	}
)

watch(
	() => [attendanceRequest.value.from_date, attendanceRequest.value.to_date],
	([from_date, to_date]) => validateDates(from_date, to_date)
)

watch(
	() => attendanceRequest.value.half_day,
	(half_day) => {
		const field = formFields.data?.find((f) => f.fieldname === "half_day_date")
		if (field) field.hidden = !half_day
	}
)

// ── Helpers ───────────────────────────────────────────────────────────────────

function setFormReadOnly() {
	const userId = sessionEmployee.data.user_id
	const isApprover =
		userId === attendanceRequest.value.approver ||
		userId === attendanceRequest.value.custom_secondary_leave_approver

	if (isApprover) {
		// Approvers can only change status — lock content fields
		const contentFields = ["from_date", "to_date", "half_day", "half_day_date", "reason", "explanation"]
		formFields.data?.forEach((field) => {
			if (contentFields.includes(field.fieldname)) field.read_only = true
		})
	} else {
		formFields.data?.forEach((field) => (field.read_only = true))
	}
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return
	const field = formFields.data?.find((f) => f.fieldname === "from_date")
	if (field) field.error_message = from_date > to_date ? __("To Date cannot be before From Date") : ""
}

function validateForm() {
	attendanceRequest.value.employee = sessionEmployee.data.name
	// Ensure approvers are set from fetched data (fallback)
	if (approvalInfo.data) {
		if (!attendanceRequest.value.approver) {
			attendanceRequest.value.approver = approvalInfo.data.leave_approver
			attendanceRequest.value.approver_name = approvalInfo.data.leave_approver_name
		}
		if (!attendanceRequest.value.custom_secondary_leave_approver && approvalInfo.data.secondary_leave_approver) {
			attendanceRequest.value.custom_secondary_leave_approver = approvalInfo.data.secondary_leave_approver
			attendanceRequest.value.custom_secondary_approver_name = approvalInfo.data.secondary_approver_name
		}
	}
}
</script>
