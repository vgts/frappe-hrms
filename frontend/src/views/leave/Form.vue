<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Leave Application"
				v-model="leaveApplication"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:showFormButton="!showSecondaryActions"
				@validateForm="validateForm"
			>
				<!-- Secondary approval buttons slot -->
				<template #formButton v-if="showSecondaryActions">
					<div class="flex flex-col gap-3 w-full">
						<!-- Approval Stage Tracker -->
						<ApprovalStageTracker
							v-if="approvalDetails?.data && leaveApplication.custom_secondary_leave_approver"
							:doc="leaveApplication"
							:approvalDetails="approvalDetails"
						/>

						<!-- Waiting message for non-secondary users -->
						<div
							v-if="isPendingSecondaryByOther"
							class="text-center text-sm font-medium text-blue-700 bg-blue-50 rounded-lg p-3"
						>
							{{ __("Forwarded to {0} for secondary approval", [leaveApplication.custom_secondary_approver_name || leaveApplication.custom_secondary_leave_approver]) }}
						</div>

						<!-- Secondary approver buttons -->
						<template v-if="isSecondaryApproverPending">
							<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
								{{ __("Waiting for your approval") }}
							</div>
							<div class="flex flex-row gap-3">
								<Button
									@click="handleSecondaryAction('reject')"
									class="w-full py-5"
									variant="subtle"
									theme="red"
								>
									{{ __("Reject") }}
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

const dayjs = inject("$dayjs")
const __ = inject("$translate")
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

// reactive object to store form data
const leaveApplication = ref({})

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Leave Application" },
	transform(data) {
		let fields = getFilteredFields(data)

		return fields.map((field) => {
			if (field.fieldname === "half_day_date") field.hidden = true

			if (field.fieldname === "posting_date") field.default = today

			return field
		})
	},
	onSuccess(_data) {
		leaveApprovalDetails.reload()
		leaveTypes.reload()
	},
})
formFields.reload()

const leaveApprovalDetails = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: currEmployee.value },
	onSuccess(data) {
		setLeaveApprovers(data)
	},
})

const leaveTypes = createResource({
	url: "hrms.api.get_leave_types",
	params: {
		employee: currEmployee.value,
		date: today,
	},
	onSuccess(data) {
		setLeaveTypes(data)
	},
})

// Fetch secondary approval details for existing docs
const approvalDetails = createResource({
	url: "hrms.hr.doctype.leave_application.leave_application.get_secondary_approval_details",
	params: { leave_application: props.id },
	auto: !!props.id,
})

// Two-level approval computed
const isSecondaryApproverPending = computed(() => {
	return (
		leaveApplication.value.custom_approval_stage === "Pending Secondary Approver" &&
		sessionEmployee.data?.user_id === leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.docstatus === 0
	)
})

const isPendingSecondaryByOther = computed(() => {
	return (
		leaveApplication.value.custom_approval_stage === "Pending Secondary Approver" &&
		sessionEmployee.data?.user_id !== leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.docstatus === 0 &&
		leaveApplication.value.custom_secondary_leave_approver
	)
})

const showSecondaryActions = computed(() => {
	return (
		props.id &&
		leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.custom_approval_stage === "Pending Secondary Approver" &&
		leaveApplication.value.docstatus === 0
	)
})

function handleSecondaryAction(action) {
	const method = action === "approve"
		? "hrms.hr.doctype.leave_application.leave_application.secondary_approve"
		: "hrms.hr.doctype.leave_application.leave_application.secondary_reject"

	createResource({
		url: method,
		params: { leave_application: props.id },
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

// form scripts
watch(
	() => leaveApplication.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== currEmployee.value) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
		currEmployee.value = employee_id
		leaveTypes.fetch({ employee: currEmployee.value, date: today })
		leaveApprovalDetails.fetch({ employee: currEmployee.value })
	}
)
watch(
	() => leaveApplication.value.leave_type,
	(leave_type) => setLeaveBalance(leave_type)
)

watch(
	() => leaveApplication.value.half_day,
	(half_day) => setHalfDayDate(half_day)
)

watch(
	() => leaveApplication.value.half_day && leaveApplication.value.half_day_date,
	() => setTotalLeaveDays()
)

watch(
	() => leaveApplication.value.from_date,
	(from_date) => {
		if (!leaveApplication.value.to_date) {
			leaveApplication.value.to_date = from_date
		}

		// fetch leave types for the selected date
		leaveTypes.fetch({
			employee: currEmployee.value,
			date: from_date,
		})
	}
)

watch(
	() => [leaveApplication.value.from_date, leaveApplication.value.to_date],
	([from_date, to_date]) => {
		validateDates(from_date, to_date)
		setHalfDayDateRange()
		setTotalLeaveDays()
	}
)


// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// ex: employee and other details can be fetched from the session user
	const excludeFields = [
		"naming_series",
		"sb_other_details",
		"salary_slip",
		"letter_head",
		// Hide secondary approval fields from the form (shown in tracker instead)
		"custom_secondary_approval_section",
		"custom_secondary_leave_approver",
		"custom_secondary_approver_name",
		"custom_column_break_secondary",
		"custom_approval_stage",
	]

	const employeeFields = [
		"employee",
		"employee_name",
		"department",
		"company",
		"follow_via_email",
		"status",
		"posting_date",
	]

	if (!props.id) excludeFields.push(...employeeFields)

	return fields.filter((field) => !excludeFields.includes(field.fieldname))
}

function setFormReadOnly() {
	if (leaveApplication.value.leave_approver === sessionEmployee.data.user_id) return
	if (leaveApplication.value.custom_secondary_leave_approver === sessionEmployee.data.user_id) return
	formFields.data.map((field) => (field.read_only = true))
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return

	const error_message =
		from_date > to_date ? __("To Date cannot be before From Date") : ""

	const from_date_field = formFields.data.find(
		(field) => field.fieldname === "from_date"
	)
	from_date_field.error_message = error_message
}

function setTotalLeaveDays() {
	if (!areValuesSet()) return

	const leaveDays = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
		params: {
			employee: currEmployee.value,
			leave_type: leaveApplication.value.leave_type,
			from_date: leaveApplication.value.from_date,
			to_date: leaveApplication.value.to_date,
			half_day: leaveApplication.value.half_day,
			half_day_date: leaveApplication.value.half_day_date,
		},
		onSuccess(data) {
			leaveApplication.value.total_leave_days = data
		},
	})
	leaveDays.reload()
	setLeaveBalance()
}

function setLeaveBalance() {
	if (!areValuesSet()) return

	const leaveBalance = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
		params: {
			employee: currEmployee.value,
			date: leaveApplication.value.from_date,
			to_date: leaveApplication.value.to_date,
			leave_type: leaveApplication.value.leave_type,
			consider_all_leaves_in_the_allocation_period: 1,
		},
		onSuccess(data) {
			leaveApplication.value.leave_balance = data
		},
	})
	leaveBalance.reload()
}

function setHalfDayDate(half_day) {
	const half_day_date = formFields.data.find(
		(field) => field.fieldname === "half_day_date"
	)
	half_day_date.hidden = !half_day
	half_day_date.reqd = half_day

	if (!half_day) return

	if (leaveApplication.value.from_date === leaveApplication.value.to_date) {
		leaveApplication.value.half_day_date = leaveApplication.value.from_date
	} else {
		setHalfDayDateRange()
	}
}

function setHalfDayDateRange() {
	const half_day_date = formFields.data.find(
		(field) => field.fieldname === "half_day_date"
	)
	half_day_date.minDate = leaveApplication.value.from_date
	half_day_date.maxDate = leaveApplication.value.to_date
}

function setLeaveApprovers(data) {
	const leave_approver = formFields.data?.find(
		(field) => field.fieldname === "leave_approver"
	)
	leave_approver.reqd = data?.is_mandatory
	leave_approver.documentList = data?.department_approvers.map((approver) => ({
		label: approver.full_name
			? `${approver.name} : ${approver.full_name}`
			: approver.name,
		value: approver.name,
	}))
	if (!leaveApplication.value.leave_approver){
		leaveApplication.value.leave_approver = data?.leave_approver
		leaveApplication.value.leave_approver_name = data?.leave_approver_name
	}

}

function setLeaveTypes(data) {
	const leave_type = formFields.data.find(
		(field) => field.fieldname === "leave_type"
	)
	leave_type.documentList = data?.map((leave_type) => ({
		label: leave_type,
		value: leave_type,
	}))
}

function areValuesSet() {
	return (
		leaveApplication.value.from_date &&
		leaveApplication.value.to_date &&
		leaveApplication.value.leave_type
	)
}

function validateForm() {
	setHalfDayDate(leaveApplication.value.half_day)
	leaveApplication.value.employee = currEmployee.value
}
</script>
