<template>
	<ion-app>
		<SplashScreen />
		<ion-router-outlet id="main-content" />
		<Toasts />
		<DesktopFormModal />
		<InstallPrompt />
	</ion-app>
</template>

<script setup>
import { onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { Toasts } from "frappe-ui"

import InstallPrompt from "@/components/InstallPrompt.vue"
import SplashScreen from "@/components/SplashScreen.vue"
import DesktopFormModal from "@/components/DesktopFormModal.vue"
import { showNotification } from "@/utils/pushNotifications"
import { useTheme } from "@/composables/useTheme"
import { notifications, unreadNotificationsCount } from "@/data/notifications"

// Initialize theme from localStorage / system preference
useTheme()

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		// Show OS notification while app is in the foreground
		showNotification(payload)
		// Also refresh in-app notification list and badge immediately
		unreadNotificationsCount.reload()
		if (notifications.data) {
			notifications.reload()
		}
	})
})
</script>
