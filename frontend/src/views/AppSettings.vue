<template>
	<ion-page>
		<ion-content>
			<div class="flex flex-col min-h-screen bg-gray-50">

				<!-- Header -->
				<header class="flex flex-row bg-white shadow-sm py-4 px-4 lg:px-10 items-center border-b sticky top-0 z-10">
					<Button variant="ghost" class="!pl-0 hover:bg-white" @click="router.back()">
						<FeatherIcon name="chevron-left" class="h-5 w-5" />
					</Button>
					<h2 class="text-xl font-semibold text-gray-900">{{ __("Settings") }}</h2>
				</header>

				<!-- Content -->
				<div class="flex flex-col gap-6 p-4 lg:px-10 lg:py-8 lg:max-w-2xl lg:mx-auto w-full">

					<!-- Notifications Section -->
					<div class="flex flex-col gap-3">
						<div class="text-xs font-semibold text-gray-400 uppercase tracking-wide px-1">
							{{ __("Notifications") }}
						</div>
						<div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
							<div class="flex items-center justify-between px-4 py-4">
								<div class="flex flex-col gap-0.5">
									<span class="text-sm font-medium text-gray-800">{{ __("Push Notifications") }}</span>
									<span v-if="description" class="text-xs text-gray-400">{{ description }}</span>
									<span v-else class="text-xs text-gray-400">{{ __("Receive alerts on your device") }}</span>
								</div>
								<Switch
									size="md"
									:model-value="pushNotificationState"
									:disabled="disablePushSetting"
									@update:model-value="togglePushNotifications"
								/>
							</div>
							<!-- Loading -->
							<div v-if="isLoading" class="flex items-center gap-2 px-4 pb-3">
								<LoadingIndicator class="w-3 h-3 text-gray-500" />
								<span class="text-xs text-gray-500">
									{{ pushNotificationState ? __("Disabling...") : __("Enabling...") }}
								</span>
							</div>
						</div>
					</div>

				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import { FeatherIcon, Switch, toast, LoadingIndicator } from "frappe-ui"
import { computed, inject, ref } from "vue"
import { arePushNotificationsEnabled } from "@/data/notifications"

const __ = inject("$translate")
const router = useRouter()
const pushNotificationState = ref(window.frappePushNotification?.isNotificationEnabled())
const isLoading = ref(false)

const disablePushSetting = computed(() => {
	return (
		!(window.frappe?.boot.push_relay_server_url && arePushNotificationsEnabled.data)
		|| isLoading.value
	)
})

const description = computed(() => {
	return !(window.frappe?.boot.push_relay_server_url && arePushNotificationsEnabled.data)
		? __("Push notifications have been disabled on your site")
		: ""
})

const togglePushNotifications = (newValue) => {
	if (newValue) {
		enablePushNotifications()
	} else {
		isLoading.value = true
		window.frappePushNotification
			.disableNotification()
			.then(() => {
				pushNotificationState.value = false
				toast({ title: __("Success"), text: __("Push notifications disabled"), icon: "check-circle", position: "bottom-center", iconClasses: "text-green-500" })
			})
			.catch((error) => {
				toast({ title: __("Error"), text: __(error.message), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			})
			.finally(() => { isLoading.value = false })
	}
}

const enablePushNotifications = () => {
	isLoading.value = true
	window.frappePushNotification
		.enableNotification()
		.then((data) => {
			if (data.permission_granted) {
				pushNotificationState.value = true
			} else {
				toast({ title: __("Error"), text: __("Push Notification permission denied"), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
				pushNotificationState.value = false
			}
		})
		.catch((error) => {
			toast({ title: __("Error"), text: __(error.message), icon: "alert-circle", position: "bottom-center", iconClasses: "text-red-500" })
			pushNotificationState.value = false
		})
		.finally(() => { isLoading.value = false })
}
</script>
