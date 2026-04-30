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
						<div class="avatar-wrapper" @click="triggerImageUpload">
							<img
								v-if="user.data.user_image"
								class="avatar-img"
								:src="user.data.user_image"
								:alt="user.data.first_name"
							/>
							<div v-else class="avatar-fallback">
								{{ user.data.first_name[0] }}
							</div>
							<div class="avatar-edit-badge">
								<FeatherIcon v-if="!isUploading" name="edit-2" class="edit-icon" />
								<div v-else class="upload-spinner-sm"></div>
							</div>
						</div>
						<input
							ref="fileInput"
							type="file"
							accept="image/*"
							class="hidden"
							@change="onImageSelected"
						/>

						<span v-if="employee" class="emp-name">{{ employee?.data?.employee_name }}</span>
						<span v-if="employee" class="emp-designation">{{ employee?.data?.designation }}</span>

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
						<!-- Use button (not div) so click events fire reliably inside ion-content -->
						<button
							v-for="link in profileLinks"
							:key="link.title"
							class="section-row w-full"
							@click="openInfoModal(link)"
						>
							<div class="section-left">
								<FeatherIcon :name="link.icon" class="section-icon" />
								<span class="section-label">{{ link.title }}</span>
							</div>
							<FeatherIcon name="chevron-right" class="section-arrow" />
						</button>

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

		<!-- Bottom-sheet info panel — rendered directly inside ion-page (outside
		     ion-content) so Ionic's stacking context is correct on all mobile
		     browsers including iOS Safari PWA mode. -->
		<div v-if="isInfoModalOpen" class="profile-sheet-overlay" @click.self="closeInfoModal">
			<!-- Backdrop -->
			<div class="profile-sheet-backdrop" @click="closeInfoModal"></div>

			<!-- Sheet panel -->
			<div class="profile-sheet">
				<!-- Drag handle -->
				<div class="profile-sheet-handle-row">
					<div class="profile-sheet-handle"></div>
				</div>

				<!-- Sheet header -->
				<div class="profile-sheet-header">
					<span class="profile-sheet-title">{{ selectedItem?.title }}</span>
					<button class="profile-sheet-close" @click="closeInfoModal">
						<FeatherIcon name="x" class="w-4 h-4 text-gray-500" />
					</button>
				</div>

				<!-- Loading skeleton -->
				<div v-if="!employeeDoc.doc" class="profile-sheet-body">
					<div v-for="n in 7" :key="n" class="profile-field-row">
						<div class="skeleton-label"></div>
						<div class="skeleton-value"></div>
					</div>
				</div>

				<!-- Field list -->
				<div v-else class="profile-sheet-body">
					<div
						v-for="field in selectedItem.fields"
						:key="field"
						class="profile-field-row"
					>
						<span class="profile-field-label">{{ getFieldLabel(field) }}</span>
						<span class="profile-field-value">{{ employeeDoc.doc?.[field] || "—" }}</span>
					</div>
				</div>
			</div>
		</div>
	</ion-page>
</template>

<script setup>
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue"
import { useRouter } from "vue-router"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, createDocumentResource, createResource, call } from "frappe-ui"

import { showErrorAlert } from "@/utils/dialogs"
import { arePushNotificationsEnabled } from "@/data/notifications"

const DOCTYPE = "Employee"

const socket = inject("$socket")
const session = inject("$session")
const user = inject("$user")
const employee = inject("$employee")
const __ = inject("$translate")

const router = useRouter()

// ── Profile image upload ──────────────────────────────────────────────────
const fileInput = ref(null)
const isUploading = ref(false)

function triggerImageUpload() {
	fileInput.value?.click()
}

async function onImageSelected(event) {
	const file = event.target.files?.[0]
	if (!file) return
	isUploading.value = true
	try {
		const dataUrl = await readFileAsDataUrl(file)
		const base64 = dataUrl.split(",")[1]
		const fileDoc = await call("hrms.api.upload_base64_file", {
			content: base64,
			dt: "User",
			dn: session.user,
			filename: file.name,
			fieldname: "user_image",
		})
		await call("frappe.client.set_value", {
			doctype: "User",
			name: session.user,
			fieldname: "user_image",
			value: fileDoc.file_url,
		})
		await user.reload()
	} catch (e) {
		console.error("Image upload failed", e)
	} finally {
		isUploading.value = false
		event.target.value = ""
	}
}

function readFileAsDataUrl(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onload = () => resolve(reader.result)
		reader.onerror = reject
		reader.readAsDataURL(file)
	})
}

// ── Profile sections ──────────────────────────────────────────────────────
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

// ── Sheet open / close ────────────────────────────────────────────────────
const isInfoModalOpen = ref(false)
const selectedItem = ref(null)

function openInfoModal(link) {
	selectedItem.value = link
	isInfoModalOpen.value = true
}

function closeInfoModal() {
	isInfoModalOpen.value = false
	selectedItem.value = null
}

// ── Push notifications ────────────────────────────────────────────────────
const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

// ── Default Present badge ─────────────────────────────────────────────────
const defaultPresentResource = createResource({
	url: "vgts.default_present.default_present.is_default_present",
	params: { employee: employee.data.name },
	cache: `hrms:default_present:${employee.data.name}`,
	auto: true,
})

const isDefaultPresent = computed(() => !!defaultPresentResource.data)

// ── Employee document (for field values) ──────────────────────────────────
const employeeDoc = createDocumentResource({
	doctype: DOCTYPE,
	name: employee.data.name,
	cache: `hrms:employee_doc:${employee.data.name}`,
	auto: true,
})

// ── Employee doctype fields (for labels) ──────────────────────────────────
const employeeDocType = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: DOCTYPE },
	cache: "hrms:employee_doctype_fields",
	auto: true,
})

function getFieldLabel(fieldname) {
	const field = employeeDocType.data?.find((f) => f.fieldname === fieldname)
	return __(field?.label ?? fieldname, null, "Employee")
}

// ── Logout ────────────────────────────────────────────────────────────────
const logout = async () => {
	try {
		await session.logout.submit()
	} catch (e) {
		const msg = "An error occurred while attempting to log out!"
		console.error(msg, e)
		showErrorAlert(msg)
	}
}

// ── Live reload via socket ────────────────────────────────────────────────
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
/* ── Page ─────────────────────────────────────────────────────────────── */
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
	.profile-container { max-width: 520px; }
}

@media (min-width: 1024px) {
	.profile-page { padding: 0 40px 60px; }
	.profile-container { max-width: 680px; }
}

/* ── Nav ──────────────────────────────────────────────────────────────── */
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

/* ── Avatar card ──────────────────────────────────────────────────────── */
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

.avatar-wrapper {
	position: relative;
	width: 80px;
	height: 80px;
	margin-bottom: 8px;
	cursor: pointer;
}

.avatar-img {
	height: 80px;
	width: 80px;
	border-radius: 50%;
	object-fit: cover;
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
}

.avatar-edit-badge {
	position: absolute;
	bottom: 2px;
	right: 2px;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	background: #ffffff;
	border: 1.5px solid #e5e7eb;
	box-shadow: 0 1px 4px rgba(0,0,0,0.15);
	display: flex;
	align-items: center;
	justify-content: center;
}

.edit-icon { height: 12px; width: 12px; color: #6b7280; }

.upload-spinner-sm {
	width: 12px;
	height: 12px;
	border: 2px solid rgba(107,114,128,0.3);
	border-top-color: #6b7280;
	border-radius: 50%;
	animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.emp-name { font-size: 1.125rem; font-weight: 700; color: #111827; }
.emp-designation { font-size: 0.8125rem; color: #6b7280; }

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

.info-icon { height: 12px; width: 12px; }

/* ── Section list ─────────────────────────────────────────────────────── */
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
	background: transparent;
	border-radius: 0;
	transition: background 0.1s;
	text-align: left;
}

.section-row:last-child { border-bottom: none; }
.section-row:active { background: #f9fafb; }

.section-left { display: flex; align-items: center; gap: 12px; }
.section-icon { height: 18px; width: 18px; color: #9ca3af; }
.section-label { font-size: 0.9375rem; font-weight: 500; color: #374151; }
.section-arrow { height: 16px; width: 16px; color: #d1d5db; }

/* ── Logout / Footer ──────────────────────────────────────────────────── */
.logout-btn { border-radius: 12px !important; }

.footer-text {
	text-align: center;
	font-size: 0.6875rem;
	color: #d1d5db;
	padding: 20px 0 0;
	letter-spacing: 0.05em;
}

/* ── Bottom sheet (inside ion-page, outside ion-content) ──────────────── */
.profile-sheet-overlay {
	position: absolute;
	inset: 0;
	z-index: 9999;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
	pointer-events: all;
}

.profile-sheet-backdrop {
	position: absolute;
	inset: 0;
	background: rgba(0, 0, 0, 0.45);
}

.profile-sheet {
	position: relative;
	background: #ffffff;
	border-radius: 20px 20px 0 0;
	max-height: 85vh;
	display: flex;
	flex-direction: column;
	box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.12);
	animation: sheet-slide-up 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

@keyframes sheet-slide-up {
	from { transform: translateY(100%); }
	to   { transform: translateY(0); }
}

.profile-sheet-handle-row {
	display: flex;
	justify-content: center;
	padding: 12px 0 4px;
	flex-shrink: 0;
}

.profile-sheet-handle {
	width: 40px;
	height: 4px;
	border-radius: 99px;
	background: #d1d5db;
}

.profile-sheet-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 16px 12px;
	border-bottom: 1px solid #f3f4f6;
	flex-shrink: 0;
}

.profile-sheet-title {
	font-size: 1rem;
	font-weight: 600;
	color: #111827;
}

.profile-sheet-close {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: 50%;
	background: transparent;
	border: none;
	cursor: pointer;
	transition: background 0.15s;
}

.profile-sheet-close:active { background: #f3f4f6; }

.profile-sheet-body {
	overflow-y: auto;
	flex: 1;
	padding: 4px 16px 24px;
}

.profile-field-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 13px 0;
	border-bottom: 1px solid #f9fafb;
}

.profile-field-row:last-child { border-bottom: none; }

.profile-field-label {
	font-size: 0.875rem;
	color: #6b7280;
	flex-shrink: 0;
}

.profile-field-value {
	font-size: 0.875rem;
	color: #111827;
	text-align: right;
	word-break: break-word;
}

/* Skeleton shimmer */
.skeleton-label {
	height: 14px;
	width: 100px;
	border-radius: 6px;
	background: #f3f4f6;
	animation: shimmer 1.2s ease-in-out infinite;
}

.skeleton-value {
	height: 14px;
	width: 80px;
	border-radius: 6px;
	background: #f3f4f6;
	animation: shimmer 1.2s ease-in-out infinite 0.2s;
}

@keyframes shimmer {
	0%, 100% { opacity: 1; }
	50%       { opacity: 0.4; }
}
</style>
