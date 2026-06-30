<template>
	<ion-page>
		<ion-content :scroll-y="true">
			<div class="ap-page">

				<!-- ── Header ───────────────────────────────────────────────── -->
				<header class="ap-header">
					<div class="ap-header-left">
						<h2 class="ap-title">{{ __("Approvals") }}</h2>
						<span v-if="totalCount > 0" class="ap-total-badge">{{ totalCount }}</span>
					</div>
					<button
						class="ap-refresh-btn"
						:class="{ 'ap-spinning': teamRequests.loading }"
						@click="teamRequests.reload()"
					>
						<FeatherIcon name="refresh-cw" class="w-4 h-4" />
					</button>
				</header>

				<!-- ── Filter tabs ──────────────────────────────────────────── -->
				<div class="ap-tabs-row">
					<button
						v-for="tab in tabs"
						:key="tab.key"
						class="ap-tab"
						:class="{ 'ap-tab--active': activeTab === tab.key }"
						@click="activeTab = tab.key"
					>
						{{ tab.label }}
						<span v-if="tab.count > 0" class="ap-tab-count">{{ tab.count }}</span>
					</button>
				</div>

				<!-- ── Loading skeleton ─────────────────────────────────────── -->
				<template v-if="teamRequests.loading && !allItems.length">
					<div v-for="n in 4" :key="n" class="ap-skeleton-card">
						<div class="ap-skel-row">
							<div class="ap-skel-badge"></div>
							<div class="ap-skel-date"></div>
						</div>
						<div class="ap-skel-name"></div>
						<div class="ap-skel-detail"></div>
						<div class="ap-skel-actions">
							<div class="ap-skel-btn"></div>
							<div class="ap-skel-btn"></div>
						</div>
					</div>
				</template>

				<!-- ── Empty state ──────────────────────────────────────────── -->
				<div v-else-if="!teamRequests.loading && filteredItems.length === 0" class="ap-empty">
					<div class="ap-empty-icon">
						<FeatherIcon name="check-circle" class="w-10 h-10 text-green-400" />
					</div>
					<p class="ap-empty-title">{{ __("All clear!") }}</p>
					<p class="ap-empty-sub">{{ __("No pending requests for your approval.") }}</p>
				</div>

				<!-- ── Request cards ────────────────────────────────────────── -->
				<div v-else class="ap-cards">
					<div
						v-for="item in filteredItems"
						:key="item.name"
						class="ap-card"
					>
						<!-- Card top row: type badge + stage badge + date -->
						<div class="ap-card-toprow">
							<span class="ap-type-badge" :class="typeBadgeClass(item.type)">
								{{ typeLabelMap[item.type] || item.type }}
							</span>
							<div class="ap-card-toprow-right">
								<span class="ap-stage-badge" :class="stageBadgeClass(item.custom_approval_stage)">
									{{ stageLabel(item.custom_approval_stage) }}
								</span>
								<span class="ap-date">{{ item.creation_fmt }}</span>
							</div>
						</div>

						<!-- Employee name -->
						<p class="ap-emp-name">{{ item.employee_name }}</p>

						<!-- Detail line -->
						<p class="ap-detail">{{ detailLine(item) }}</p>

						<!-- Reason / description -->
						<p v-if="itemReason(item)" class="ap-reason">
							{{ itemReason(item) }}
						</p>

						<!-- Card footer: view + action buttons -->
						<div class="ap-card-footer">
							<!-- View full form -->
							<router-link :to="itemRoute(item)" class="ap-view-btn">
								{{ __("View") }}
								<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
							</router-link>

							<!-- Action buttons (only for current pending approver) -->
							<template v-if="canApprove(item)">
								<button
									class="ap-reject-btn"
									:disabled="!!actionLoading[item.name]"
									@click="openRejectSheet(item)"
								>
									<FeatherIcon name="x" class="w-3.5 h-3.5 mr-1" />
									{{ __("Reject") }}
								</button>
								<button
									class="ap-approve-btn"
									:disabled="!!actionLoading[item.name]"
									@click="doApprove(item)"
								>
									<span v-if="actionLoading[item.name] === 'approving'" class="ap-spinner"></span>
									<FeatherIcon v-else name="check" class="w-3.5 h-3.5 mr-1" />
									{{ __("Approve") }}
								</button>
							</template>
						</div>
					</div>
				</div>

			</div>
			<!-- END pending cards -->

			<!-- ── Approved by Me section ───────────────────────────────────── -->
			<div class="ap-approved-section">
				<div class="ap-approved-header" @click="approvedExpanded = !approvedExpanded">
					<span class="ap-approved-title">{{ __("Approved by Me") }}</span>
					<span v-if="approvedItems.length > 0" class="ap-tab-count">{{ approvedItems.length }}</span>
					<FeatherIcon
						:name="approvedExpanded ? 'chevron-up' : 'chevron-down'"
						class="w-4 h-4 text-gray-400 ml-auto"
					/>
				</div>

				<template v-if="approvedExpanded">
					<div v-if="approvedRequests.loading && !approvedItems.length" class="ap-approved-loading">
						<div v-for="n in 3" :key="n" class="ap-skeleton-card ap-skeleton-card--sm">
							<div class="ap-skel-row"><div class="ap-skel-badge"></div><div class="ap-skel-date"></div></div>
							<div class="ap-skel-name"></div>
						</div>
					</div>
					<div v-else-if="!approvedRequests.loading && approvedItems.length === 0" class="ap-approved-empty">
						{{ __("No approvals in the last 30 days.") }}
					</div>
					<div v-else class="ap-cards ap-cards--approved">
						<div
							v-for="item in approvedItems"
							:key="item.name"
							class="ap-card ap-card--approved"
						>
							<div class="ap-card-toprow">
								<span class="ap-type-badge" :class="typeBadgeClass(item.type)">
									{{ typeLabelMap[item.type] || item.type }}
								</span>
								<div class="ap-card-toprow-right">
									<span class="ap-stage-badge ap-stage--done">{{ __("Approved") }}</span>
									<span class="ap-date">{{ item.creation_fmt }}</span>
								</div>
							</div>
							<p class="ap-emp-name">{{ item.employee_name }}</p>
							<p class="ap-detail">{{ detailLine(item) }}</p>
							<p v-if="itemReason(item)" class="ap-reason">{{ itemReason(item) }}</p>
						</div>
					</div>
				</template>
			</div>
			<!-- END ap-approved-section -->
		</ion-content>

		<!-- ── Reject reason bottom sheet (inside ion-page) ────────────────── -->
		<div v-if="rejectSheet.open" class="ap-reject-overlay" @click.self="closeRejectSheet">
			<div class="ap-reject-backdrop" @click="closeRejectSheet"></div>
			<div class="ap-reject-sheet">
				<div class="ap-reject-handle-row">
					<div class="ap-reject-handle"></div>
				</div>
				<div class="ap-reject-header">
					<span class="ap-reject-title">{{ __("Reject Request") }}</span>
					<button class="ap-reject-close" @click="closeRejectSheet">
						<FeatherIcon name="x" class="w-4 h-4 text-gray-500" />
					</button>
				</div>
				<div class="ap-reject-body">
					<p class="ap-reject-emp">{{ rejectSheet.item?.employee_name }}</p>
					<p class="ap-reject-sub">{{ detailLine(rejectSheet.item) }}</p>
					<label class="ap-reject-label">{{ __("Reason for rejection") }} *</label>
					<textarea
						v-model="rejectReason"
						class="ap-reject-textarea"
						:placeholder="__('Enter reason...')"
						rows="3"
					></textarea>
					<button
						class="ap-reject-confirm-btn"
						:disabled="!rejectReason.trim() || !!actionLoading[rejectSheet.item?.name]"
						@click="doReject"
					>
						<span v-if="actionLoading[rejectSheet.item?.name] === 'rejecting'" class="ap-spinner ap-spinner--white"></span>
						{{ __("Confirm Rejection") }}
					</button>
				</div>
			</div>
		</div>
	</ion-page>
</template>

<script setup>
import { ref, computed, inject, onMounted, onBeforeUnmount } from "vue"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, createResource, call, toast } from "frappe-ui"

const __ = inject("$translate")
const employee = inject("$employee")
const sessionUser = computed(() => employee?.data?.user_id ?? "")

// ── Data ──────────────────────────────────────────────────────────────────────

const teamRequests = createResource({
	url: "vgts.api.get_team_requests",
	auto: true,
})

const approvedRequests = createResource({
	url: "vgts.api.get_approved_requests",
	auto: true,
})

const approvedExpanded = ref(false)

const approvedItems = computed(() => {
	const d = approvedRequests.data
	if (!d) return []

	const DOCTYPE = {
		"Leave":             "Leave Application",
		"Permission":        "Employee Permission",
		"Attendance Request":"Attendance Request",
		"Shift Request":     "Shift Request",
		"Regularization":   "Attendance Regularization",
		"CompOff":           "Compensatory Leave Request",
	}

	const flatten = (arr) =>
		(arr || []).map((item) => ({
			...item,
			doctype: DOCTYPE[item.type] || item.type,
		}))

	return [
		...flatten(d.leaves),
		...flatten(d.permissions),
		...flatten(d.attendance_requests),
		...flatten(d.shift_requests),
		...flatten(d.regularizations),
		...flatten(d.compensatory_requests),
	].sort((a, b) => (b.creation || "").localeCompare(a.creation || ""))
})

// Flatten all request arrays into a single list with doctype attached
const allItems = computed(() => {
	const d = teamRequests.data
	if (!d) return []

	const DOCTYPE = {
		"Leave":             "Leave Application",
		"Permission":        "Employee Permission",
		"Attendance Request":"Attendance Request",
		"Shift Request":     "Shift Request",
		"Regularization":   "Attendance Regularization",
		"CompOff":           "Compensatory Leave Request",
	}

	const flatten = (arr) =>
		(arr || []).map((item) => ({
			...item,
			doctype: DOCTYPE[item.type] || item.type,
		}))

	return [
		...flatten(d.leaves),
		...flatten(d.permissions),
		...flatten(d.attendance_requests),
		...flatten(d.shift_requests),
		...flatten(d.regularizations),
		...flatten(d.compensatory_requests),
	].sort((a, b) => (b.creation || "").localeCompare(a.creation || ""))
})

// ── Tabs ──────────────────────────────────────────────────────────────────────

const activeTab = ref("all")

const tabs = computed(() => {
	const d = teamRequests.data || {}
	return [
		{ key: "all",         label: __("All"),         count: allItems.value.length },
		{ key: "leave",       label: __("Leave"),        count: (d.leaves || []).length },
		{ key: "permission",  label: __("Permission"),   count: (d.permissions || []).length },
		{ key: "attendance",  label: __("Attendance"),   count: (d.attendance_requests || []).length },
		{ key: "others",      label: __("Others"),
			count: ((d.shift_requests || []).length + (d.regularizations || []).length + (d.compensatory_requests || []).length) },
	].filter((t) => t.key === "all" || t.count > 0)
})

const filteredItems = computed(() => {
	if (activeTab.value === "all") return allItems.value

	const typeFilter = {
		leave:      ["Leave"],
		permission: ["Permission"],
		attendance: ["Attendance Request"],
		others:     ["Shift Request", "Regularization", "CompOff"],
	}
	const allowed = typeFilter[activeTab.value] || []
	return allItems.value.filter((i) => allowed.includes(i.type))
})

const totalCount = computed(() => allItems.value.length)

// ── Approve / Reject logic ────────────────────────────────────────────────────

const actionLoading = ref({})  // name → "approving" | "rejecting" | null

function canApprove(item) {
	return item.current_approver === sessionUser.value
}

async function doApprove(item) {
	const isSecondary = item.custom_approval_stage === "Pending Secondary Reporting Approval"
	const method = isSecondary
		? "hrms.hr.two_level_approval.secondary_approve"
		: "vgts.api.primary_approve_request"

	actionLoading.value = { ...actionLoading.value, [item.name]: "approving" }

	try {
		await call(method, { doctype: item.doctype, docname: item.name })
		actionLoading.value = { ...actionLoading.value, [item.name]: null }
		toast({
			title: __("Approved"),
			text: __("Request approved successfully."),
			icon: "check-circle",
			iconClasses: "text-green-500",
			position: "bottom-center",
		})
		teamRequests.reload()
	} catch (err) {
		actionLoading.value = { ...actionLoading.value, [item.name]: null }
		const msg = err?.messages?.[0] || err?.message || __("Approval failed. Please try again.")
		toast({
			title: __("Error"),
			text: msg,
			icon: "alert-circle",
			iconClasses: "text-red-500",
			position: "bottom-center",
		})
	}
}

// Reject sheet state
const rejectSheet = ref({ open: false, item: null })
const rejectReason = ref("")

function openRejectSheet(item) {
	rejectReason.value = ""
	rejectSheet.value = { open: true, item }
}

function closeRejectSheet() {
	rejectSheet.value = { open: false, item: null }
	rejectReason.value = ""
}

async function doReject() {
	const item = rejectSheet.value.item
	if (!item || !rejectReason.value.trim()) return

	const isSecondary = item.custom_approval_stage === "Pending Secondary Reporting Approval"
	const method = isSecondary
		? "hrms.hr.two_level_approval.secondary_reject"
		: "hrms.hr.two_level_approval.primary_reject"

	actionLoading.value = { ...actionLoading.value, [item.name]: "rejecting" }

	try {
		await call(method, { doctype: item.doctype, docname: item.name, reason: rejectReason.value.trim() })
		actionLoading.value = { ...actionLoading.value, [item.name]: null }
		toast({
			title: __("Rejected"),
			text: __("Request has been rejected."),
			icon: "x-circle",
			iconClasses: "text-red-500",
			position: "bottom-center",
		})
		closeRejectSheet()
		teamRequests.reload()
	} catch (err) {
		actionLoading.value = { ...actionLoading.value, [item.name]: null }
		const msg = err?.messages?.[0] || err?.message || __("Rejection failed. Please try again.")
		toast({
			title: __("Error"),
			text: msg,
			icon: "alert-circle",
			iconClasses: "text-red-500",
			position: "bottom-center",
		})
	}
}

// ── Display helpers ───────────────────────────────────────────────────────────

const typeLabelMap = {
	"Leave":             "Leave",
	"Permission":        "Permission",
	"Attendance Request":"Attendance",
	"Shift Request":     "Shift",
	"Regularization":   "Regularization",
	"CompOff":           "Comp Off",
}

function typeBadgeClass(type) {
	return {
		"Leave":             "ap-badge--leave",
		"Permission":        "ap-badge--perm",
		"Attendance Request":"ap-badge--att",
		"Shift Request":     "ap-badge--shift",
		"Regularization":   "ap-badge--reg",
		"CompOff":           "ap-badge--comp",
	}[type] || "ap-badge--default"
}

function stageBadgeClass(stage) {
	if (stage === "Pending Secondary Reporting Approval") return "ap-stage--secondary"
	return "ap-stage--primary"
}

function stageLabel(stage) {
	if (stage === "Pending Secondary Reporting Approval") return __("2nd Approval")
	return __("1st Approval")
}

function detailLine(item) {
	if (!item) return ""
	const parts = []

	// Date range
	if (item.from_date_fmt && item.to_date_fmt && item.from_date_fmt !== item.to_date_fmt)
		parts.push(`${item.from_date_fmt} – ${item.to_date_fmt}`)
	else if (item.from_date_fmt)
		parts.push(item.from_date_fmt)
	else if (item.date_fmt)
		parts.push(item.date_fmt)

	// Type-specific
	if (item.leave_type) parts.push(item.leave_type)
	if (item.total_leave_days) parts.push(`${item.total_leave_days}d`)
	if (item.reason && item.type !== "Leave") parts.push(item.reason)
	if (item.shift_type) parts.push(item.shift_type)
	if (item.from_time && item.to_time) parts.push(`${item.from_time} – ${item.to_time}`)

	return parts.join("  ·  ")
}

function itemReason(item) {
	if (item.description && item.description.trim()) return item.description.trim()
	if (item.type === "Leave" && item.reason) return item.reason
	return ""
}

function itemRoute(item) {
	const routeMap = {
		"Leave Application":          { name: "LeaveApplicationDetailView",            params: { id: item.name } },
		"Employee Permission":         { name: "EmployeePermissionDetailView",           params: { id: item.name } },
		"Attendance Request":          { name: "AttendanceRequestDetailView",            params: { id: item.name } },
		"Shift Request":               { name: "ShiftRequestDetailView",                 params: { id: item.name } },
		"Attendance Regularization":   { name: "AttendanceRegularizationDetailView",     params: { id: item.name } },
		"Compensatory Leave Request":  { name: "CompensatoryLeaveDetailView",            params: { id: item.name } },
	}
	return routeMap[item.doctype] || { name: "Home" }
}

// ── Visibility refresh ────────────────────────────────────────────────────────

function onVisible() {
	if (!document.hidden) teamRequests.reload()
}

onMounted(() => document.addEventListener("visibilitychange", onVisible))
onBeforeUnmount(() => document.removeEventListener("visibilitychange", onVisible))
</script>

<style scoped>
/* ── Page ────────────────────────────────────────────────────────── */
.ap-page {
	min-height: 100%;
	background: #f9fafb;
	padding: 0 0 80px;
}

/* ── Header ──────────────────────────────────────────────────────── */
.ap-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 16px 12px;
	position: sticky;
	top: 0;
	z-index: 10;
	background: #f9fafb;
}

.ap-header-left {
	display: flex;
	align-items: center;
	gap: 8px;
}

.ap-title {
	font-size: 1.25rem;
	font-weight: 700;
	color: #111827;
	margin: 0;
}

.ap-total-badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 22px;
	height: 22px;
	padding: 0 6px;
	border-radius: 999px;
	background: #ef4444;
	color: #fff;
	font-size: 11px;
	font-weight: 700;
}

.ap-refresh-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 36px;
	height: 36px;
	border-radius: 50%;
	background: #fff;
	border: 1px solid #e5e7eb;
	color: #6b7280;
	cursor: pointer;
	transition: background 0.15s;
}

.ap-refresh-btn:active { background: #f3f4f6; }

.ap-spinning {
	animation: ap-spin 0.8s linear infinite;
}

@keyframes ap-spin { to { transform: rotate(360deg); } }

/* ── Filter tabs ─────────────────────────────────────────────────── */
.ap-tabs-row {
	display: flex;
	gap: 6px;
	padding: 0 16px 12px;
	overflow-x: auto;
	scrollbar-width: none;
}
.ap-tabs-row::-webkit-scrollbar { display: none; }

.ap-tab {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 6px 14px;
	border-radius: 999px;
	font-size: 0.8125rem;
	font-weight: 500;
	white-space: nowrap;
	background: #fff;
	border: 1px solid #e5e7eb;
	color: #6b7280;
	cursor: pointer;
	transition: all 0.15s;
	flex-shrink: 0;
}

.ap-tab--active {
	background: #1e3a8a;
	border-color: #1e3a8a;
	color: #fff;
}

.ap-tab-count {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 18px;
	height: 18px;
	padding: 0 4px;
	border-radius: 999px;
	background: rgba(255,255,255,0.25);
	font-size: 10px;
	font-weight: 700;
	color: inherit;
}

.ap-tab:not(.ap-tab--active) .ap-tab-count {
	background: #f3f4f6;
	color: #6b7280;
}

/* ── Cards ───────────────────────────────────────────────────────── */
.ap-cards {
	display: flex;
	flex-direction: column;
	gap: 10px;
	padding: 0 16px;
}

.ap-card {
	background: #fff;
	border-radius: 14px;
	border: 1px solid #e5e7eb;
	padding: 14px;
	box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* Card top row */
.ap-card-toprow {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
	gap: 8px;
}

.ap-card-toprow-right {
	display: flex;
	align-items: center;
	gap: 6px;
	flex-shrink: 0;
}

/* Type badge */
.ap-type-badge {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 11px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.4px;
}

.ap-badge--leave   { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
.ap-badge--perm    { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.ap-badge--att     { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.ap-badge--shift   { background: #faf5ff; color: #7c3aed; border: 1px solid #ddd6fe; }
.ap-badge--reg     { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
.ap-badge--comp    { background: #f0fdfa; color: #0d9488; border: 1px solid #99f6e4; }
.ap-badge--default { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }

/* Stage badge */
.ap-stage-badge {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	border-radius: 999px;
	font-size: 10px;
	font-weight: 600;
}

.ap-stage--primary   { background: #fef3c7; color: #92400e; }
.ap-stage--secondary { background: #ede9fe; color: #5b21b6; }

.ap-date {
	font-size: 11px;
	color: #9ca3af;
	white-space: nowrap;
}

/* Content */
.ap-emp-name {
	font-size: 0.9375rem;
	font-weight: 700;
	color: #111827;
	margin: 0 0 3px;
}

.ap-detail {
	font-size: 0.8125rem;
	color: #6b7280;
	margin: 0 0 4px;
	line-height: 1.4;
}

.ap-reason {
	font-size: 0.8125rem;
	color: #374151;
	margin: 0 0 4px;
	font-style: italic;
	line-height: 1.4;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

/* Card footer */
.ap-card-footer {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 12px;
	padding-top: 10px;
	border-top: 1px solid #f3f4f6;
}

.ap-view-btn {
	display: inline-flex;
	align-items: center;
	font-size: 0.8125rem;
	color: #6b7280;
	text-decoration: none;
	margin-right: auto;
	padding: 4px 0;
}

.ap-view-btn:active { color: #374151; }

.ap-reject-btn, .ap-approve-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 7px 14px;
	border-radius: 8px;
	font-size: 0.8125rem;
	font-weight: 600;
	cursor: pointer;
	border: none;
	transition: opacity 0.15s, transform 0.1s;
}

.ap-reject-btn:active, .ap-approve-btn:active { transform: scale(0.96); }
.ap-reject-btn:disabled, .ap-approve-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ap-reject-btn {
	background: #fef2f2;
	color: #dc2626;
	border: 1px solid #fecaca;
}

.ap-approve-btn {
	background: #16a34a;
	color: #fff;
}

/* ── Skeleton ────────────────────────────────────────────────────── */
.ap-skeleton-card {
	background: #fff;
	border-radius: 14px;
	border: 1px solid #e5e7eb;
	padding: 14px;
	margin: 0 16px 10px;
	animation: ap-shimmer 1.3s ease-in-out infinite;
}

.ap-skel-row {
	display: flex;
	justify-content: space-between;
	margin-bottom: 10px;
}

.ap-skel-badge { height: 20px; width: 72px; border-radius: 999px; background: #f3f4f6; }
.ap-skel-date  { height: 14px; width: 60px; border-radius: 4px; background: #f3f4f6; }
.ap-skel-name  { height: 16px; width: 140px; border-radius: 4px; background: #f3f4f6; margin-bottom: 8px; }
.ap-skel-detail{ height: 13px; width: 190px; border-radius: 4px; background: #f3f4f6; margin-bottom: 12px; }

.ap-skel-actions {
	display: flex;
	gap: 8px;
	justify-content: flex-end;
	padding-top: 10px;
	border-top: 1px solid #f3f4f6;
}

.ap-skel-btn { height: 32px; width: 80px; border-radius: 8px; background: #f3f4f6; }

@keyframes ap-shimmer {
	0%, 100% { opacity: 1; }
	50%       { opacity: 0.5; }
}

/* ── Empty state ─────────────────────────────────────────────────── */
.ap-empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 64px 24px;
	gap: 10px;
	text-align: center;
}

.ap-empty-icon {
	width: 64px;
	height: 64px;
	border-radius: 50%;
	background: #f0fdf4;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: 4px;
}

.ap-empty-title { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.ap-empty-sub   { font-size: 0.875rem; color: #9ca3af; margin: 0; }

/* ── Spinner ─────────────────────────────────────────────────────── */
.ap-spinner {
	display: inline-block;
	width: 13px;
	height: 13px;
	border: 2px solid rgba(0,0,0,0.15);
	border-top-color: #16a34a;
	border-radius: 50%;
	animation: ap-spin 0.7s linear infinite;
	margin-right: 4px;
	flex-shrink: 0;
}

.ap-spinner--white {
	border-color: rgba(255,255,255,0.3);
	border-top-color: #fff;
}

/* ── Reject sheet ────────────────────────────────────────────────── */
.ap-reject-overlay {
	position: absolute;
	inset: 0;
	z-index: 9999;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
}

.ap-reject-backdrop {
	position: absolute;
	inset: 0;
	background: rgba(0,0,0,0.45);
}

.ap-reject-sheet {
	position: relative;
	background: #fff;
	border-radius: 20px 20px 0 0;
	box-shadow: 0 -4px 24px rgba(0,0,0,0.12);
	animation: ap-slide-up 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

@keyframes ap-slide-up {
	from { transform: translateY(100%); }
	to   { transform: translateY(0); }
}

.ap-reject-handle-row {
	display: flex;
	justify-content: center;
	padding: 12px 0 4px;
}

.ap-reject-handle {
	width: 40px;
	height: 4px;
	border-radius: 99px;
	background: #d1d5db;
}

.ap-reject-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 16px 12px;
	border-bottom: 1px solid #f3f4f6;
}

.ap-reject-title {
	font-size: 1rem;
	font-weight: 600;
	color: #111827;
}

.ap-reject-close {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: 50%;
	background: transparent;
	border: none;
	cursor: pointer;
}

.ap-reject-body {
	padding: 16px 16px 32px;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.ap-reject-emp  { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.ap-reject-sub  { font-size: 0.8125rem; color: #6b7280; margin: 0; }
.ap-reject-label { font-size: 0.875rem; font-weight: 500; color: #374151; margin: 4px 0 0; }

.ap-reject-textarea {
	width: 100%;
	border: 1.5px solid #d1d5db;
	border-radius: 10px;
	padding: 10px 12px;
	font-size: 0.875rem;
	color: #111827;
	resize: none;
	outline: none;
	font-family: inherit;
	transition: border-color 0.15s;
	box-sizing: border-box;
}

.ap-reject-textarea:focus { border-color: #6b7280; }

.ap-reject-confirm-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
	padding: 12px;
	background: #dc2626;
	color: #fff;
	border: none;
	border-radius: 10px;
	font-size: 0.9375rem;
	font-weight: 600;
	cursor: pointer;
	margin-top: 4px;
	transition: opacity 0.15s;
	gap: 6px;
}

.ap-reject-confirm-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ap-reject-confirm-btn:active:not(:disabled) { opacity: 0.85; }

/* ── Approved by Me section ──────────────────────────────────── */
.ap-approved-section {
	margin: 16px 16px 0;
	border: 1px solid #e5e7eb;
	border-radius: 12px;
	background: #fff;
	overflow: hidden;
}

.ap-approved-header {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 14px 16px;
	cursor: pointer;
	user-select: none;
}

.ap-approved-title {
	font-size: 0.9375rem;
	font-weight: 600;
	color: #374151;
}

.ap-approved-empty {
	padding: 12px 16px 16px;
	font-size: 0.875rem;
	color: #9ca3af;
	text-align: center;
}

.ap-approved-loading {
	padding: 0 12px 12px;
}

.ap-skeleton-card--sm {
	padding: 10px 12px;
	margin-bottom: 6px;
}

.ap-cards--approved {
	padding: 0 12px 12px;
}

.ap-card--approved {
	border-left: 3px solid #10b981;
	opacity: 0.85;
}

.ap-stage--done {
	background: #d1fae5;
	color: #065f46;
}
</style>
