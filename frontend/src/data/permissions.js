import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

import dayjs from "@/utils/dayjs"

const transformPermissions = (data) => {
	return data.map((perm) => {
		perm.doctype = "Employee Permission"
		perm.permission_display_date = dayjs(perm.permission_date).format("D MMM")
		perm.time_range = formatTimeRange(perm.from_time, perm.to_time)
		return perm
	})
}

export const formatTimeRange = (from_time, to_time) => {
	if (!from_time || !to_time) return ""
	const fmt = (t) => t.split(":").slice(0, 2).join(":")
	return `${fmt(from_time)} - ${fmt(to_time)}`
}

export const myPermissions = createResource({
	url: "hrms.api.get_employee_permissions",
	params: {
		employee: employeeResource.data.name,
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_permissions",
	transform(data) {
		return transformPermissions(data)
	},
})

export const teamPermissions = createResource({
	url: "hrms.api.get_employee_permissions",
	params: {
		employee: employeeResource.data.name,
		approver_id: employeeResource.data.user_id,
		for_approval: 1,
		limit: 10,
	},
	auto: true,
	cache: "hrms:team_permissions",
	transform(data) {
		return transformPermissions(data)
	},
})
