import { ref, defineAsyncComponent, shallowRef } from "vue"

const isOpen = ref(false)
const activeComponent = shallowRef(null)
const modalTitle = ref("")

const formComponentMap = {
	AttendanceRequestFormView: defineAsyncComponent(() => import("@/views/attendance/AttendanceRequestForm.vue")),
	LeaveApplicationFormView: defineAsyncComponent(() => import("@/views/leave/Form.vue")),
	ShiftRequestFormView: defineAsyncComponent(() => import("@/views/attendance/ShiftRequestForm.vue")),
	ExpenseClaimFormView: defineAsyncComponent(() => import("@/views/expense_claim/Form.vue")),
	PermissionFormView: defineAsyncComponent(() => import("@/views/permission/Form.vue")),
	RegularizationFormView: defineAsyncComponent(() => import("@/views/regularization/Form.vue")),
}

export function useFormModal() {
	function openForm(routeName) {
		const comp = formComponentMap[routeName]
		if (comp) {
			activeComponent.value = comp
			isOpen.value = true
		}
	}

	function closeForm() {
		isOpen.value = false
		activeComponent.value = null
		modalTitle.value = ""
	}

	return { isOpen, activeComponent, modalTitle, openForm, closeForm }
}
