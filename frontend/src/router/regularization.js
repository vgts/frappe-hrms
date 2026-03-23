export default [
	{
		path: "/attendance-regularization",
		name: "RegularizationListView",
		component: () => import("@/views/regularization/List.vue"),
	},
	{
		path: "/attendance-regularization/new",
		name: "RegularizationFormView",
		component: () => import("@/views/regularization/Form.vue"),
	},
	{
		path: "/attendance-regularization/:id",
		name: "AttendanceRegularizationDetailView",
		props: true,
		component: () => import("@/views/regularization/Form.vue"),
	},
]
