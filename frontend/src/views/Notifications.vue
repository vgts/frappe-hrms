<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-full">
				<div class="w-full">
					<header
						class="flex flex-row bg-white shadow-sm py-4 px-3 lg:px-10 items-center justify-between border-b sticky top-0 z-10"
					>
						<div class="flex flex-row items-center">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-white"
								@click="router.back()"
							>
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</Button>
							<h2 class="text-xl font-semibold text-gray-900">{{ __("Notifications") }}</h2>
						</div>
					</header>

					<div class="flex flex-col gap-4 mt-5 p-4 lg:px-10 lg:py-8 lg:max-w-3xl lg:mx-auto">
						<!-- Top bar: unread count + action buttons -->
						<div class="flex flex-row justify-between items-center">
							<div
								class="text-lg text-gray-800 font-semibold"
								v-if="unreadNotificationsCount.data"
							>
								{{ __("{0} Unread", [unreadNotificationsCount.data]) }}
							</div>
							<div class="flex ml-auto gap-1">
								<Button
									v-if="allowPushNotifications"
									variant="outline"
									@click="router.push({ name: 'Settings' })"
								>
									<template #prefix>
										<FeatherIcon name="settings" class="w-4" />
									</template>
									{{ __("Settings") }}
								</Button>
								<Button
									v-if="unreadNotificationsCount.data > 0"
									variant="outline"
									@click="markAllAsRead.submit()"
									:loading="markAllAsRead.loading"
								>
									<template #prefix>
										<FeatherIcon name="check-circle" class="w-4" />
									</template>
									{{ __("Mark all as read") }}
								</Button>
							</div>
						</div>

						<!-- Initial loading skeleton -->
						<div v-if="notifications.loading && !notifications.data?.length" class="flex flex-col gap-3">
							<div v-for="n in 5" :key="n" class="flex items-center gap-3 p-4 bg-white rounded border border-gray-100">
								<div class="w-2 h-2 rounded-full bg-gray-200 shrink-0"></div>
								<div class="w-9 h-9 rounded-full bg-gray-200 shrink-0 animate-pulse"></div>
								<div class="flex flex-col gap-2 grow">
									<div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
									<div class="h-3 bg-gray-100 rounded animate-pulse w-1/4"></div>
								</div>
							</div>
						</div>

						<!-- Notification list -->
						<div
							v-else-if="notifications.data?.length"
							class="flex flex-col bg-white rounded border border-gray-100 divide-y divide-gray-50"
						>
							<router-link
								v-for="item in notifications.data"
								:key="item.name"
								:class="[
									'flex flex-row items-start p-4 gap-3',
									item.read ? 'bg-white' : 'bg-blue-50',
								]"
								:to="getItemRoute(item)"
								@click="markAsRead(item)"
							>
								<!-- Unread dot -->
								<span
									class="mt-2 shrink-0 w-2 h-2 rounded-full"
									:class="item.read ? 'bg-transparent' : 'bg-blue-500'"
								></span>
								<EmployeeAvatar :userID="item.from_user" size="md" />
								<div class="flex flex-col gap-1 grow min-w-0">
									<div
										class="text-sm leading-5 font-normal text-gray-800"
										v-html="item.message"
									></div>
									<div class="text-xs font-normal text-gray-400">
										{{ dayjs(item.creation).fromNow() }}
									</div>
								</div>
							</router-link>
						</div>

						<!-- Empty state -->
						<EmptyState
							v-else-if="!notifications.loading"
							:message="__('You have no notifications')"
						/>

						<!-- Load more -->
						<div v-if="notifications.hasNextPage" class="flex justify-center">
							<Button
								variant="outline"
								@click="loadMore"
								:loading="notifications.loading"
							>
								{{ __("Load more") }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonContent, IonPage } from "@ionic/vue"
import { useRouter } from "vue-router"
import { createResource, FeatherIcon } from "frappe-ui"
import { computed, inject, onMounted } from "vue"

import EmployeeAvatar from "@/components/EmployeeAvatar.vue"
import EmptyState from "@/components/EmptyState.vue"

import {
	unreadNotificationsCount,
	notifications,
	arePushNotificationsEnabled,
} from "@/data/notifications"

const userResource = inject("$user")
const dayjs = inject("$dayjs")
const router = useRouter()
const __ = inject("$translate")

const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

const markAllAsRead = createResource({
	url: "hrms.api.mark_all_notifications_as_read",
	onSuccess() {
		// reload() re-fetches all currently visible items and resets unread count
		notifications.reload()
	},
})

function markAsRead(item) {
	if (item.read) return
	// Optimistic update so the blue dot disappears immediately
	item.read = 1
	unreadNotificationsCount.reload()
	notifications.setValue.submit({ name: item.name, read: 1 })
}

// Map doctype name → PWA route name
const DOCTYPE_ROUTE = {
	"Leave Application": "LeaveApplicationDetailView",
	"Attendance Request": "AttendanceRequestDetailView",
	"Shift Request": "ShiftRequestDetailView",
	"Employee Permission": "EmployeePermissionDetailView",
	"Attendance Regularization": "AttendanceRegularizationDetailView",
	"Compensatory Leave Request": "CompensatoryLeaveRequestDetailView",
	"Expense Claim": "ExpenseClaimDetailView",
}

function getItemRoute(item) {
	if (!item.reference_document_type || !item.reference_document_name) {
		return { name: "Notifications" }
	}
	const routeName =
		DOCTYPE_ROUTE[item.reference_document_type] ||
		`${item.reference_document_type.replace(/\s+/g, "")}DetailView`
	return {
		name: routeName,
		params: { id: item.reference_document_name },
	}
}

onMounted(() => {
	const user = userResource.data?.name
	// Reset to first page for this user, then fetch
	notifications.filters = { to_user: user }
	notifications.start = 0
	notifications.pageLength = 20
	notifications.fetch()
})

// next() increments start by pageLength internally and appends new items to the list
function loadMore() {
	notifications.next()
}
</script>
