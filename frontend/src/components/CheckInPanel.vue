<template>
	<div class="flex flex-col bg-white rounded-xl w-full py-5 px-4 shadow-sm border border-gray-100">

		<!-- Header -->
		<div class="flex items-start justify-between">
			<div>
				<h2 class="text-lg font-bold text-gray-900">
					{{ __("Hey, {0} 👋", [employee?.data?.first_name]) }}
				</h2>
				<div class="text-xs text-gray-400 mt-0.5">
					{{ dayjs().format("ddd, D MMMM YYYY") }}
				</div>
			</div>
			<router-link
				v-if="settings.data?.allow_employee_checkin_from_mobile_app"
				:to="{ name: 'EmployeeCheckinListView' }"
			>
				<FeatherIcon name="list" class="w-4 h-4 text-gray-400 mt-1" />
			</router-link>
		</div>

		<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">

			<!-- Status + Timer card -->
			<div
				class="mt-4 rounded-xl px-4 py-4 flex flex-col items-center gap-2 transition-colors duration-300"
				:class="cardBgClass"
			>
				<!-- Status badge -->
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-2.5 h-2.5 rounded-full"
						:class="[dotClass, isCheckedIn ? 'animate-pulse' : '']"
					></span>
					<span class="text-xs font-semibold tracking-wide uppercase" :class="statusTextClass">
						{{ statusLabel }}
					</span>
				</div>

				<!-- Sub-label -->
				<div class="text-xs text-gray-400 -mt-0.5" v-if="firstCheckinTime">
					{{
						isCheckedIn
							? __("since {0}", [dayjs(firstCheckinTime.replace(" ", "T")).format("hh:mm A")])
							: __("total today")
					}}
				</div>

				<!-- Timer digits -->
				<div class="flex items-end gap-0.5 mt-2">
					<template v-if="firstCheckinTime">
						<div class="flex flex-col items-center w-12">
							<span class="font-mono text-4xl font-extrabold leading-none" :class="digitClass">
								{{ timerParts.hh }}
							</span>
							<span class="text-[9px] font-medium text-gray-400 mt-1 tracking-widest uppercase">hr</span>
						</div>
						<span class="font-mono text-3xl font-extrabold mb-4 mx-0.5" :class="digitClass">:</span>
						<div class="flex flex-col items-center w-12">
							<span class="font-mono text-4xl font-extrabold leading-none" :class="digitClass">
								{{ timerParts.mm }}
							</span>
							<span class="text-[9px] font-medium text-gray-400 mt-1 tracking-widest uppercase">min</span>
						</div>
						<span class="font-mono text-3xl font-extrabold mb-4 mx-0.5" :class="digitClass">:</span>
						<div class="flex flex-col items-center w-12">
							<span class="font-mono text-4xl font-extrabold leading-none" :class="digitClass">
								{{ timerParts.ss }}
							</span>
							<span class="text-[9px] font-medium text-gray-400 mt-1 tracking-widest uppercase">sec</span>
						</div>
					</template>
					<template v-else>
						<span class="font-mono text-4xl font-extrabold text-gray-300 leading-none tracking-widest">
							--:--:--
						</span>
					</template>
				</div>
			</div>

			<!-- Check-in / Check-out button -->
			<Button
				class="mt-4 mb-1 drop-shadow-sm py-5 text-base"
				@click="openCheckinModal"
			>
				<template #prefix>
					<FeatherIcon
						:name="nextAction.action === 'IN' ? 'arrow-right-circle' : 'arrow-left-circle'"
						class="w-4"
					/>
				</template>
				{{ nextAction.label }}
			</Button>
		</template>

		<div v-else class="font-medium text-sm text-gray-500 mt-1.5">
			{{ dayjs().format("ddd, D MMMM, YYYY") }}
		</div>
	</div>

	<!-- Confirmation modal — works on both mobile (sheet) and desktop -->
	<ion-modal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		ref="modal"
		:is-open="showModal"
		@didDismiss="showModal = false"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="h-120 w-full flex flex-col items-center justify-center gap-5 p-4 mb-5">
			<div class="flex flex-col gap-1.5 mt-2 items-center justify-center">
				<div class="font-bold text-xl">
					{{ dayjs(checkinTimestamp).format("hh:mm:ss a") }}
				</div>
				<div class="font-medium text-gray-500 text-sm">
					{{ dayjs().format("D MMM, YYYY") }}
				</div>
			</div>

			<template v-if="settings.data?.allow_geolocation_tracking">
				<span v-if="locationStatus" class="font-medium text-gray-500 text-sm">
					{{ locationStatus }}
				</span>
				<div class="rounded border-4 translate-z-0 block overflow-hidden w-full h-170">
					<iframe
						width="100%"
						height="170"
						frameborder="0"
						scrolling="no"
						marginheight="0"
						marginwidth="0"
						style="border: 0"
						:src="`https://maps.google.com/maps?q=${latitude},${longitude}&hl=en&z=15&amp;output=embed`"
					></iframe>
				</div>
			</template>

			<Button
				:loading="checkins.insert.loading"
				variant="solid"
				class="w-full py-5 text-sm disabled:bg-gray-700"
				@click="submitLog(nextAction.action)"
			>
				{{ __("Confirm {0}", [nextAction.label]) }}
			</Button>
		</div>
	</ion-modal>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, ref, watch, onMounted, onBeforeUnmount } from "vue"
import { IonModal, modalController } from "@ionic/vue"
import { formatTimestamp } from "@/utils/formatters"

const DOCTYPE = "Employee Checkin"

const socket   = inject("$socket")
const employee = inject("$employee")
const dayjs    = inject("$dayjs")
const __       = inject("$translate")

const checkinTimestamp = ref(null)
const latitude         = ref(0)
const longitude        = ref(0)
const locationStatus   = ref("")
const showModal        = ref(false)

const settings = createResource({ url: "hrms.api.get_hr_settings", auto: true })

// ── Checkin status — fetched from server (same calculation as VGTS dashboard) ──
// This is the single source of truth for timer and button state.
const checkinStatus = createResource({
	url: "vgts.api.get_checkin_status",
	auto: true,
})

const isCheckedIn      = computed(() => checkinStatus.data?.is_checked_in      ?? false)
const checkedInSeconds = computed(() => checkinStatus.data?.checked_in_seconds ?? 0)
const lastCheckinTime  = computed(() => checkinStatus.data?.last_checkin_time  ?? null)
const firstCheckinTime = computed(() => checkinStatus.data?.first_checkin_time ?? null)

const nextAction = computed(() =>
	isCheckedIn.value
		? { action: "OUT", label: __("Check Out") }
		: { action: "IN",  label: __("Check In") }
)

// ── UI state ─────────────────────────────────────────────────────────────

const cardBgClass = computed(() => {
	if (!firstCheckinTime.value) return "bg-gray-50 border border-gray-100"
	return isCheckedIn.value ? "bg-green-50 border border-green-100" : "bg-gray-50 border border-gray-100"
})
const dotClass = computed(() => {
	if (!firstCheckinTime.value) return "bg-gray-300"
	return isCheckedIn.value ? "bg-green-500" : "bg-gray-400"
})
const statusTextClass = computed(() => {
	if (!firstCheckinTime.value) return "text-gray-400"
	return isCheckedIn.value ? "text-green-600" : "text-gray-500"
})
const digitClass = computed(() => {
	if (!firstCheckinTime.value) return "text-gray-300"
	return isCheckedIn.value ? "text-green-700" : "text-gray-600"
})
const statusLabel = computed(() => {
	if (!firstCheckinTime.value) return __("Not Checked In")
	return isCheckedIn.value ? __("Checked In") : __("Checked Out")
})

// ── Timer ─────────────────────────────────────────────────────────────────
// live   = checked_in_seconds (completed pairs) + (now − last_checkin_time)
// static = checked_in_seconds

const timerSeconds  = ref(0)
const timerInterval = ref(null)

function stopTimer() {
	if (timerInterval.value) {
		clearInterval(timerInterval.value)
		timerInterval.value = null
	}
}

function startTimer() {
	stopTimer()
	const base   = checkedInSeconds.value
	const lastIn = lastCheckinTime.value

	if (!base && !lastIn) {
		timerSeconds.value = 0
		return
	}

	if (isCheckedIn.value && lastIn) {
		const lastInMs = new Date(lastIn.replace(" ", "T")).getTime()
		const tick = () => {
			timerSeconds.value = base + Math.max(0, Math.floor((Date.now() - lastInMs) / 1000))
		}
		tick()
		timerInterval.value = setInterval(tick, 1000)
	} else {
		timerSeconds.value = base
	}
}

const timerParts = computed(() => {
	const s = timerSeconds.value
	return {
		hh: String(Math.floor(s / 3600)).padStart(2, "0"),
		mm: String(Math.floor((s % 3600) / 60)).padStart(2, "0"),
		ss: String(s % 60).padStart(2, "0"),
	}
})

// Restart timer whenever server data changes
watch(() => checkinStatus.data, () => startTimer(), { deep: true })

// ── List resource — only used for insert (submit action) ─────────────────
const checkins = createListResource({
	doctype: DOCTYPE,
	fields:  ["name", "log_type", "time"],
	filters: { employee: employee.data.name },
	orderBy: "time desc",
	pageLength: 1,
})

// ── Real-time sync ────────────────────────────────────────────────────────

function refreshStatus() {
	checkinStatus.reload()
}

// Reload when tab becomes visible (user switches back from dashboard)
function onVisibilityChange() {
	if (!document.hidden) refreshStatus()
}

// 5-second polling — catches any missed socket events quickly
const pollInterval = ref(null)

// ── Geolocation ───────────────────────────────────────────────────────────

function handleLocationSuccess(pos) {
	latitude.value  = pos.coords.latitude
	longitude.value = pos.coords.longitude
	locationStatus.value = [
		__("Latitude: {0}°",  [Number(latitude.value).toFixed(5)]),
		__("Longitude: {0}°", [Number(longitude.value).toFixed(5)]),
	].join(", ")
}
function handleLocationError(err) {
	locationStatus.value = "Unable to retrieve your location"
	if (err) locationStatus.value += `: ERROR(${err.code}): ${err.message}`
}
const fetchLocation = () => {
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
	} else {
		locationStatus.value = __("Locating...")
		navigator.geolocation.getCurrentPosition(handleLocationSuccess, handleLocationError)
	}
}

// ── Actions ───────────────────────────────────────────────────────────────

const openCheckinModal = () => {
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")
	if (settings.data?.allow_geolocation_tracking) fetchLocation()
	showModal.value = true
}

const submitLog = (logType) => {
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")
	checkins.insert.submit(
		{
			employee:  employee.data.name,
			log_type:  logType,
			time:      checkinTimestamp.value,
			latitude:  latitude.value,
			longitude: longitude.value,
		},
		{
			onSuccess() {
				showModal.value = false
				// Immediately refresh status so timer and button update at once
				refreshStatus()
				toast({
					title: __("Success"),
					text:  __("{0} successful!", [actionLabel]),
					icon:  "check-circle",
					position:    "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError(error) {
				for (const message of (error.messages || [])) {
					toast({
						title: __("Error"),
						text:  message || __("{0} failed!", [actionLabel]),
						icon:  "alert-circle",
						position:    "bottom-center",
						iconClasses: "text-red-500",
					})
				}
			},
		}
	)
}

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(() => {
	// Socket: instant update when any Employee Checkin record changes
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype === DOCTYPE) refreshStatus()
	})

	// Visibility: refresh when user comes back to this tab/app
	document.addEventListener("visibilitychange", onVisibilityChange)

	// Polling: 5-second fallback for missed socket events
	pollInterval.value = setInterval(refreshStatus, 5000)

	startTimer()
})

onBeforeUnmount(() => {
	stopTimer()
	clearInterval(pollInterval.value)
	document.removeEventListener("visibilitychange", onVisibilityChange)
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
})
</script>
