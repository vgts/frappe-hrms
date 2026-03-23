<template>
	<ion-page>
		<ListView
			doctype="Attendance Regularization"
			:pageTitle="__('Regularization')"
			:tabButtons="TAB_BUTTONS"
			:fields="FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"

const __ = inject("$translate")
const TAB_BUTTONS = ["My Requests", "Team Requests"]
const FIELDS = [
	"name",
	"employee",
	"employee_name",
	"attendance_date",
	"reason",
	"checkin_time",
	"checkout_time",
	"total_hours",
	"status",
	"custom_approval_stage",
	"custom_secondary_leave_approver",
	"custom_secondary_approver_name",
]
const STATUS_FILTER_OPTIONS = ["Open", "Approved", "Rejected"]
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: STATUS_FILTER_OPTIONS,
	},
	{
		fieldname: "reason",
		fieldtype: "Select",
		label: __("Reason"),
		options: ["Forgot to Check-in", "Forgot to Check-out", "Forgot Both", "Incorrect Entry"],
	},
	{
		fieldname: "employee",
		fieldtype: "Link",
		label: __("Employee"),
		options: "Employee",
	},
	{ fieldname: "attendance_date", fieldtype: "Date", label: __("Date") },
]
</script>
