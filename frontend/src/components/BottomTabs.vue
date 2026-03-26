<template>
	<ion-tab-bar
		slot="bottom"
		class="shadow-md py-2 pb-2 standalone:pb-safe-bottom transition-colors duration-200"
		:class="isDark() ? 'bg-gray-800 border-t border-gray-700' : 'bg-white'"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.title"
			:tab="item.title"
			:href="item.route"
			:class="[
				'text-xs space-y-1.5 transition active:scale-95',
				isDark() ? 'bg-gray-800' : 'bg-white',
				route.path === item.route
					? isDark() ? 'text-gray-50 font-semibold' : 'border-gray-900 text-gray-800 font-semibold'
					: isDark() ? 'text-gray-400 font-normal' : 'text-gray-600 font-normal',
			]"
		>
			<component :is="item.icon" class="h-5 w-5" />
			<div>{{ item.title }}</div>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import { inject } from "vue"
import { useTheme } from "@/composables/useTheme"

const __ = inject("$translate")
const route = useRoute()
const { isDark } = useTheme()

const tabItems = [
	{
		icon: HomeIcon,
		title: __("Home"),
		route: "/home",
	},
	{
		icon: AttendanceIcon,
		title: __("Attendance"),
		route: "/dashboard/attendance",
	},
	{
		icon: LeaveIcon,
		title: __("Leaves"),
		route: "/dashboard/leaves",
	},
	{
		icon: ExpenseIcon,
		title: __("Expenses"),
		route: "/dashboard/expense-claims",
	},
]
</script>
