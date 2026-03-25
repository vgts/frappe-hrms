<template>
	<div class="flex flex-col bg-white rounded w-full py-6 px-4 border-none">
		<h2 class="text-lg font-bold text-gray-900">
			{{ __("Hey, {0} 👋", [employee?.data?.first_name]) }}
		</h2>

		<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">
			<div class="font-medium text-sm text-gray-500 mt-1.5" v-if="lastLog">
				<span>{{ __("Last {0} was at {1}", [__(lastLogType), formatTimestamp(lastLog.time)]) }}</span>
				<span class="whitespace-pre"> &middot; </span>
				<router-link :to="{ name: 'EmployeeCheckinListView' }" v-slot="{ navigate }">
					<span @click="navigate" class="underline">View List</span>
				</router-link>
			</div>

			<!-- Timer display -->
			<div v-if="firstCheckinTime" class="mt-3 mb-1 flex flex-col items-center gap-1">
				<div class="font-mono text-3xl font-bold text-gray-800 tracking-widest">
					{{ timerDisplay }}
				</div>
				<div class="text-xs text-gray-400">
					{{ isCheckedIn ? __("Time elapsed since check-in") : __("Total time worked today") }}
				</div>
			</div>

			<Button
				class="mt-4 mb-1 drop-shadow-sm py-5 text-base"
				id="open-checkin-modal"
				@click="handleEmployeeCheckin"
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

	<ion-modal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		ref="modal"
		trigger="open-checkin-modal"
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
					>
					</iframe>
				</div>
			</template>

			<Button :loading="checkins.insert.loading" variant="solid" class="w-full py-5 text-sm disabled:bg-gray-700" @click="submitLog(nextAction.action)">
				{{ __("Confirm {0}", [nextAction.label]) }}
			</Button>
		</div>
	</ion-modal>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, ref, onMounted, onBeforeUnmount, watch } from "vue"
import { IonModal, modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"

const DOCTYPE = "Employee Checkin"

const socket = inject("$socket")
const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const checkinTimestamp = ref(null)
const latitude = ref(0)
const longitude = ref(0)
const locationStatus = ref("")
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

// Filter to today's logs only — sufficient for button state and timer
// pageLength 50 handles any realistic number of daily swipes
const todayStart = dayjs().format("YYYY-MM-DD") + " 00:00:00"

const checkins = createListResource({
	doctype: DOCTYPE,
	fields: ["name", "employee", "employee_name", "log_type", "time", "device_id"],
	filters: {
		employee: employee.data.name,
		time: [">=", todayStart],
	},
	orderBy: "time desc",
	pageLength: 50,
})
checkins.reload()

const lastLog = computed(() => {
	if (checkins.list.loading || !checkins.data) return {}
	return checkins.data[0]
})

const lastLogType = computed(() => {
	return lastLog?.value?.log_type === "IN" ? "check-in" : "check-out"
})

const nextAction = computed(() => {
	return lastLog?.value?.log_type === "IN"
		? { action: "OUT", label: __("Check Out") }
		: { action: "IN", label: __("Check In") }
})

// ── Timer computeds (mirrors VGTS dashboard calculation exactly) ─────────

// Earliest IN today — timer start anchor
const firstCheckinTime = computed(() => {
	if (!checkins.data) return null
	const inLogs = checkins.data.filter(l => l.log_type === "IN")
	if (!inLogs.length) return null
	// data is desc order → last element is earliest
	return inLogs[inLogs.length - 1].time
})

// Latest OUT today
const lastCheckoutTime = computed(() => {
	if (!checkins.data) return null
	const outLogs = checkins.data.filter(l => l.log_type === "OUT")
	if (!outLogs.length) return null
	// data is desc order → first element is latest
	return outLogs[0].time
})

// Same string-comparison logic as api.py is_checked_in
const isCheckedIn = computed(() => {
	if (!checkins.data) return false
	const latestInLog = checkins.data.find(l => l.log_type === "IN")
	const lastInStr  = latestInLog?.time  || ""
	const lastOutStr = lastCheckoutTime.value || ""
	return Boolean(lastInStr) && (!lastOutStr || lastInStr > lastOutStr)
})

// ── Timer tick ───────────────────────────────────────────────────────────

const timerSeconds = ref(0)
const timerInterval = ref(null)

function stopTimer() {
	if (timerInterval.value) {
		clearInterval(timerInterval.value)
		timerInterval.value = null
	}
}

function startTimer() {
	stopTimer()
	if (!firstCheckinTime.value) return

	const start = new Date(firstCheckinTime.value.replace(" ", "T"))

	if (isCheckedIn.value) {
		// Live counter: elapsed since first check-in today
		const tick = () => {
			timerSeconds.value = Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000))
		}
		tick()
		timerInterval.value = setInterval(tick, 1000)
	} else if (lastCheckoutTime.value) {
		// Static total: last checkout − first check-in
		const end = new Date(lastCheckoutTime.value.replace(" ", "T"))
		timerSeconds.value = Math.max(0, Math.floor((end.getTime() - start.getTime()) / 1000))
	}
}

const timerDisplay = computed(() => {
	const s = timerSeconds.value
	const hh = String(Math.floor(s / 3600)).padStart(2, "0")
	const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0")
	const ss = String(s % 60).padStart(2, "0")
	return `${hh}:${mm}:${ss}`
})

// Restart timer whenever checkin state changes (socket reload updates checkins.data)
watch([isCheckedIn, firstCheckinTime], () => {
	startTimer()
})

// ── Geolocation ──────────────────────────────────────────────────────────

function handleLocationSuccess(position) {
	latitude.value = position.coords.latitude
	longitude.value = position.coords.longitude

	locationStatus.value = [
		__("Latitude: {0}°", [Number(latitude.value).toFixed(5)]),
		__("Longitude: {0}°", [Number(longitude.value).toFixed(5)]),
	].join(", ")
}

function handleLocationError(error) {
	locationStatus.value = "Unable to retrieve your location"
	if (error) locationStatus.value += `: ERROR(${error.code}): ${error.message}`
}

const fetchLocation = () => {
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
	} else {
		locationStatus.value = __("Locating...")
		navigator.geolocation.getCurrentPosition(handleLocationSuccess, handleLocationError)
	}
}

const handleEmployeeCheckin = () => {
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")

	if (settings.data?.allow_geolocation_tracking) {
		fetchLocation()
	}
}

const submitLog = (logType) => {
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")

	checkins.insert.submit(
		{
			employee: employee.data.name,
			log_type: logType,
			time: checkinTimestamp.value,
			latitude: latitude.value,
			longitude: longitude.value,
		},
		{
			onSuccess() {
				modalController.dismiss()
				toast({
					title: __("Success"),
					text: __("{0} successful!", [actionLabel]),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError(error) {
				let messages = error.messages || []

				for (const message of messages) {
					toast({
						title: __("Error"),
						text: message || __("{0} failed!", [actionLabel]),
						icon: "alert-circle",
						position: "bottom-center",
						iconClasses: "text-red-500",
					})
				}
			},
		}
	)
}

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype == DOCTYPE) {
			checkins.reload()
		}
	})
	startTimer()
})

onBeforeUnmount(() => {
	stopTimer()
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
})
</script>
