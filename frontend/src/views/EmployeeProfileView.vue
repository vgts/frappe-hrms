<template>
	<ion-page>
		<ion-content :scroll-y="true">
			<div class="ep-page">
				<div class="ep-container">

					<!-- Nav -->
					<header class="ep-nav">
						<Button variant="ghost" class="!pl-0 hover:bg-white" @click="router.back()">
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="ep-nav-title">{{ __("Employee Profile") }}</h2>
						<div class="w-5"></div>
					</header>

					<!-- Loading skeleton -->
					<div v-if="profileResource.loading" class="ep-skeleton">
						<div class="ep-skel-avatar"></div>
						<div class="ep-skel-line w-40"></div>
						<div class="ep-skel-line w-28"></div>
					</div>

					<!-- Error -->
					<div v-else-if="profileResource.error" class="ep-error">
						<FeatherIcon name="alert-circle" class="h-8 w-8 text-red-400 mb-2" />
						<p>{{ __("Failed to load employee profile.") }}</p>
					</div>

					<template v-else-if="emp">
						<!-- Avatar Card -->
						<div class="ep-avatar-card">
							<div class="ep-avatar-wrap">
								<img
									v-if="emp.user_image"
									:src="emp.user_image"
									class="ep-avatar-img"
									:alt="emp.employee_name"
								/>
								<div v-else class="ep-avatar-fallback">
									{{ (emp.employee_name || "?")[0].toUpperCase() }}
								</div>
							</div>

							<span class="ep-emp-name">{{ emp.employee_name }}</span>
							<span class="ep-emp-desg">{{ emp.designation }}</span>

							<div class="ep-quick-row">
								<span v-if="emp.department" class="ep-quick-item">
									<FeatherIcon name="briefcase" class="ep-qi-icon" />
									{{ emp.department }}
								</span>
								<span v-if="emp.employee_number" class="ep-quick-item">
									<FeatherIcon name="hash" class="ep-qi-icon" />
									{{ emp.employee_number }}
								</span>
							</div>

							<!-- Check-in Status Badge -->
							<div
								class="ep-status-badge"
								:class="emp.is_checked_in ? 'ep-status-in' : 'ep-status-out'"
							>
								<span
									class="ep-status-dot"
									:class="emp.is_checked_in ? 'dot-in' : 'dot-out'"
								></span>
								<span class="ep-status-text">
									<template v-if="emp.is_checked_in">
										{{ __("IN") }}
										<span v-if="emp.checkin_time" class="ep-status-time">
											{{ __("since {0}", [emp.checkin_time]) }}
										</span>
									</template>
									<template v-else>
										{{ __("Yet to Check In") }}
									</template>
								</span>
							</div>
						</div>

						<!-- Info Grid: Location | Department | Shift -->
						<div class="ep-info-grid ep-info-grid-3">
							<div class="ep-info-cell" v-if="emp.branch">
								<span class="ep-cell-icon">
									<FeatherIcon name="map-pin" class="h-4 w-4" />
								</span>
								<div>
									<p class="ep-cell-lbl">{{ __("Location") }}</p>
									<p class="ep-cell-val">{{ emp.branch }}</p>
								</div>
							</div>
							<div class="ep-info-cell" v-if="emp.department">
								<span class="ep-cell-icon">
									<FeatherIcon name="grid" class="h-4 w-4" />
								</span>
								<div>
									<p class="ep-cell-lbl">{{ __("Department") }}</p>
									<p class="ep-cell-val">{{ emp.department }}</p>
								</div>
							</div>
							<div class="ep-info-cell" v-if="emp.shift_info">
								<span class="ep-cell-icon">
									<FeatherIcon name="clock" class="h-4 w-4" />
								</span>
								<div>
									<p class="ep-cell-lbl">{{ __("Shift") }}</p>
									<p class="ep-cell-val">
										{{ emp.shift_info.name }}
										<span class="ep-cell-sub">
											({{ emp.shift_info.start_fmt }} – {{ emp.shift_info.end_fmt }})
										</span>
									</p>
								</div>
							</div>
						</div>

						<!-- Info Grid: Email | Company -->
						<div class="ep-info-grid ep-info-grid-2" v-if="emp.work_email || emp.company">
							<div class="ep-info-cell" v-if="emp.work_email">
								<span class="ep-cell-icon">
									<FeatherIcon name="mail" class="h-4 w-4" />
								</span>
								<div>
									<p class="ep-cell-lbl">{{ __("Email") }}</p>
									<p class="ep-cell-val">{{ emp.work_email }}</p>
								</div>
							</div>
							<div class="ep-info-cell" v-if="emp.company">
								<span class="ep-cell-icon">
									<FeatherIcon name="home" class="h-4 w-4" />
								</span>
								<div>
									<p class="ep-cell-lbl">{{ __("Company") }}</p>
									<p class="ep-cell-val">{{ emp.company }}</p>
								</div>
							</div>
						</div>

						<!-- Organisation Structure -->
						<div class="ep-card" v-if="emp.reports_to_info || emp.department">
							<p class="ep-card-title">{{ __("Organization") }}</p>
							<div class="ep-org-row" v-if="emp.department">
								<FeatherIcon name="layers" class="ep-org-icon" />
								<span class="ep-org-lbl">{{ __("Department") }}</span>
								<span class="ep-org-val">{{ emp.department }}</span>
							</div>
							<div class="ep-org-row" v-if="emp.reports_to_info">
								<FeatherIcon name="user" class="ep-org-icon" />
								<span class="ep-org-lbl">{{ __("Reports To") }}</span>
								<div class="ep-org-mgr">
									<div class="ep-mgr-av-wrap">
										<img
											v-if="emp.reports_to_info.user_image"
											:src="emp.reports_to_info.user_image"
											class="ep-mgr-av-img"
										/>
										<div v-else class="ep-mgr-av-init">
											{{ (emp.reports_to_info.employee_name || "?")[0].toUpperCase() }}
										</div>
									</div>
									<div>
										<p class="ep-mgr-name">{{ emp.reports_to_info.employee_name }}</p>
										<p class="ep-mgr-desg">{{ emp.reports_to_info.designation }}</p>
									</div>
								</div>
							</div>
						</div>

						<!-- Details Card -->
						<div class="ep-card" v-if="detailFields.length">
							<p class="ep-card-title">{{ __("Details") }}</p>
							<div class="ep-detail-grid">
								<div
									class="ep-detail-item"
									v-for="f in detailFields"
									:key="f.lbl"
								>
									<p class="ep-detail-lbl">{{ __(f.lbl) }}</p>
									<p class="ep-detail-val">{{ f.val }}</p>
								</div>
							</div>
						</div>

						<!-- About Me -->
						<div class="ep-card" v-if="emp.custom_about_me">
							<p class="ep-card-title">{{ __("About") }}</p>
							<p class="ep-bio">{{ emp.custom_about_me }}</p>
						</div>
					</template>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, createResource } from "frappe-ui"
import { inject } from "vue"

const __ = inject("$translate")
const route  = useRoute()
const router = useRouter()

const employeeName = route.params.employeeName

const profileResource = createResource({
	url: "vgts.api.get_employee_profile",
	params: { employee_name: employeeName },
	auto: true,
})

const emp = computed(() => profileResource.data || null)

const detailFields = computed(() => {
	if (!emp.value) return []
	const e = emp.value
	return [
		{ lbl: "Employee ID",    val: e.employee_number || e.name },
		{ lbl: "Date of Joining", val: e.date_of_joining ? formatDate(e.date_of_joining) : null },
		{ lbl: "Employment Type", val: e.employment_type },
		{ lbl: "Mobile",          val: e.cell_number },
		{ lbl: "Personal Email",  val: e.personal_email },
		{ lbl: "Gender",          val: e.gender },
		{ lbl: "Date of Birth",   val: e.date_of_birth ? formatDate(e.date_of_birth) : null },
	].filter(f => f.val)
})

function formatDate(dateStr) {
	if (!dateStr) return ""
	try {
		const d = new Date(dateStr)
		return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
	} catch {
		return dateStr
	}
}
</script>

<style scoped>
.ep-page {
	min-height: 100%;
	background: #f9fafb;
	padding: 0 16px 40px;
}

.ep-container {
	max-width: 100%;
	margin: 0 auto;
}

@media (min-width: 768px) {
	.ep-container { max-width: 520px; }
}

@media (min-width: 1024px) {
	.ep-page { padding: 0 40px 60px; }
	.ep-container { max-width: 680px; }
}

/* Nav */
.ep-nav {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 0;
	position: sticky;
	top: 0;
	z-index: 10;
	background: #f9fafb;
}

.ep-nav-title {
	font-size: 1.125rem;
	font-weight: 600;
	color: #111827;
	margin: 0;
}

/* Skeleton */
.ep-skeleton {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	padding: 32px 0;
}

.ep-skel-avatar {
	width: 80px;
	height: 80px;
	border-radius: 50%;
	background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
	background-size: 200% 100%;
	animation: shimmer 1.2s infinite;
}

.ep-skel-line {
	height: 14px;
	border-radius: 7px;
	background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
	background-size: 200% 100%;
	animation: shimmer 1.2s infinite;
}

@keyframes shimmer { to { background-position: -200% 0; } }

/* Error */
.ep-error {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 48px 0;
	color: #9ca3af;
	font-size: 0.875rem;
}

/* Avatar Card */
.ep-avatar-card {
	display: flex;
	flex-direction: column;
	align-items: center;
	background: #fff;
	border-radius: 16px;
	border: 1px solid #e5e7eb;
	padding: 24px 16px 20px;
	gap: 4px;
}

.ep-avatar-wrap {
	position: relative;
	width: 80px;
	height: 80px;
	margin-bottom: 8px;
}

.ep-avatar-img {
	width: 80px;
	height: 80px;
	border-radius: 50%;
	object-fit: cover;
}

.ep-avatar-fallback {
	width: 80px;
	height: 80px;
	border-radius: 50%;
	background: #f3f4f6;
	color: #6b7280;
	font-size: 1.75rem;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
	text-transform: uppercase;
}

.ep-emp-name {
	font-size: 1.125rem;
	font-weight: 700;
	color: #111827;
}

.ep-emp-desg {
	font-size: 0.8125rem;
	color: #6b7280;
}

.ep-quick-row {
	display: flex;
	flex-wrap: wrap;
	gap: 12px;
	margin-top: 8px;
	justify-content: center;
}

.ep-quick-item {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 0.75rem;
	color: #9ca3af;
}

.ep-qi-icon {
	height: 12px;
	width: 12px;
}

/* Status Badge */
.ep-status-badge {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-top: 8px;
	padding: 5px 14px;
	border-radius: 999px;
	font-size: 0.8125rem;
	font-weight: 600;
}

.ep-status-in {
	background: #dcfce7;
	border: 1px solid #bbf7d0;
	color: #15803d;
}

.ep-status-out {
	background: #f3f4f6;
	border: 1px solid #e5e7eb;
	color: #9ca3af;
}

.ep-status-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	flex-shrink: 0;
}

.dot-in {
	background: #22c55e;
	animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.dot-out {
	background: #d1d5db;
}

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.4; }
}

.ep-status-text {
	display: flex;
	align-items: center;
	gap: 4px;
}

.ep-status-time {
	font-weight: 400;
	font-size: 0.75rem;
	opacity: 0.8;
}

/* Info Grid */
.ep-info-grid {
	display: grid;
	gap: 10px;
	margin-top: 12px;
}

.ep-info-grid-3 { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
.ep-info-grid-2 { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }

.ep-info-cell {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	background: #fff;
	border-radius: 12px;
	border: 1px solid #e5e7eb;
	padding: 12px;
}

.ep-cell-icon {
	color: #6b7280;
	flex-shrink: 0;
	margin-top: 1px;
}

.ep-cell-lbl {
	font-size: 0.6875rem;
	color: #9ca3af;
	margin: 0;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.ep-cell-val {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #374151;
	margin: 2px 0 0;
	word-break: break-word;
}

.ep-cell-sub {
	font-weight: 400;
	font-size: 0.75rem;
	color: #9ca3af;
}

/* Card */
.ep-card {
	background: #fff;
	border-radius: 16px;
	border: 1px solid #e5e7eb;
	padding: 16px;
	margin-top: 12px;
}

.ep-card-title {
	font-size: 0.75rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	color: #9ca3af;
	margin: 0 0 12px;
}

/* Org */
.ep-org-row {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	padding: 8px 0;
	border-bottom: 1px solid #f3f4f6;
}

.ep-org-row:last-child { border-bottom: none; }

.ep-org-icon {
	height: 15px;
	width: 15px;
	color: #9ca3af;
	flex-shrink: 0;
	margin-top: 2px;
}

.ep-org-lbl {
	font-size: 0.8125rem;
	color: #6b7280;
	width: 90px;
	flex-shrink: 0;
}

.ep-org-val {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #111827;
}

.ep-org-mgr {
	display: flex;
	align-items: center;
	gap: 10px;
}

.ep-mgr-av-wrap { flex-shrink: 0; }

.ep-mgr-av-img {
	width: 32px;
	height: 32px;
	border-radius: 50%;
	object-fit: cover;
}

.ep-mgr-av-init {
	width: 32px;
	height: 32px;
	border-radius: 50%;
	background: #e5e7eb;
	color: #6b7280;
	font-size: 0.875rem;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
	text-transform: uppercase;
}

.ep-mgr-name {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #111827;
	margin: 0;
}

.ep-mgr-desg {
	font-size: 0.75rem;
	color: #9ca3af;
	margin: 2px 0 0;
}

/* Details Grid */
.ep-detail-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
	gap: 14px;
}

.ep-detail-lbl {
	font-size: 0.6875rem;
	color: #9ca3af;
	margin: 0;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.ep-detail-val {
	font-size: 0.875rem;
	font-weight: 600;
	color: #111827;
	margin: 3px 0 0;
	word-break: break-word;
}

/* Bio */
.ep-bio {
	font-size: 0.875rem;
	color: #374151;
	line-height: 1.6;
	margin: 0;
}
</style>
