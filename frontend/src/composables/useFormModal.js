import { ref, defineAsyncComponent, shallowRef } from "vue"

const isOpen = ref(false)
const activeComponent = shallowRef(null)
const modalTitle = ref("")

const formComponentMap = {
	AttendanceRequestFormView: {
		component: defineAsyncComponent(() => import("@/views/attendance/AttendanceRequestForm.vue")),
		title: "Request Attendance",
		icon: "clipboard",
	},
	LeaveApplicationFormView: {
		component: defineAsyncComponent(() => import("@/views/leave/Form.vue")),
		title: "Request Leave",
		icon: "calendar",
	},
	ShiftRequestFormView: {
		component: defineAsyncComponent(() => import("@/views/attendance/ShiftRequestForm.vue")),
		title: "Request Shift",
		icon: "clock",
	},
	ExpenseClaimFormView: {
		component: defineAsyncComponent(() => import("@/views/expense_claim/Form.vue")),
		title: "Claim Expense",
		icon: "credit-card",
	},
	PermissionFormView: {
		component: defineAsyncComponent(() => import("@/views/permission/Form.vue")),
		title: "Request Permission",
		icon: "shield",
	},
	RegularizationFormView: {
		component: defineAsyncComponent(() => import("@/views/regularization/Form.vue")),
		title: "Regularization",
		icon: "check-square",
	},
}

const modalIcon = ref("")

export function useFormModal() {
	function openForm(routeName) {
		const entry = formComponentMap[routeName]
		if (entry) {
			activeComponent.value = entry.component
			modalTitle.value = entry.title
			modalIcon.value = entry.icon
			isOpen.value = true
		}
	}

	function closeForm() {
		isOpen.value = false
		activeComponent.value = null
		modalTitle.value = ""
		modalIcon.value = ""
	}

	return { isOpen, activeComponent, modalTitle, modalIcon, openForm, closeForm }
}
