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
				@validateForm="validateForm"
			/>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const today = dayjs().format("YYYY-MM-DD")

const props = defineProps({
	id: { type: String, required: false },
})

const sessionEmployee = inject("$employee")
const compRequest = ref({})

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Compensatory Leave Request" },
	transform(data) {
		const excludeFields = [
			"naming_series",
			"leave_allocation",
			"column_break_8",
		]
		const employeeFields = ["employee", "employee_name", "department", "company", "status"]
		if (!props.id) excludeFields.push(...employeeFields)

		let fields = data.filter((f) => !excludeFields.includes(f.fieldname))

		// default leave type to Compensatory Off
		const leaveTypeField = fields.find((f) => f.fieldname === "leave_type")
		if (leaveTypeField && !props.id) {
			leaveTypeField.default = "Compensatory Off"
			leaveTypeField.read_only = 1
		}

		// default work_from_date and work_end_date to today
		const fromField = fields.find((f) => f.fieldname === "work_from_date")
		if (fromField && !props.id) fromField.default = today

		const toField = fields.find((f) => f.fieldname === "work_end_date")
		if (toField && !props.id) toField.default = today

		// hide half_day_date initially
		const halfDayDate = fields.find((f) => f.fieldname === "half_day_date")
		if (halfDayDate) halfDayDate.hidden = !compRequest.value.half_day

		return fields
	},
})
formFields.reload()

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
			formFields.data?.forEach((field) => (field.read_only = true))
		}
	}
)

function validateForm() {
	compRequest.value.employee = sessionEmployee.data.name
	if (!compRequest.value.leave_type) {
		compRequest.value.leave_type = "Compensatory Off"
	}
}
</script>
