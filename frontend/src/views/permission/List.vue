<template>
	<ion-page>
		<ListView
			doctype="Employee Permission"
			:pageTitle="__('Permission History')"
			:tabButtons="TAB_BUTTONS"
			:fields="PERMISSION_FIELDS"
			:filterConfig="FILTER_CONFIG"
		>
			<template #aboveList="{ isTeamRequest }">
				<PermissionBalanceBanner
					v-if="!isTeamRequest"
					:balance="permissionBalance.data"
				/>
			</template>
		</ListView>
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import ListView from "@/components/ListView.vue"
import PermissionBalanceBanner from "@/components/PermissionBalanceBanner.vue"
import { inject } from "vue"
import { permissionBalance } from "@/data/permissions"

const __ = inject("$translate")
const TAB_BUTTONS = ["My Permissions", "Team Permissions"] // __("My Permissions"), __("Team Permissions")
const PERMISSION_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"permission_date",
	"from_time",
	"to_time",
	"duration",
	"reason",
	"status",
	"custom_approval_stage",
	"custom_secondary_leave_approver",
	"custom_secondary_approver_name",
]
const STATUS_FILTER_OPTIONS = ["Open", "Approved", "Rejected"] // __("Open"), __("Approved"), __("Rejected")
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: STATUS_FILTER_OPTIONS,
	},
	{
		fieldname: "employee",
		fieldtype: "Link",
		label: __("Employee"),
		options: "Employee",
	},
	{
		fieldname: "department",
		fieldtype: "Link",
		label: __("Department"),
		options: "Department",
	},
	{ fieldname: "permission_date", fieldtype: "Date", label: __("Permission Date") },
]
</script>
