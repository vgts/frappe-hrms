<template>
	<!-- Desktop sidebar — visible only on lg+ -->
	<aside
		class="hidden lg:flex flex-col fixed top-0 left-0 h-full w-56 bg-white border-r border-gray-100 shadow-sm z-50"
	>
		<!-- Brand -->
		<div class="flex items-center gap-2 px-5 py-5 border-b border-gray-100">
			<VGTSLogo class="h-6 w-auto text-gray-800" />
			<span class="text-base font-bold text-gray-900">VGTS-HRMS</span>
		</div>

		<!-- Search button -->
		<div class="px-3 pt-4 pb-1">
			<button
				@click="showSearch = true"
				class="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-gray-500 bg-gray-50 hover:bg-gray-100 border border-gray-200 transition-colors"
			>
				<FeatherIcon name="search" class="h-4 w-4 text-gray-400 shrink-0" />
				<span class="text-gray-400">{{ __("Search employee…") }}</span>
			</button>
		</div>

		<!-- Navigation links -->
		<nav class="flex flex-col gap-0.5 px-3 pt-2">
			<router-link
				v-for="item in navItems"
				:key="item.route"
				:to="item.route"
				class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
				:class="isActive(item.route)
					? 'bg-blue-50 text-blue-700'
					: 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'"
			>
				<component :is="item.icon" class="h-4 w-4 shrink-0" />
				{{ item.label }}
			</router-link>
		</nav>

		<!-- Divider -->
		<div class="mx-4 my-4 border-t border-gray-100"></div>

		<!-- Quick Links -->
		<div class="flex flex-col px-3 gap-0.5">
			<div class="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
				{{ __("Quick Links") }}
			</div>
			<button
				v-for="link in quickLinks"
				:key="link.route"
				@click="openForm(link.route)"
				class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors text-left"
			>
				<component :is="link.icon" class="h-4 w-4 shrink-0 text-gray-400" />
				{{ link.title }}
			</button>
		</div>

		<!-- Employee Search Modal -->
		<EmployeeSearchModal v-model="showSearch" />

		<!-- Bottom: user + notifications -->
		<div class="mt-auto border-t border-gray-100 px-4 py-4 flex items-center justify-between">
			<router-link :to="{ name: 'Profile' }" class="flex items-center gap-2 min-w-0">
				<Avatar :image="user.data?.user_image" :label="user.data?.first_name" size="md" />
				<span class="text-sm font-medium text-gray-700 truncate">{{ user.data?.first_name }}</span>
			</router-link>
			<div class="flex items-center gap-2">
				<router-link :to="{ name: 'Notifications' }" class="relative">
					<FeatherIcon name="bell" class="h-4 w-4 text-gray-400" />
					<span
						v-if="unreadNotificationsCount.data"
						class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-red-500 rounded-full"
					></span>
				</router-link>
			</div>
		</div>
	</aside>
</template>

<script setup>
import { inject, markRaw, ref } from "vue"
import { useRoute } from "vue-router"
import { FeatherIcon, Avatar } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"
import { useFormModal } from "@/composables/useFormModal"
import VGTSLogo from "@/components/icons/FrappeHRLogo.vue"
import HomeIcon from "@/components/icons/HomeIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ApprovalsIcon from "@/components/icons/ApprovalsIcon.vue"
import EmployeeSearchModal from "@/components/EmployeeSearchModal.vue"

const __ = inject("$translate")
const user = inject("$user")
const route = useRoute()
const { openForm } = useFormModal()

const showSearch = ref(false)

const navItems = [
	{ icon: markRaw(HomeIcon),       label: __("Home"),       route: "/home" },
	{ icon: markRaw(AttendanceIcon), label: __("Attendance"), route: "/dashboard/attendance" },
	{ icon: markRaw(LeaveIcon),      label: __("Leaves"),     route: "/dashboard/leaves" },
	{ icon: markRaw(ExpenseIcon),    label: __("Expenses"),   route: "/dashboard/expense-claims" },
	{ icon: markRaw(ApprovalsIcon),  label: __("Approvals"),  route: "/approvals" },
]

const quickLinks = [
	{ icon: markRaw(AttendanceIcon), title: __("Request Attendance"),  route: "AttendanceRequestFormView" },
	{ icon: markRaw(LeaveIcon),      title: __("Request Leave"),        route: "LeaveApplicationFormView" },
	{ icon: markRaw(AttendanceIcon), title: __("Request Shift"),        route: "ShiftRequestFormView" },
	{ icon: markRaw(ExpenseIcon),    title: __("Claim Expense"),        route: "ExpenseClaimFormView" },
	{ icon: markRaw(AttendanceIcon), title: __("Request Permission"),   route: "PermissionFormView" },
	{ icon: markRaw(AttendanceIcon), title: __("Regularization"),       route: "RegularizationFormView" },
	{ icon: markRaw(LeaveIcon),      title: __("Compensatory Request"), route: "CompensatoryLeaveFormView" },
]

function isActive(path) {
	return route.path === path || route.path.startsWith(path + "/")
}
</script>
