<template>
	<ion-page>
		<ion-content :scroll-y="true">
			<div class="profile-page">
				<div class="profile-container">

					<!-- Header -->
					<header class="profile-nav">
						<Button
							variant="ghost"
							class="!pl-0 hover:bg-white"
							@click="router.back()"
						>
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="nav-title">{{ __("Profile") }}</h2>
						<div class="w-5"></div>
					</header>

					<!-- Avatar card -->
					<div class="avatar-card">
						<img
							v-if="user.data.user_image"
							class="avatar-img"
							:src="user.data.user_image"
							:alt="user.data.first_name"
						/>
						<div v-else class="avatar-fallback">
							{{ user.data.first_name[0] }}
						</div>

						<span v-if="employee" class="emp-name">{{ employee?.data?.employee_name }}</span>
						<span v-if="employee" class="emp-designation">{{ employee?.data?.designation }}</span>

						<!-- Quick info row -->
						<div class="info-row" v-if="employee?.data">
							<span v-if="employee.data.department" class="info-item">
								<FeatherIcon name="briefcase" class="info-icon" />
								{{ employee.data.department }}
							</span>
							<span v-if="employee.data.employee_number" class="info-item">
								<FeatherIcon name="hash" class="info-icon" />
								{{ employee.data.employee_number }}
							</span>
						</div>

						<!-- Default Present Badge -->
						<div
							v-if="isDefaultPresent"
							class="flex items-center gap-1.5 mt-1 px-3 py-1 rounded-full bg-green-100 border border-green-300"
						>
							<span class="h-2 w-2 rounded-full bg-green-500 flex-shrink-0"></span>
							<span class="text-xs font-semibold text-green-700">
								{{ __("Default Present") }}
							</span>
						</div>
					</div>

					<!-- Profile sections -->
					<div class="sections-list">
						<div
							v-for="link in profileLinks"
							:key="link.title"
							class="section-row"
							@click="openInfoModal(link)"
						>
							<div class="section-left">
								<FeatherIcon :name="link.icon" class="section-icon" />
								<span class="section-label">{{ link.title }}</span>
							</div>
							<FeatherIcon name="chevron-right" class="section-arrow" />
						</div>

						<!-- Settings -->
						<router-link
							v-if="allowPushNotifications"
							:to="{ name: 'Settings' }"
							class="section-row"
						>
							<div class="section-left">
								<FeatherIcon name="settings" class="section-icon" />
								<span class="section-label">{{ __("Settings") }}</span>
							</div>
							<FeatherIcon name="chevron-right" class="section-arrow" />
						</router-link>
					</div>

					<!-- Logout -->
					<Button
						@click="logout"
						variant="outline"
						theme="red"
						class="w-full shadow-sm py-4 mt-6 logout-btn"
					>
						<template #prefix>
							<FeatherIcon name="log-out" class="w-4" />
						</template>
						{{ __("Log Out") }}
					</Button>

					<div class="footer-text">VGTS-HRMS</div>
				</div>
			</div>
		</ion-content>

		<!-- Info modal — direct child of ion-page so Ionic can present it correctly -->
		<ion-modal
			:is-open="isInfoModalOpen"
			@didDismiss="closeInfoModal"
			:initial-breakpoint="1"
			:breakpoints="[0, 1]"
		>
			<ProfileInfoModal
				v-if="selectedItem && employeeDoc.doc"
				:title="selectedItem.title"
				:data="
					selectedItem.fields.map((field) => {
						const [label, fieldtype] = getFieldInfo(field)
						return {
							fieldname: field,
							value: employeeDoc.doc?.[field] ?? null,
							label: label,
							fieldtype: fieldtype,
						}
					})
				"
			/>
		</ion-modal>
	</ion-page>
</template>

<script setup>
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue"
import { useRouter } from "vue-router"
import { IonModal, IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, createDocumentResource, createResource } from "frappe-ui"

import { showErrorAlert } from "@/utils/dialogs"
import { formatCurrency } from "@/utils/formatters"

import ProfileInfoModal from "@/components/ProfileInfoModal.vue"

import { arePushNotificationsEnabled } from "@/data/notifications"

const DOCTYPE = "Employee"

const socket = inject("$socket")
const session = inject("$session")
const user = inject("$user")
const employee = inject("$employee")
const __ = inject("$translate")

const router = useRouter()

const profileLinks = [
	{
		icon: "user",
		title: __("Employee Details"),
		fields: [
			"employee_name",
			"employee_number",
			"gender",
			"date_of_birth",
			"date_of_joining",
			"blood_group",
		],
	},
	{
		icon: "file",
		title: __("Company Information"),
		fields: [
			"company",
			"department",
			"designation",
			"branch",
			"grade",
			"reports_to",
			"employment_type",
		],
	},
	{
		icon: "book",
		title: __("Contact Information"),
		fields: [
			"cell_number",
			"personal_email",
			"company_email",
			"preferred_email",
		],
	},
	{
		icon: "dollar-sign",
		title: __("Salary Information"),
		fields: [
			"ctc",
			"payroll_cost_center",
			"pan_number",
			"provident_fund_account",
			"salary_mode",
			"bank_name",
			"bank_ac_no",
			"ifsc_code",
			"micr_code",
			"iban",
		],
	},
]

const isInfoModalOpen = ref(false)
const selectedItem = ref(null)

const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

// ── Default Present status ────────────────────────────────────────────────
const defaultPresentResource = createResource({
	url: "vgts.default_present.default_present.is_default_present",
	params: { employee: employee.data.name },
	auto: true,
})

const isDefaultPresent = computed(() => !!defaultPresentResource.data)

// ── Profile modal ─────────────────────────────────────────────────────────
const openInfoModal = (request) => {
	selectedItem.value = request
	isInfoModalOpen.value = true
}

const closeInfoModal = () => {
	isInfoModalOpen.value = false
	selectedItem.value = null
}

const employeeDoc = createDocumentResource({
	doctype: DOCTYPE,
	name: employee.data.name,
	fields: "*",
	auto: true,
	transform: (data) => {
		data.ctc = formatCurrency(data.ctc, data.salary_currency)
		return data
	},
})

const employeeDocType = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: DOCTYPE },
	auto: true,
})

const getFieldInfo = (fieldname) => {
	const field = employeeDocType.data?.find(
		(f) => f.fieldname === fieldname
	)
	return [__(field?.label, null, "Employee"), field?.fieldtype]
}

const logout = async () => {
	try {
		await session.logout.submit()
	} catch (e) {
		const msg = "An error occurred while attempting to log out!"
		console.error(msg, e)
		showErrorAlert(msg)
	}
}

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype === DOCTYPE && data.name === employee.data.name) {
			employeeDoc.reload()
			defaultPresentResource.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
})
</script>

<style scoped>
.profile-page {
	min-height: 100%;
	background: #f9fafb;
	padding: 0 16px 40px;
}

.profile-container {
	max-width: 100%;
	margin: 0 auto;
}

@media (min-width: 768px) {
	.profile-container {
		max-width: 520px;
	}
}

/* Nav */
.profile-nav {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 0;
	position: sticky;
	top: 0;
	z-index: 10;
	background: #f9fafb;
}

.nav-title {
	font-size: 1.125rem;
	font-weight: 600;
	color: #111827;
	margin: 0;
}

/* Avatar card */
.avatar-card {
	display: flex;
	flex-direction: column;
	align-items: center;
	background: #ffffff;
	border-radius: 16px;
	border: 1px solid #e5e7eb;
	padding: 24px 16px 20px;
	gap: 4px;
}

.avatar-img {
	height: 80px;
	width: 80px;
	border-radius: 50%;
	object-fit: cover;
	margin-bottom: 8px;
}

.avatar-fallback {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 80px;
	width: 80px;
	border-radius: 50%;
	background: #f3f4f6;
	color: #6b7280;
	font-size: 1.75rem;
	font-weight: 700;
	text-transform: uppercase;
	margin-bottom: 8px;
}

.emp-name {
	font-size: 1.125rem;
	font-weight: 700;
	color: #111827;
}

.emp-designation {
	font-size: 0.8125rem;
	color: #6b7280;
}

.info-row {
	display: flex;
	flex-wrap: wrap;
	gap: 12px;
	margin-top: 8px;
	justify-content: center;
}

.info-item {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 0.75rem;
	color: #9ca3af;
}

.info-icon {
	height: 12px;
	width: 12px;
}

/* Section list */
.sections-list {
	margin-top: 16px;
	background: #ffffff;
	border-radius: 16px;
	border: 1px solid #e5e7eb;
	overflow: hidden;
}

.section-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px;
	cursor: pointer;
	border-bottom: 1px solid #f3f4f6;
	text-decoration: none;
	transition: background 0.1s;
}

.section-row:last-child {
	border-bottom: none;
}

.section-row:active {
	background: #f9fafb;
}

.section-left {
	display: flex;
	align-items: center;
	gap: 12px;
}

.section-icon {
	height: 18px;
	width: 18px;
	color: #9ca3af;
}

.section-label {
	font-size: 0.9375rem;
	font-weight: 500;
	color: #374151;
}

.section-arrow {
	height: 16px;
	width: 16px;
	color: #d1d5db;
}

/* Logout */
.logout-btn {
	border-radius: 12px !important;
}

/* Footer */
.footer-text {
	text-align: center;
	font-size: 0.6875rem;
	color: #d1d5db;
	padding: 20px 0 0;
	letter-spacing: 0.05em;
}
</style>
