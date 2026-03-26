<template>
	<ion-page>
		<DesktopSidebar />
		<ion-tabs>
			<ion-router-outlet></ion-router-outlet>
			<BottomTabs class="lg:hidden" />
		</ion-tabs>
	</ion-page>
</template>

<script setup>
import { IonTabs, IonPage, IonRouterOutlet } from "@ionic/vue"
import BottomTabs from "@/components/BottomTabs.vue"
import DesktopSidebar from "@/components/DesktopSidebar.vue"
</script>
