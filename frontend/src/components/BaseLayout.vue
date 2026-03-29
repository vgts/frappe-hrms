<template>
	<ion-page>
		<!-- Desktop sidebar — fixed position, only visible on lg+ -->
		<DesktopSidebar />

		<ion-header class="ion-no-border">
			<div class="w-full">
				<div class="flex flex-col shadow-sm p-4 bg-white">
					<div class="flex flex-row justify-between items-center">
						<div class="flex flex-row items-center gap-2">
							<h2 class="text-xl font-bold text-gray-900">
								{{ props.pageTitle || __("VGTS-HRMS") }}
							</h2>
						</div>
						<div class="flex flex-row items-center gap-3 ml-auto">
							<!-- Bell / Notifications — mobile only (sidebar has it on desktop) -->
							<router-link
								:to="{ name: 'Notifications' }"
								v-slot="{ navigate }"
								class="flex flex-col items-center lg:hidden"
							>
								<span class="relative inline-block" @click="navigate">
									<FeatherIcon name="bell" class="h-6 w-6" />
									<span
										v-if="unreadNotificationsCount.data"
										class="absolute top-0 right-0.5 inline-block w-2 h-2 bg-red-600 rounded-full border border-white"
										style="border-width: 1px; border-style: solid;"
									></span>
								</span>
							</router-link>

							<!-- User avatar — mobile only (sidebar has it on desktop) -->
							<router-link
								:to="{ name: 'Profile' }"
								class="flex flex-col items-center lg:hidden"
							>
								<Avatar :image="user.data.user_image" :label="user.data.first_name" size="xl" />
							</router-link>
						</div>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding">
			<ion-refresher slot="fixed" @ionRefresh="handleRefresh">
				<ion-refresher-content></ion-refresher-content>
			</ion-refresher>
			<div class="flex flex-col min-h-full w-full lg:pl-56">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonHeader, IonContent, IonPage, IonRefresher, IonRefresherContent } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"
import DesktopSidebar from "@/components/DesktopSidebar.vue"

import { inject } from "vue"

const user = inject("$user")
const __ = inject("$translate")

const emit = defineEmits(["refresh"])

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})

async function handleRefresh(event) {
	emit("refresh")
	setTimeout(() => {
		event.target.complete()
	}, 1500)
}
</script>
