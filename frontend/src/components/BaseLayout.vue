<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full sm:w-96">
				<div
					class="flex flex-col shadow-sm p-4 transition-colors duration-200"
					:class="isDark() ? 'bg-gray-800' : 'bg-white'"
				>
					<div class="flex flex-row justify-between items-center">
						<div class="flex flex-row items-center gap-2">
							<h2
								class="text-xl font-bold transition-colors duration-200"
								:class="isDark() ? 'text-gray-50' : 'text-gray-900'"
							>
								{{ props.pageTitle || __("Frappe HR") }}
							</h2>
						</div>
						<div class="flex flex-row items-center gap-3 ml-auto">
							<!-- Theme toggle: moon = switch to dark, sun = switch to light -->
							<button
								@click="toggleTheme"
								class="flex items-center justify-center w-8 h-8 rounded-full transition-colors duration-200 focus:outline-none"
								:class="isDark() ? 'text-yellow-300 hover:bg-gray-700' : 'text-gray-500 hover:bg-gray-100'"
								:aria-label="isDark() ? __('Switch to light mode') : __('Switch to dark mode')"
							>
								<FeatherIcon
									:name="isDark() ? 'sun' : 'moon'"
									class="h-5 w-5"
								/>
							</button>

							<!-- Bell / Notifications -->
							<router-link
								:to="{ name: 'Notifications' }"
								v-slot="{ navigate }"
								class="flex flex-col items-center"
							>
								<span class="relative inline-block" @click="navigate">
									<FeatherIcon
										name="bell"
										class="h-6 w-6 transition-colors duration-200"
										:class="isDark() ? 'text-gray-200' : ''"
									/>
									<span
										v-if="unreadNotificationsCount.data"
										class="absolute top-0 right-0.5 inline-block w-2 h-2 bg-red-600 rounded-full"
										:class="isDark() ? 'border-gray-800' : 'border-white'"
										style="border-width: 1px; border-style: solid;"
									>
									</span>
								</span>
							</router-link>

							<!-- User avatar -->
							<router-link
								:to="{ name: 'Profile' }"
								class="flex flex-col items-center"
							>
								<Avatar
									:image="user.data.user_image"
									:label="user.data.first_name"
									size="xl"
								/>
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
			<div class="flex flex-col h-screen w-screen sm:w-96">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonHeader, IonContent, IonPage, IonRefresher, IonRefresherContent } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"
import { useTheme } from "@/composables/useTheme"

import { inject } from "vue"

const user = inject("$user")
const __ = inject("$translate")

const { isDark, toggle: toggleTheme } = useTheme()

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
