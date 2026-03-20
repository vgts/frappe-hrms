export default [
	{
		path: "/employee-permissions",
		name: "PermissionListView",
		component: () => import("@/views/permission/List.vue"),
	},
	{
		path: "/employee-permissions/new",
		name: "PermissionFormView",
		component: () => import("@/views/permission/Form.vue"),
	},
	{
		path: "/employee-permissions/:id",
		name: "EmployeePermissionDetailView",
		props: true,
		component: () => import("@/views/permission/Form.vue"),
	},
]
