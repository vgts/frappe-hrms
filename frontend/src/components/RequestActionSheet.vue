<template>
	<div
		v-if="document?.doc"
		class="bg-white w-full flex flex-col items-center justify-center pb-5 max-h-[calc(100vh-5rem)]"
	>
		<!-- Header -->
		<div
			class="w-full flex flex-row gap-2 pt-8 pb-5 border-b justify-center items-center sticky top-0 z-[100]"
		>
			<span class="text-gray-900 font-bold text-lg text-center">
				{{ __(document?.doctype) }}
			</span>
			<FeatherIcon
				v-if="props.showOpenForm"
				name="external-link"
				class="h-4 w-4 text-gray-500 cursor-pointer"
				@click="openFormView"
			/>
		</div>

		<!-- Request Summary -->
		<div class="w-full p-4 overflow-auto">
			<div class="flex flex-col items-center justify-center gap-5">
				<!-- Approval Stage Tracker -->
				<ApprovalStageTracker
					v-if="isLeaveWithSecondaryApprover"
					:doc="document.doc"
					:approvalDetails="approvalDetails"
				/>

				<div
					v-for="field in fieldsWithValues"
					:key="field.fieldname"
					:class="[
						['Small Text', 'Text', 'Long Text', 'Table', 'geolocation'].includes(
							field.fieldtype
						)
							? 'flex-col'
							: 'flex-row items-center justify-between',
						'flex w-full',
					]"
				>
					<div class="text-gray-600 text-base">{{ __(field.label, null, props.modelValue?.doctype) }}</div>
					<component
						v-if="field.fieldtype === 'Table'"
						:is="field.component"
						:doc="document?.doc"
					/>
					<FormattedField
						v-else
						:value="field.value"
						:fieldtype="field.fieldtype"
						:fieldname="field.fieldname"
					/>
				</div>

				<!-- Attachments -->
				<div
					class="flex flex-col gap-2 w-full"
					v-if="attachedFiles?.data?.length"
				>
					<div class="text-gray-600 text-base">{{ __('Attachments') }}</div>
					<ul class="w-full flex flex-col items-center gap-2">
						<li
							class="bg-gray-100 rounded p-2 w-full"
							v-for="(file, index) in attachedFiles.data"
							:key="index"
						>
							<div
								class="flex flex-row items-center justify-between text-gray-700 text-sm"
							>
								<span class="grow" @click="showFilePreview(file)">
									{{ file.file_name || file.name }}
								</span>
							</div>
						</li>
					</ul>
				</div>
			</div>
		</div>

		<!-- Actions -->
		<WorkflowActionSheet
			v-if="workflow?.hasWorkflow"
			:doc="document.doc"
			:workflow="workflow"
			view="actionSheet"
		/>

		<!-- Secondary Approver: Approve/Reject (when pending their approval) -->
		<div
			v-else-if="isSecondaryApproverPending"
			class="flex w-full flex-col gap-3 sticky bottom-0 border-t z-[100] p-4"
		>
			<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
				{{ __("Waiting for your approval") }}
			</div>
			<!-- Rejection reason input -->
			<div v-if="showRejectReason" class="w-full mb-2">
				<label class="text-sm text-gray-600 mb-1 block">{{ __("Reason for Rejection") }} *</label>
				<textarea
					v-model="rejectReason"
					class="w-full border rounded-lg p-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-red-300"
					:placeholder="__('Enter reason for rejection...')"
				></textarea>
			</div>
			<div class="flex flex-row items-center justify-between gap-3">
				<Button
					v-if="!showRejectReason"
					@click="showRejectReason = true"
					class="w-full py-5"
					variant="subtle"
					theme="red"
				>
					<template #prefix>
						<FeatherIcon name="x" class="w-4" />
					</template>
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
					<template #prefix>
						<FeatherIcon name="x" class="w-4" />
					</template>
					{{ __("Confirm Reject") }}
				</Button>
				<Button
					@click="handleSecondaryAction('approve')"
					class="w-full py-5"
					variant="solid"
					theme="green"
				>
					<template #prefix>
						<FeatherIcon name="check" class="w-4" />
					</template>
					{{ __("Approve & Submit") }}
				</Button>
			</div>
		</div>

		<!-- Leave Approver: After approving, show forwarded message (no submit) -->
		<div
			v-else-if="isPendingSecondaryByOther"
			class="flex w-full flex-col gap-2 sticky bottom-0 border-t z-[100] p-4"
		>
			<div class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3">
				{{ __("Forwarded to {0} for secondary approval", [document.doc.custom_secondary_approver_name || document.doc.custom_secondary_leave_approver]) }}
			</div>
		</div>

		<!-- Project Reporting (Primary) Approver: Approve/Reject with reason for leave applications -->
		<div
			v-else-if="isProjectReportingPending"
			class="flex w-full flex-col gap-3 sticky bottom-0 border-t z-[100] p-4"
		>
			<!-- Rejection reason input -->
			<div v-if="showPrimaryRejectReason" class="w-full mb-2">
				<label class="text-sm text-gray-600 mb-1 block">{{ __("Reason for Rejection") }} *</label>
				<textarea
					v-model="primaryRejectReason"
					class="w-full border rounded-lg p-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-red-300"
					:placeholder="__('Enter reason for rejection...')"
				></textarea>
			</div>
			<div class="flex flex-row items-center justify-between gap-3">
				<Button
					v-if="!showPrimaryRejectReason"
					@click="showPrimaryRejectReason = true"
					class="w-full py-5"
					variant="subtle"
					theme="red"
				>
					<template #prefix>
						<FeatherIcon name="x" class="w-4" />
					</template>
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
					<template #prefix>
						<FeatherIcon name="x" class="w-4" />
					</template>
					{{ __("Confirm Reject") }}
				</Button>
				<Button
					@click="updateDocumentStatus({ status: 'Approved' })"
					class="w-full py-5"
					variant="solid"
					theme="green"
				>
					<template #prefix>
						<FeatherIcon name="check" class="w-4" />
					</template>
					{{ __("Approve") }}
				</Button>
			</div>
		</div>

		<!-- Primary Approver: Approve/Reject (standard flow for non-leave or no secondary approver) -->
		<div
			v-else-if="['Open', 'Draft'].includes(document?.doc?.[approvalField]) && hasPermission('approval')"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t z-[100] p-4"
		>
			<Button
				@click="updateDocumentStatus({ status: 'Rejected' })"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Reject") }}
			</Button>

			<Button
				@click="updateDocumentStatus({ status: 'Approved' })"
				class="w-full py-5"
				variant="solid"
				theme="green"
			>
				<template #prefix>
					<FeatherIcon name="check" class="w-4" />
				</template>
				{{ __("Approve") }}
			</Button>
		</div>

		<!-- Submit (only when no secondary approver or fully approved) -->
		<div
			v-else-if="canShowSubmitButton"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t z-[100] p-4"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 1 })"
				class="w-full py-5"
				variant="solid"
			>
				{{ __("Submit") }}
			</Button>
		</div>

		<div
			v-else-if="document?.doc?.docstatus === 1 && hasPermission('cancel')"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t z-[100] p-4"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 2 })"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Cancel") }}
			</Button>
		</div>

		<!-- File Preview Modal -->
		<ion-modal
			ref="modal"
			:is-open="showPreviewModal"
			@didDismiss="showPreviewModal = false"
		>
			<FilePreviewModal :file="selectedFile" />
		</ion-modal>
	</div>
</template>

<script setup>
import { computed, inject, ref, defineAsyncComponent, onMounted } from "vue"
import { IonModal, modalController } from "@ionic/vue"
import { useRouter } from "vue-router"
import {
	toast,
	createDocumentResource,
	createResource,
	FeatherIcon,
} from "frappe-ui"

import FormattedField from "@/components/FormattedField.vue"
import FilePreviewModal from "@/components/FilePreviewModal.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"
import ApprovalStageTracker from "@/components/ApprovalStageTracker.vue"

import { getCompanyCurrency } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"

import useWorkflow from "@/composables/workflow"

const __ = inject("$translate")
const employee = inject("$employee")

const props = defineProps({
	fields: {
		type: Array,
		required: true,
	},
	showOpenForm: {
		type: Boolean,
		default: true,
	},
	modelValue: {
		type: Object,
		required: true,
	},
})
const router = useRouter()

let showPreviewModal = ref(false)
let selectedFile = ref({})
let workflow = ref(null)
let showRejectReason = ref(false)
let rejectReason = ref("")
let showPrimaryRejectReason = ref(false)
let primaryRejectReason = ref("")

function showFilePreview(fileObj) {
	selectedFile.value = fileObj
	showPreviewModal.value = true
}

const document = createDocumentResource({
	doctype: props.modelValue.doctype,
	name: props.modelValue.name,
	auto: true,
	onSuccess(doc) {
		attachedFiles.reload()
	},
})

const attachedFiles = createResource({
	url: "hrms.api.get_attachments",
	params: {
		dt: props.modelValue.doctype,
		dn: props.modelValue.name,
	},
})

const docPermissions = createResource({
	url: "frappe.client.get_doc_permissions",
	params: { doctype: props.modelValue.doctype, docname: props.modelValue.name },
	auto: true,
})

const permittedWriteFields = createResource({
	url: "hrms.api.get_permitted_fields_for_write",
	params: { doctype: props.modelValue.doctype },
	auto: true,
})

// Fetch secondary approval details (avatars, stage) for doctypes with two-level approval
const approvalApiMap = {
	"Leave Application": {
		details: "hrms.hr.doctype.leave_application.leave_application.get_secondary_approval_details",
		detailsParam: "leave_application",
	},
	"Employee Permission": {
		details: "hrms.hr.doctype.employee_permission.employee_permission.get_permission_approval_details",
		detailsParam: "employee_permission",
	},
	"Attendance Regularization": {
		details: "hrms.hr.doctype.attendance_regularization.attendance_regularization.get_regularization_approval_details",
		detailsParam: "attendance_regularization",
	},
}
const approvalConfig = approvalApiMap[props.modelValue.doctype]
const approvalDetails = createResource({
	url: approvalConfig?.details || "hrms.hr.doctype.leave_application.leave_application.get_secondary_approval_details",
	params: { [approvalConfig?.detailsParam || "leave_application"]: props.modelValue.name },
	auto: !!approvalConfig,
})

function hasPermission(action) {
	if (action === "approval")
		return permittedWriteFields.data?.includes(approvalField.value)
	return docPermissions.data?.permissions[action]
}

const currency = computed(() => {
	let docCurrency = document?.doc?.currency

	if (!docCurrency && document?.doc?.company) {
		docCurrency = getCompanyCurrency(document?.doc?.company)
	}
	return docCurrency
})

const fieldsWithValues = computed(() => {
	return props.fields.filter((field) => {
		if (field.fieldtype === "Currency") {
			field.value = formatCurrency(
				document.doc?.[field.fieldname],
				currency.value
			)
		} else {
			if (field.fieldtype === "Table") {
				field.component = defineAsyncComponent(() =>
					import(`../components/${field.componentName}.vue`)
				)
			}
			field.value =
				document?.doc?.[field.fieldname] || props.modelValue[field.fieldname]
		}

		return field.value
	})
})

const approvalField = computed(() => {
	return props.modelValue.doctype === "Expense Claim"
		? "approval_status"
		: "status"
})

// Two-level approval computed properties
const twoLevelDoctypes = ["Leave Application", "Employee Permission", "Attendance Regularization"]
const isLeaveWithSecondaryApprover = computed(() => {
	return (
		twoLevelDoctypes.includes(props.modelValue.doctype) &&
		document.doc?.custom_secondary_leave_approver
	)
})

const isSecondaryApproverPending = computed(() => {
	return (
		isLeaveWithSecondaryApprover.value &&
		document.doc?.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		employee.data?.user_id === document.doc?.custom_secondary_leave_approver &&
		document.doc?.docstatus === 0
	)
})

const isProjectReportingPending = computed(() => {
	return (
		isLeaveWithSecondaryApprover.value &&
		document.doc?.custom_approval_stage === "Pending Project Reporting Approval" &&
		document.doc?.status === "Open" &&
		document.doc?.docstatus === 0 &&
		hasPermission("approval")
	)
})

const isPendingSecondaryByOther = computed(() => {
	return (
		isLeaveWithSecondaryApprover.value &&
		document.doc?.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		employee.data?.user_id !== document.doc?.custom_secondary_leave_approver &&
		document.doc?.docstatus === 0
	)
})

const canShowSubmitButton = computed(() => {
	if (!document?.doc || document.doc.docstatus !== 0) return false
	const isAttendanceReq = document.doc.doctype === "Attendance Request"
	const isApprovedOrRejected = ["Approved", "Rejected"].includes(document.doc[approvalField.value])

	if (!(isAttendanceReq || isApprovedOrRejected)) return false
	if (!hasPermission("submit")) return false

	// Block submit for leave applications pending approval at any level
	if (
		isLeaveWithSecondaryApprover.value &&
		["Pending Project Reporting Approval", "Pending Secondary Reporting Approval"].includes(document.doc.custom_approval_stage)
	) {
		return false
	}

	return true
})

const getSuccessMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} successfully!", [__(status)])
	} else if (docstatus) {
		return __("Document {0} successfully!", [
			docstatus === 1 ? __("submitted") : __("cancelled")]
		)
	}
}

const getFailureMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} failed!", [status === __("Approved") ? __("Approval") : __("Rejection")])
	} else if (docstatus) {
		return __('Document {0} failed!', [docstatus === 1 ? __("submission") : __("cancellation")])
	}
}

const updateDocumentStatus = ({ status = "", docstatus = 0 }) => {
	let updateValues = {}

	if (status) updateValues[approvalField.value] = status
	if (docstatus) updateValues.docstatus = docstatus

	document.setValue.submit(
		{ ...updateValues },
		{
			onSuccess() {
				if (docstatus !== 0) modalController.dismiss()

				toast({
					title: __("Success"),
					text: getSuccessMessage({ status, docstatus }),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError() {
				toast({
					title: __("Error"),
					text: getFailureMessage({ status, docstatus }),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			},
		}
	)
}

const secondaryApiMap = {
	"Leave Application": {
		approve: "hrms.hr.doctype.leave_application.leave_application.secondary_approve",
		reject: "hrms.hr.doctype.leave_application.leave_application.secondary_reject",
		primaryReject: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject",
		paramKey: "leave_application",
	},
	"Employee Permission": {
		approve: "hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_approve",
		reject: "hrms.hr.doctype.employee_permission.employee_permission.permission_secondary_reject",
		primaryReject: "hrms.hr.doctype.employee_permission.employee_permission.permission_project_reporting_reject",
		paramKey: "employee_permission",
	},
	"Attendance Regularization": {
		approve: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_approve",
		reject: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_secondary_reject",
		primaryReject: "hrms.hr.doctype.attendance_regularization.attendance_regularization.regularization_project_reporting_reject",
		paramKey: "attendance_regularization",
	},
}

function handleSecondaryAction(action) {
	const apiConfig = secondaryApiMap[props.modelValue.doctype] || secondaryApiMap["Leave Application"]
	const method = action === "approve" ? apiConfig.approve : apiConfig.reject

	let params = { [apiConfig.paramKey]: props.modelValue.name }
	if (action === "reject") {
		if (!rejectReason.value?.trim()) return
		params.reason = rejectReason.value.trim()
	}

	createResource({
		url: method,
		params: params,
		auto: true,
		onSuccess(data) {
			modalController.dismiss()
			toast({
				title: __("Success"),
				text: data.message,
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: action === "approve" ? "text-green-500" : "text-red-500",
			})
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

	const apiConfig = secondaryApiMap[props.modelValue.doctype] || secondaryApiMap["Leave Application"]
	createResource({
		url: apiConfig.primaryReject,
		params: {
			[apiConfig.paramKey]: props.modelValue.name,
			reason: primaryRejectReason.value.trim(),
		},
		auto: true,
		onSuccess(data) {
			modalController.dismiss()
			toast({
				title: __("Success"),
				text: data.message,
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
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

const openFormView = () => {
	modalController.dismiss()
	router.push({
		name: `${props.modelValue.doctype.replace(/\s+/g, "")}DetailView`,
		params: { id: props.modelValue.name },
	})
}

onMounted(() => {
	workflow.value = useWorkflow(props.modelValue.doctype)
})
</script>

<style scoped>
ion-modal {
	--height: 100%;
}
</style>
