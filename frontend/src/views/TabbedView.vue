<template>
	<ion-page>
		<!-- Desktop sidebar (lg+) -->
		<DesktopSidebar />

		<!-- Content shifts right on desktop to clear sidebar -->
		<div class="lg:pl-56 h-full">
			<ion-tabs>
				<ion-router-outlet></ion-router-outlet>
				<!-- Bottom tabs: mobile only -->
				<BottomTabs class="lg:hidden" />
			</ion-tabs>
		</div>
	</ion-page>
</template>

<script setup>
import { IonTabs, IonPage, IonRouterOutlet } from "@ionic/vue"
import BottomTabs from "@/components/BottomTabs.vue"
import DesktopSidebar from "@/components/DesktopSidebar.vue"
</script>
