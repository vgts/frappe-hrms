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
				:requireAttachment="isSickLeave"
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

						<!-- Project Reporting (Primary) approver buttons -->
						<template v-if="isProjectReportingPending">
							<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
								{{ __("Waiting for your approval") }}
							</div>
							<!-- Rejection reason input -->
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
							{{ __("Forwarded to {0} for secondary approval", [leaveApplication.custom_secondary_approver_name || leaveApplication.custom_secondary_leave_approver]) }}
						</div>

						<!-- Secondary approver buttons -->
						<template v-else-if="isSecondaryApproverPending">
							<div class="text-center text-sm font-medium text-yellow-700 bg-yellow-50 rounded-lg p-2 mb-1">
								{{ __("Waiting for your approval") }}
							</div>
							<div class="flex flex-row gap-3">
								<!-- Rejection reason input -->
								<div v-if="showRejectReason" class="w-full mb-2">
									<label class="text-sm text-gray-600 mb-1 block">{{ __("Reason for Rejection") }} *</label>
									<textarea
										v-model="rejectReason"
										class="w-full border rounded-lg p-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-red-300"
										:placeholder="__('Enter reason for rejection...')"
									></textarea>
								</div>
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
import { isDocumentOwner, isApprovalOwnerContextReady } from "@/utils/twoLevelApproval.js"

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

const isSickLeave = computed(
	() => leaveApplication.value.leave_type === "Sick Leave" && parseFloat(leaveApplication.value.total_leave_days || 0) > 2
)

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

// Two-level approval computed (aligned with Regularization / Permission — server `is_owner` in approval details)
const employeeDocLoaded = computed(
	() => !!props.id && !!leaveApplication.value?.employee
)
const ownerContextReady = computed(() =>
	isApprovalOwnerContextReady(sessionEmployee, approvalDetails, leaveApplication.value?.employee)
)
const isCurrentUserEmployee = computed(
	() =>
		employeeDocLoaded.value &&
		isDocumentOwner(sessionEmployee, approvalDetails, leaveApplication.value?.employee)
)

const isSecondaryApproverPending = computed(() => {
	return (
		employeeDocLoaded.value &&
		ownerContextReady.value &&
		!isCurrentUserEmployee.value &&
		leaveApplication.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id === leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.docstatus === 0
	)
})

const isPendingSecondaryByOther = computed(() => {
	return (
		employeeDocLoaded.value &&
		ownerContextReady.value &&
		leaveApplication.value.custom_approval_stage === "Pending Secondary Reporting Approval" &&
		sessionEmployee.data?.user_id !== leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.docstatus === 0 &&
		leaveApplication.value.custom_secondary_leave_approver
	)
})

const isProjectReportingPending = computed(() => {
	return (
		employeeDocLoaded.value &&
		ownerContextReady.value &&
		!isCurrentUserEmployee.value &&
		props.id &&
		leaveApplication.value.custom_secondary_leave_approver &&
		leaveApplication.value.custom_approval_stage === "Pending Project Reporting Approval" &&
		leaveApplication.value.status === "Open" &&
		leaveApplication.value.docstatus === 0 &&
		sessionEmployee.data?.user_id === leaveApplication.value.leave_approver
	)
})

const showSecondaryActions = computed(() => {
	return (
		props.id &&
		employeeDocLoaded.value &&
		ownerContextReady.value &&
		leaveApplication.value.custom_secondary_leave_approver &&
		(leaveApplication.value.custom_approval_stage === "Pending Secondary Reporting Approval" ||
			isProjectReportingPending.value) &&
		leaveApplication.value.docstatus === 0
	)
})

const showRejectReason = ref(false)
const rejectReason = ref("")
const showPrimaryRejectReason = ref(false)
const primaryRejectReason = ref("")

function handleSecondaryAction(action) {
	if (isCurrentUserEmployee.value) return
	const method = action === "approve"
		? "hrms.hr.doctype.leave_application.leave_application.secondary_approve"
		: "hrms.hr.doctype.leave_application.leave_application.secondary_reject"

	let params = { leave_application: props.id }
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
	if (isCurrentUserEmployee.value) return
	if (!primaryRejectReason.value?.trim()) return

	createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.project_reporting_reject",
		params: {
			leave_application: props.id,
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
	if (isCurrentUserEmployee.value) return
	createResource({
		url: "frappe.client.set_value",
		params: {
			doctype: "Leave Application",
			name: props.id,
			fieldname: "status",
			value: "Approved",
		},
		auto: true,
		onSuccess() {
			toast({
				title: __("Success"),
				text: __("Leave Application approved and forwarded for secondary approval."),
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
// Reactively hide/show approval section based on whether approver is set
watch(
	() => leaveApplication.value.leave_approver,
	(approver) => {
		if (!formFields.data) return
		const approvalFields = ["section_break_7", "leave_approver", "leave_approver_name", "column_break_18"]
		const hasApprover = !!approver || !!leaveApplication.value.custom_secondary_leave_approver
		formFields.data.forEach((field) => {
			if (approvalFields.includes(field.fieldname)) {
				field.hidden = !hasApprover
			}
		})
	},
	{ immediate: true }
)

watch(
	() => leaveApplication.value.leave_type,
	(leave_type) => {
		setLeaveBalance(leave_type)
		// Auto-calculate To Date when Paternity Leave is selected
		if (leave_type === "Paternity Leave" && leaveApplication.value.from_date) {
			setPaternityToDate()
		}
	}
)

watch(
	() => leaveApplication.value.half_day,
	(half_day) => {
		syncHalfDaySession("half_day")
		setHalfDayDate(half_day)
	}
)

watch(
	() => leaveApplication.value.custom_first_half,
	() => {
		syncHalfDaySession("custom_first_half")
	}
)

watch(
	() => leaveApplication.value.custom_second_half,
	() => {
		syncHalfDaySession("custom_second_half")
	}
)

watch(
	() => leaveApplication.value.half_day && leaveApplication.value.half_day_date,
	() => setTotalLeaveDays()
)

watch(
	() => leaveApplication.value.from_date,
	(from_date) => {
		if (leaveApplication.value.leave_type === "Paternity Leave") {
			// Always auto-calculate To Date = From Date + 7 working days
			if (from_date) setPaternityToDate()
		} else if (!leaveApplication.value.to_date) {
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
	const userId = sessionEmployee.data.user_id
	const isApprover = userId === leaveApplication.value.leave_approver ||
		userId === leaveApplication.value.custom_secondary_leave_approver

	if (isApprover) {
		// Approvers can only change status — lock all content fields
		const contentFields = [
			"leave_type", "from_date", "to_date", "half_day", "half_day_date",
			"description", "total_leave_days", "leave_balance", "posting_date",
		]
		formFields.data.forEach((field) => {
			if (contentFields.includes(field.fieldname)) {
				field.read_only = true
			}
		})
	} else {
		// Not the employee and not an approver — full read-only
		formFields.data.forEach((field) => (field.read_only = true))
	}
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

const MONTHLY_OFF_TYPE = "Monthly Off"

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
			// Monthly Off with no balance → warn, will be applied as LWP
			if (
				leaveApplication.value.leave_type === MONTHLY_OFF_TYPE &&
				(!data || data <= 0)
			) {
				toast({
					title: __("No Monthly Off Balance"),
					text: __(
						"No balance available. Leave will be applied as Leave Without Pay (LWP) and shown in attendance sheet accordingly."
					),
					icon: "alert-triangle",
					position: "bottom-center",
					iconClasses: "text-yellow-500",
				})
			}
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

function syncHalfDaySession(changedField = "") {
	if (leaveApplication.value.__syncing_half_day_session) return
	leaveApplication.value.__syncing_half_day_session = true

	try {
		// When a custom session checkbox is explicitly enabled, auto-enable half_day
		// so the user doesn't need to tick the main half_day field separately
		if (
			(changedField === "custom_first_half" && leaveApplication.value.custom_first_half) ||
			(changedField === "custom_second_half" && leaveApplication.value.custom_second_half)
		) {
			leaveApplication.value.half_day = 1
			// Ensure half_day_date is set immediately so total_leave_days → 0.5
			if (leaveApplication.value.from_date) {
				leaveApplication.value.half_day_date = leaveApplication.value.from_date
			}
		}

		const halfDayEnabled = !!leaveApplication.value.half_day
		const hasFirst = !!leaveApplication.value.custom_first_half
		const hasSecond = !!leaveApplication.value.custom_second_half

		if (!halfDayEnabled) {
			if (hasFirst) leaveApplication.value.custom_first_half = 0
			if (hasSecond) leaveApplication.value.custom_second_half = 0
			return
		}

		// Mutual exclusion: only one session can be selected at a time
		if (hasFirst && hasSecond) {
			if (changedField === "custom_second_half") {
				leaveApplication.value.custom_first_half = 0
			} else {
				leaveApplication.value.custom_second_half = 0
			}
		}

		// Default to first half when half_day is enabled but no session chosen yet
		if (!leaveApplication.value.custom_first_half && !leaveApplication.value.custom_second_half) {
			leaveApplication.value.custom_first_half = 1
		}
	} finally {
		leaveApplication.value.__syncing_half_day_session = false
	}
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
	if (!leaveApplication.value.custom_secondary_leave_approver && data?.secondary_leave_approver) {
		leaveApplication.value.custom_secondary_leave_approver = data.secondary_leave_approver
		leaveApplication.value.custom_secondary_approver_name = data.secondary_approver_name
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

// ── Paternity Leave: auto-set To Date = From Date + 7 working days ──────────
// Weekends (Sat/Sun) and public holidays are NOT counted.
function setPaternityToDate() {
	if (!leaveApplication.value.from_date || !currEmployee.value) return

	// Step 1: get the employee's holiday list
	const empRes = createResource({
		url: "frappe.client.get_value",
		params: {
			doctype: "Employee",
			fieldname: "holiday_list",
			filters: { name: currEmployee.value },
		},
		onSuccess(empData) {
			const holidayList = empData?.holiday_list || ""
			if (!holidayList) {
				// No holiday list — count Mon–Fri only
				leaveApplication.value.to_date = _nthWorkingDay(
					leaveApplication.value.from_date, 7, new Set()
				)
				return
			}

			// Step 2: fetch non-weekly-off holidays from the list
			const holRes = createResource({
				url: "frappe.client.get_list",
				params: {
					doctype: "Holiday",
					parent: holidayList,
					filters: [
						["holiday_date", ">=", leaveApplication.value.from_date],
						["weekly_off", "=", 0],
					],
					fields: ["holiday_date"],
					limit: 200,
				},
				onSuccess(holidays) {
					const holidaySet = new Set((holidays || []).map(h => h.holiday_date))
					leaveApplication.value.to_date = _nthWorkingDay(
						leaveApplication.value.from_date, 7, holidaySet
					)
				},
			})
			holRes.reload()
		},
	})
	empRes.reload()
}

// Return the date string of the n-th working day counting from startDateStr.
// Skips Saturday (6), Sunday (0), and any date in holidaySet.
function _nthWorkingDay(startDateStr, n, holidaySet) {
	let date  = dayjs(startDateStr)
	let count = 0
	while (count < n) {
		const day     = date.day()                       // 0=Sun … 6=Sat
		const dateStr = date.format("YYYY-MM-DD")
		if (day !== 0 && day !== 6 && !holidaySet.has(dateStr)) {
			count++
		}
		if (count < n) date = date.add(1, "day")
	}
	return date.format("YYYY-MM-DD")
}

function validateForm() {
	syncHalfDaySession("validate")
	setHalfDayDate(leaveApplication.value.half_day)
	leaveApplication.value.employee = currEmployee.value
}
</script>
