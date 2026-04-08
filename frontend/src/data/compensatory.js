import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

import dayjs from "@/utils/dayjs"

const transformCompensatory = (data) => {
	return data.map((req) => {
		req.doctype = "Compensatory Leave Request"
		req.display_date =
			req.work_from_date === req.work_end_date
				? dayjs(req.work_from_date).format("D MMM")
				: dayjs(req.work_from_date).format("D MMM") + " – " + dayjs(req.work_end_date).format("D MMM")
		return req
	})
}

export const myCompensatoryRequests = createResource({
	url: "hrms.api.get_compensatory_requests",
	params: {
		employee: employeeResource.data.name,
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_compensatory_requests",
	transform(data) {
		return transformCompensatory(data)
	},
})

export const teamCompensatoryRequests = createResource({
	url: "hrms.api.get_compensatory_requests",
	params: {
		employee: employeeResource.data.name,
		approver_id: employeeResource.data.user_id,
		for_approval: 1,
		limit: 10,
	},
	auto: true,
	cache: "hrms:team_compensatory_requests",
	transform(data) {
		return transformCompensatory(data)
	},
})
