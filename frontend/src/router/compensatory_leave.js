export default [
	{
		path: "/compensatory-leave",
		name: "CompensatoryLeaveListView",
		component: () => import("@/views/compensatory_leave/List.vue"),
	},
	{
		path: "/compensatory-leave/new",
		name: "CompensatoryLeaveFormView",
		component: () => import("@/views/compensatory_leave/Form.vue"),
	},
	{
		path: "/compensatory-leave/:id",
		name: "CompensatoryLeaveDetailView",
		props: true,
		component: () => import("@/views/compensatory_leave/Form.vue"),
	},
	// Alias so FormView's auto-generated route name also works
	{
		path: "/compensatory-leave-request/:id",
		name: "CompensatoryLeaveRequestDetailView",
		props: true,
		component: () => import("@/views/compensatory_leave/Form.vue"),
	},
]
