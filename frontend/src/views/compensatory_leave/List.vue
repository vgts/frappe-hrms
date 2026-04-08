<template>
	<ion-page>
		<ListView
			doctype="Compensatory Leave Request"
			:pageTitle="__('Compensatory Off')"
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
	"leave_type",
	"work_from_date",
	"work_end_date",
	"half_day",
	"reason",
	"status",
	"custom_approval_stage",
	"approver",
	"approver_name",
	"custom_secondary_leave_approver",
	"custom_secondary_approver_name",
]
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: ["Open", "Approved", "Rejected"],
	},
	{
		fieldname: "leave_type",
		fieldtype: "Link",
		label: __("Leave Type"),
		options: "Leave Type",
	},
	{ fieldname: "work_from_date", fieldtype: "Date", label: __("From Date") },
	{ fieldname: "work_end_date", fieldtype: "Date", label: __("To Date") },
]
</script>
