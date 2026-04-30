<template>
	<div class="flex flex-col w-full gap-5" v-if="calendarEvents.data">
		<div class="text-lg text-gray-800 font-bold">{{ __("Attendance Calendar") }}</div>

		<div class="flex flex-col gap-6 bg-white py-6 px-3.5 rounded-lg border-none">
			<!-- Month Change -->
			<div class="flex flex-row justify-between items-center px-4">
				<Button
					icon="chevron-left"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
				/>
				<span class="text-lg text-gray-800 font-bold">
					{{ firstOfMonth.format("MMMM") }} {{ firstOfMonth.format("YYYY") }}
				</span>
				<Button
					icon="chevron-right"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
				/>
			</div>

			<!-- Calendar -->
			<div class="grid grid-cols-7 gap-y-3">
				<!-- Day headers -->
				<div
					v-for="(day, i) in DAYS"
					:key="day + i"
					class="flex justify-center text-sm font-medium leading-6"
					:class="i === 0 || i === 6 ? 'text-orange-400' : 'text-gray-600'"
				>
					{{ day }}
				</div>

				<!-- Empty offset cells -->
				<div v-for="_ in firstOfMonth.get('d')" />

				<!-- Day cells -->
				<div v-for="index in firstOfMonth.endOf('M').get('D')" :key="index">
					<button
						class="h-8 w-8 flex rounded-full mx-auto focus:outline-none active:scale-95 transition-transform"
						:class="getCellClass(index)"
						@click="onDateClick(index)"
					>
						<span
							class="text-sm font-medium m-auto"
							:class="isWeekend(index) && !getEventOnDate(index) ? 'text-orange-400' : 'text-gray-800'"
						>
							{{ index }}
						</span>
					</button>
				</div>
			</div>

			<hr />

			<!-- Legend pills -->
			<div class="flex flex-wrap gap-2 px-1">
				<div
					v-for="item in legendItems"
					:key="item.label"
					class="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium"
					:class="item.pillClass"
				>
					<span class="w-2 h-2 rounded-full flex-shrink-0" :class="item.dotClass"></span>
					{{ item.label }}
					<span v-if="summary[item.status] !== undefined" class="font-bold ml-0.5">
						{{ summary[item.status] || 0 }}
					</span>
				</div>
			</div>
		</div>

		<!-- Date Detail Bottom Sheet -->
		<Teleport to="body">
			<div v-if="showDateModal" class="ac-overlay" @click.self="closeDateModal">
				<div class="ac-backdrop" @click="closeDateModal"></div>
				<div class="ac-sheet">
					<!-- Handle -->
					<div class="ac-handle-row"><div class="ac-handle"></div></div>

					<!-- Header -->
					<div class="ac-header">
						<span class="ac-date-title">{{ selectedDateFormatted }}</span>
						<button class="ac-close" @click="closeDateModal">
							<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
							</svg>
						</button>
					</div>

					<!-- Status badge -->
					<div v-if="selectedStatus" class="ac-status-row">
						<span class="ac-status-pill" :class="colorMap[selectedStatus] || 'bg-gray-100 text-gray-600'">
							{{ __(selectedStatus) }}
						</span>
					</div>

					<!-- Content -->
					<div class="ac-body">

						<!-- Weekend with no data -->
						<div v-if="isSelectedWeekend && !dateDetail?.in_time" class="ac-empty">
							<span>🌿</span>
							<span class="text-sm text-gray-400">{{ __("Weekend — Rest day") }}</span>
						</div>

						<!-- Holiday -->
						<div v-else-if="selectedStatus === 'Holiday'" class="ac-holiday-block">
							<span class="text-2xl">🎉</span>
							<span class="ac-holiday-label">{{ __("Holiday") }}</span>
						</div>

						<!-- Loading -->
						<div v-else-if="dateDetailLoading" class="ac-loading">
							<div class="ac-skeleton" v-for="n in 3" :key="n"></div>
						</div>

						<!-- No checkin -->
						<div v-else-if="!dateDetail?.in_time" class="ac-empty">
							<span>🕐</span>
							<span class="text-sm text-gray-400">{{ __("No check-in recorded") }}</span>
						</div>

						<!-- Checkin detail -->
						<div v-else class="ac-detail-rows">
							<!-- Check-in -->
							<div class="ac-row">
								<div class="ac-row-icon ac-row-icon--in">
									<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/>
									</svg>
								</div>
								<div class="ac-row-info">
									<span class="ac-row-label">{{ __("Check In") }}</span>
									<span class="ac-row-time">{{ formatTime(dateDetail.in_time) }}</span>
									<span v-if="inAddress" class="ac-row-addr">📍 {{ inAddress }}</span>
									<span v-else-if="dateDetail.in_lat" class="ac-row-addr ac-row-addr--loading">{{ __("Locating…") }}</span>
								</div>
							</div>

							<!-- Check-out -->
							<div v-if="dateDetail.out_time" class="ac-row">
								<div class="ac-row-icon ac-row-icon--out">
									<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/>
									</svg>
								</div>
								<div class="ac-row-info">
									<span class="ac-row-label">{{ __("Check Out") }}</span>
									<span class="ac-row-time">{{ formatTime(dateDetail.out_time) }}</span>
									<span v-if="outAddress" class="ac-row-addr">📍 {{ outAddress }}</span>
									<span v-else-if="dateDetail.out_lat" class="ac-row-addr ac-row-addr--loading">{{ __("Locating…") }}</span>
								</div>
							</div>

							<div v-else class="ac-row">
								<div class="ac-row-icon ac-row-icon--pending">
									<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
									</svg>
								</div>
								<div class="ac-row-info">
									<span class="ac-row-label">{{ __("Check Out") }}</span>
									<span class="ac-row-time ac-row-time--muted">{{ __("Not checked out") }}</span>
								</div>
							</div>

							<!-- Duration -->
							<div v-if="duration" class="ac-duration">
								<svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
								</svg>
								<span>{{ __("Duration: {0}", [duration]) }}</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, ref, watch } from "vue"
import { createResource, call } from "frappe-ui"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))

const colorMap = {
	Present:        "bg-green-100 text-green-700",
	"Work From Home":"bg-violet-100 text-violet-700",
	"On Duty":      "bg-cyan-100 text-cyan-700",
	"Half Day":     "bg-yellow-100 text-yellow-700",
	Absent:         "bg-red-100 text-red-700",
	"On Leave":     "bg-blue-100 text-blue-700",
	Holiday:        "bg-gray-100 text-gray-600",
	Weekend:        "bg-orange-50 text-orange-400",
}

const cellColorMap = {
	Present:        "bg-green-300",
	"Work From Home":"bg-violet-300",
	"On Duty":      "bg-cyan-300",
	"Half Day":     "bg-yellow-200",
	Absent:         "bg-red-200",
	"On Leave":     "bg-blue-300",
	Holiday:        "bg-gray-300",
	Weekend:        "bg-orange-100",
}

const legendItems = [
	{ status: "Present",         label: __("Present"),   dotClass: "bg-green-400",   pillClass: "bg-green-50 border-green-200 text-green-700"   },
	{ status: "Work From Home",  label: __("WFH"),       dotClass: "bg-violet-400",  pillClass: "bg-violet-50 border-violet-200 text-violet-700" },
	{ status: "On Duty",         label: __("OD"),        dotClass: "bg-cyan-400",    pillClass: "bg-cyan-50 border-cyan-200 text-cyan-700"       },
	{ status: "Half Day",        label: __("Half Day"),  dotClass: "bg-yellow-400",  pillClass: "bg-yellow-50 border-yellow-200 text-yellow-700" },
	{ status: "Absent",          label: __("Absent"),    dotClass: "bg-red-400",     pillClass: "bg-red-50 border-red-200 text-red-700"          },
	{ status: "On Leave",        label: __("Leave"),     dotClass: "bg-blue-400",    pillClass: "bg-blue-50 border-blue-200 text-blue-700"       },
	{ status: "Holiday",         label: __("Holiday"),   dotClass: "bg-gray-400",    pillClass: "bg-gray-50 border-gray-200 text-gray-600"       },
	{ status: "Weekend",         label: __("Weekend"),   dotClass: "bg-orange-300",  pillClass: "bg-orange-50 border-orange-200 text-orange-500" },
]

const summary = computed(() => {
	const result = {}
	for (const status of Object.values(calendarEvents.data)) {
		result[status] = (result[status] || 0) + 1
	}
	const daysInMonth = firstOfMonth.value.endOf("M").get("D")
	let weekends = 0
	for (let i = 1; i <= daysInMonth; i++) {
		if (isWeekend(i)) weekends++
	}
	result["Weekend"] = weekends
	return result
})

watch(() => firstOfMonth.value, () => { calendarEvents.fetch() })

let refreshTimer = null
onMounted(() => {
	refreshTimer = setInterval(() => { calendarEvents.fetch() }, 30000)
})
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })

const getEventOnDate = (date) =>
	calendarEvents.data[firstOfMonth.value.date(date).format("YYYY-MM-DD")]

const getDayOfWeek = (index) => (firstOfMonth.value.get("d") + index - 1) % 7
const isWeekend = (index) => { const d = getDayOfWeek(index); return d === 0 || d === 6 }

const getCellClass = (index) => {
	const event = getEventOnDate(index)
	if (event) return cellColorMap[event]
	if (isWeekend(index)) return cellColorMap["Weekend"]
	return ""
}

const getFirstLetter = (s) => Array.from(s.trim())[0]
const DAYS = [
	getFirstLetter(__("Sunday")),
	getFirstLetter(__("Monday")),
	getFirstLetter(__("Tuesday")),
	getFirstLetter(__("Wednesday")),
	getFirstLetter(__("Thursday")),
	getFirstLetter(__("Friday")),
	getFirstLetter(__("Saturday")),
]

// ── Date click modal ──────────────────────────────────────────────────────
const showDateModal     = ref(false)
const selectedDay       = ref(null)
const dateDetail        = ref(null)
const dateDetailLoading = ref(false)
const inAddress         = ref("")
const outAddress        = ref("")

const selectedDate = computed(() =>
	selectedDay.value ? firstOfMonth.value.date(selectedDay.value) : null
)
const selectedDateFormatted = computed(() =>
	selectedDate.value ? selectedDate.value.format("dddd, D MMMM YYYY") : ""
)
const selectedStatus = computed(() =>
	selectedDay.value ? (getEventOnDate(selectedDay.value) || (isWeekend(selectedDay.value) ? "Weekend" : null)) : null
)
const isSelectedWeekend = computed(() =>
	selectedDay.value ? isWeekend(selectedDay.value) : false
)

const duration = computed(() => {
	if (!dateDetail.value?.in_time || !dateDetail.value?.out_time) return ""
	const inMs  = new Date(dateDetail.value.in_time.replace(" ", "T")).getTime()
	const outMs = new Date(dateDetail.value.out_time.replace(" ", "T")).getTime()
	const diff  = Math.max(0, Math.floor((outMs - inMs) / 1000))
	const hh = String(Math.floor(diff / 3600)).padStart(2, "0")
	const mm = String(Math.floor((diff % 3600) / 60)).padStart(2, "0")
	return `${hh}h ${mm}m`
})

function formatTime(dt) {
	if (!dt) return "—"
	return dayjs(dt.replace(" ", "T")).format("hh:mm A")
}

async function reverseGeocode(lat, lng) {
	if (!lat || !lng || lat == 0 || lng == 0) return ""
	try {
		const res = await fetch(
			`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
			{ headers: { "Accept-Language": "en" } }
		)
		const data = await res.json()
		const a = data.address || {}
		// Short form: suburb / neighbourhood / city_district, city/town/village
		const area = a.suburb || a.neighbourhood || a.city_district || a.residential || ""
		const city = a.city || a.town || a.village || a.county || ""
		return [area, city].filter(Boolean).join(", ") || data.display_name?.split(",")[0] || ""
	} catch {
		return ""
	}
}

async function onDateClick(index) {
	selectedDay.value  = index
	showDateModal.value = true
	dateDetail.value   = null
	inAddress.value    = ""
	outAddress.value   = ""

	// Skip API for weekends with no event and holidays
	const status = getEventOnDate(index)
	const weekend = isWeekend(index)
	if (weekend && !status) return
	if (status === "Holiday") return

	dateDetailLoading.value = true
	try {
		const dateStr = firstOfMonth.value.date(index).format("YYYY-MM-DD")
		const data = await call("hrms.api.get_employee_checkins_on_date", { date: dateStr })
		dateDetail.value = data || {}

		// Reverse geocode in parallel
		if (data?.in_lat) {
			reverseGeocode(data.in_lat, data.in_lng).then(addr => { inAddress.value = addr })
		}
		if (data?.out_lat) {
			reverseGeocode(data.out_lat, data.out_lng).then(addr => { outAddress.value = addr })
		}
	} catch {
		dateDetail.value = {}
	} finally {
		dateDetailLoading.value = false
	}
}

function closeDateModal() {
	showDateModal.value = false
	selectedDay.value   = null
	dateDetail.value    = null
	inAddress.value     = ""
	outAddress.value    = ""
}

const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: () => `hrms:attendance_calendar_events:${firstOfMonth.value.format("YYYY-MM")}`,
	makeParams() {
		return {
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date:   firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>

<style scoped>
/* ── Bottom sheet overlay ─────────────────────────────────────────────── */
.ac-overlay {
	position: fixed;
	inset: 0;
	z-index: 9999;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
}
.ac-backdrop {
	position: absolute;
	inset: 0;
	background: rgba(0,0,0,0.4);
}
.ac-sheet {
	position: relative;
	background: #fff;
	border-radius: 20px 20px 0 0;
	max-height: 80vh;
	display: flex;
	flex-direction: column;
	box-shadow: 0 -4px 24px rgba(0,0,0,0.12);
	animation: ac-slide-up 0.26s cubic-bezier(0.32,0.72,0,1);
}
@keyframes ac-slide-up {
	from { transform: translateY(100%); }
	to   { transform: translateY(0); }
}
.ac-handle-row { display:flex; justify-content:center; padding:12px 0 4px; }
.ac-handle { width:36px; height:4px; border-radius:99px; background:#d1d5db; }

/* Header */
.ac-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 16px 12px;
	border-bottom: 1px solid #f3f4f6;
}
.ac-date-title { font-size:1rem; font-weight:600; color:#111827; }
.ac-close {
	display:flex; align-items:center; justify-content:center;
	width:30px; height:30px; border-radius:50%; border:none;
	background:transparent; cursor:pointer;
}
.ac-close:active { background:#f3f4f6; }

/* Status badge */
.ac-status-row { padding: 10px 16px 0; }
.ac-status-pill {
	display: inline-block;
	padding: 3px 12px;
	border-radius: 99px;
	font-size: 0.75rem;
	font-weight: 600;
}

/* Body */
.ac-body { padding: 12px 16px 28px; overflow-y: auto; flex:1; }

/* Empty / holiday states */
.ac-empty, .ac-holiday-block {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 8px;
	padding: 24px 0;
}
.ac-holiday-label { font-size:1rem; font-weight:600; color:#374151; }

/* Loading skeleton */
.ac-loading { display:flex; flex-direction:column; gap:12px; padding: 8px 0; }
.ac-skeleton {
	height:48px; border-radius:10px; background:#f3f4f6;
	animation: shimmer 1.2s ease-in-out infinite;
}
@keyframes shimmer { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* Detail rows */
.ac-detail-rows { display:flex; flex-direction:column; gap:12px; }
.ac-row {
	display:flex; align-items:flex-start; gap:12px;
	background:#f9fafb; border-radius:12px; padding:12px;
}
.ac-row-icon {
	width:32px; height:32px; border-radius:50%; display:flex;
	align-items:center; justify-content:center; flex-shrink:0;
}
.ac-row-icon--in      { background:#dcfce7; color:#16a34a; }
.ac-row-icon--out     { background:#fee2e2; color:#dc2626; }
.ac-row-icon--pending { background:#f3f4f6; color:#9ca3af; }

.ac-row-info { display:flex; flex-direction:column; gap:2px; min-width:0; }
.ac-row-label { font-size:0.75rem; color:#6b7280; font-weight:500; }
.ac-row-time  { font-size:1rem; font-weight:700; color:#111827; }
.ac-row-time--muted { color:#9ca3af; font-size:0.875rem; font-weight:500; }
.ac-row-addr  { font-size:0.75rem; color:#6b7280; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ac-row-addr--loading { color:#d1d5db; }

.ac-duration {
	display:flex; align-items:center; gap:6px;
	font-size:0.8125rem; color:#6b7280; padding: 4px 0 0 4px;
}
</style>
