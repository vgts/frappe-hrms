<template>
	<ion-page>
		<ion-content :scroll-y="true">
			<div class="profile-page">

				<!-- Header with gradient -->
				<div class="profile-header">
					<div class="header-nav">
						<button class="back-btn" @click="router.back()">
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</button>
						<h2 class="header-title">{{ __("Profile") }}</h2>
						<div class="w-5"></div>
					</div>

					<!-- Avatar + Name -->
					<div class="avatar-section">
						<div class="avatar-ring">
							<img
								v-if="user.data.user_image"
								class="avatar-img"
								:src="user.data.user_image"
								:alt="user.data.first_name"
							/>
							<div v-else class="avatar-placeholder">
								{{ user.data.first_name?.[0] || "?" }}
							</div>
						</div>
						<div class="name-wrap">
							<span class="emp-name">{{ employee?.data?.employee_name }}</span>
							<span class="emp-designation">{{ employee?.data?.designation }}</span>
						</div>

						<!-- Default Present badge -->
						<div v-if="isDefaultPresent" class="dp-badge">
							<span class="dp-dot"></span>
							<span>{{ __("Default Present") }}</span>
						</div>
					</div>
				</div>

				<!-- Quick info chips -->
				<div class="quick-info" v-if="employee?.data">
					<div class="info-chip" v-if="employee.data.department">
						<FeatherIcon name="briefcase" class="chip-icon" />
						<span>{{ employee.data.department }}</span>
					</div>
					<div class="info-chip" v-if="employee.data.employee_number">
						<FeatherIcon name="hash" class="chip-icon" />
						<span>{{ employee.data.employee_number }}</span>
					</div>
					<div class="info-chip" v-if="employee.data.branch">
						<FeatherIcon name="map-pin" class="chip-icon" />
						<span>{{ employee.data.branch }}</span>
					</div>
				</div>

				<!-- Profile sections -->
				<div class="sections-wrap">
					<div
						v-for="link in profileLinks"
						:key="link.title"
						class="section-card"
						@click="openInfoModal(link)"
					>
						<div class="section-left">
							<div class="section-icon-wrap" :class="link.colorClass">
								<FeatherIcon :name="link.icon" class="section-icon" />
							</div>
							<div class="section-text">
								<div class="section-title">{{ link.title }}</div>
								<div class="section-subtitle">{{ link.subtitle }}</div>
							</div>
						</div>
						<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
					</div>

					<!-- Settings -->
					<router-link
						v-if="allowPushNotifications"
						:to="{ name: 'Settings' }"
						class="section-card"
					>
						<div class="section-left">
							<div class="section-icon-wrap bg-gray-50 text-gray-600">
								<FeatherIcon name="settings" class="section-icon" />
							</div>
							<div class="section-text">
								<div class="section-title">{{ __("Settings") }}</div>
								<div class="section-subtitle">{{ __("Notifications & preferences") }}</div>
							</div>
						</div>
						<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
					</router-link>
				</div>

				<!-- Logout -->
				<div class="logout-wrap">
					<button class="logout-btn" @click="logout">
						<FeatherIcon name="log-out" class="h-4 w-4" />
						<span>{{ __("Log Out") }}</span>
					</button>
				</div>

				<!-- App version -->
				<div class="version-text">VGTS-HRMS</div>
			</div>

			<!-- Info modal -->
			<ion-modal
				ref="modal"
				:is-open="isInfoModalOpen"
				@didDismiss="closeInfoModal"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<ProfileInfoModal
					v-if="selectedItem"
					:title="selectedItem.title"
					:data="
						selectedItem.fields.map((field) => {
							const [label, fieldtype] = getFieldInfo(field)
							return {
								fieldname: field,
								value: employeeDoc.doc[field],
								label: label,
								fieldtype: fieldtype,
							}
						})
					"
				/>
			</ion-modal>
		</ion-content>
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
		subtitle: __("Name, DOB, joining date & more"),
		colorClass: "bg-blue-50 text-blue-600",
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
		icon: "briefcase",
		title: __("Company Information"),
		subtitle: __("Department, designation & reporting"),
		colorClass: "bg-purple-50 text-purple-600",
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
		icon: "phone",
		title: __("Contact Information"),
		subtitle: __("Phone, email & address"),
		colorClass: "bg-green-50 text-green-600",
		fields: [
			"cell_number",
			"personal_email",
			"company_email",
			"preferred_email",
		],
	},
	{
		icon: "credit-card",
		title: __("Salary & Bank"),
		subtitle: __("CTC, PAN, bank account details"),
		colorClass: "bg-amber-50 text-amber-600",
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
const openInfoModal = async (request) => {
	selectedItem.value = request
	isInfoModalOpen.value = true
}

const closeInfoModal = async (_request) => {
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
	const field = employeeDocType.data.find(
		(field) => field.fieldname === fieldname
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
	background: #f4f6f8;
}

/* ── Header ─────────────────────────────────────────────── */
.profile-header {
	background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
	padding: 0 0 32px;
	border-radius: 0 0 24px 24px;
}

/* ── Desktop constraint — cap content width on large screens ── */
@media (min-width: 768px) {
	.header-nav,
	.avatar-section,
	.quick-info,
	.sections-wrap,
	.logout-wrap,
	.version-text {
		max-width: 520px;
		margin-left: auto;
		margin-right: auto;
	}
}

.header-nav {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 16px 0;
}

.back-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 36px;
	height: 36px;
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.1);
	border: none;
	color: #ffffff;
	cursor: pointer;
}

.back-btn:active {
	background: rgba(255, 255, 255, 0.2);
}

.header-title {
	font-size: 1.125rem;
	font-weight: 600;
	color: #ffffff;
	margin: 0;
}

/* ── Avatar ─────────────────────────────────────────────── */
.avatar-section {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	margin-top: 20px;
}

.avatar-ring {
	padding: 3px;
	border-radius: 50%;
	background: linear-gradient(135deg, #22c55e, #3b82f6);
}

.avatar-img {
	height: 88px;
	width: 88px;
	border-radius: 50%;
	object-fit: cover;
	border: 3px solid #111827;
}

.avatar-placeholder {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 88px;
	width: 88px;
	border-radius: 50%;
	background: #374151;
	color: #e5e7eb;
	font-size: 2rem;
	font-weight: 700;
	text-transform: uppercase;
	border: 3px solid #111827;
}

.name-wrap {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 2px;
}

.emp-name {
	font-size: 1.25rem;
	font-weight: 700;
	color: #ffffff;
}

.emp-designation {
	font-size: 0.8125rem;
	color: #9ca3af;
}

.dp-badge {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 4px 12px;
	border-radius: 999px;
	background: rgba(34, 197, 94, 0.15);
	border: 1px solid rgba(34, 197, 94, 0.3);
	font-size: 0.6875rem;
	font-weight: 600;
	color: #86efac;
}

.dp-dot {
	height: 6px;
	width: 6px;
	border-radius: 50%;
	background: #22c55e;
	flex-shrink: 0;
}

/* ── Quick info chips ───────────────────────────────────── */
.quick-info {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	padding: 16px 16px 0;
	justify-content: center;
	margin-top: -12px;
}

.info-chip {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 6px 12px;
	border-radius: 999px;
	background: #ffffff;
	border: 1px solid #e5e7eb;
	font-size: 0.75rem;
	font-weight: 500;
	color: #4b5563;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.chip-icon {
	height: 12px;
	width: 12px;
	color: #9ca3af;
}

/* ── Section cards ──────────────────────────────────────── */
.sections-wrap {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 20px 16px 0;
}

.section-card {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 14px 16px;
	background: #ffffff;
	border-radius: 14px;
	border: 1px solid #f3f4f6;
	cursor: pointer;
	transition: background 0.15s, box-shadow 0.15s;
	text-decoration: none;
}

.section-card:active {
	background: #f9fafb;
}

.section-left {
	display: flex;
	align-items: center;
	gap: 14px;
}

.section-icon-wrap {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 40px;
	height: 40px;
	border-radius: 12px;
	flex-shrink: 0;
}

.section-icon {
	height: 18px;
	width: 18px;
}

.section-text {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.section-title {
	font-size: 0.9375rem;
	font-weight: 600;
	color: #111827;
}

.section-subtitle {
	font-size: 0.75rem;
	color: #9ca3af;
}

/* ── Logout ─────────────────────────────────────────────── */
.logout-wrap {
	padding: 24px 16px 0;
}

.logout-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	width: 100%;
	padding: 14px;
	font-size: 0.9375rem;
	font-weight: 600;
	color: #ef4444;
	background: #ffffff;
	border: 1.5px solid #fecaca;
	border-radius: 14px;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
}

.logout-btn:active {
	background: #fef2f2;
	border-color: #fca5a5;
}

/* ── Version ────────────────────────────────────────────── */
.version-text {
	text-align: center;
	font-size: 0.6875rem;
	color: #d1d5db;
	padding: 20px 0 40px;
	letter-spacing: 0.05em;
}
</style>
