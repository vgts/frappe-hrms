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

// Initialize theme from localStorage / system preference
useTheme()

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
