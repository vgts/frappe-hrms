<template>
	<ion-app>
		<ion-router-outlet id="main-content" />
		<Toasts />

		<InstallPrompt />
	</ion-app>
</template>

<script setup>
import { onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { Toasts } from "frappe-ui"

import InstallPrompt from "@/components/InstallPrompt.vue"
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
