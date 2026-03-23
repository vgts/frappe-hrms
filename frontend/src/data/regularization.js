import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

import dayjs from "@/utils/dayjs"

const transformRegularizations = (data) => {
	return data.map((reg) => {
		reg.doctype = "Attendance Regularization"
		reg.display_date = dayjs(reg.attendance_date).format("D MMM")
		return reg
	})
}

export const myRegularizations = createResource({
	url: "hrms.api.get_attendance_regularizations",
	params: {
		employee: employeeResource.data.name,
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_regularizations",
	transform(data) {
		return transformRegularizations(data)
	},
})

export const teamRegularizations = createResource({
	url: "hrms.api.get_attendance_regularizations",
	params: {
		employee: employeeResource.data.name,
		approver_id: employeeResource.data.user_id,
		for_approval: 1,
		limit: 10,
	},
	auto: true,
	cache: "hrms:team_regularizations",
	transform(data) {
		return transformRegularizations(data)
	},
})
