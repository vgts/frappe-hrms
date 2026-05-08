<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-full">

				<!-- Header -->
				<header
					class="flex flex-row bg-white shadow-sm py-4 px-3 lg:px-10 items-center justify-between border-b sticky top-0 z-10"
				>
					<div class="flex flex-row items-center gap-1">
						<Button variant="ghost" class="!pl-0 hover:bg-white" @click="router.back()">
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="text-xl font-semibold text-gray-900">{{ __("Notifications") }}</h2>
						<span
							v-if="unreadNotificationsCount.data"
							class="ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold rounded-full bg-blue-600 text-white"
						>
							{{ unreadNotificationsCount.data }}
						</span>
					</div>
					<div class="flex items-center gap-2">
						<Button
							v-if="allowPushNotifications"
							variant="ghost"
							@click="router.push({ name: 'Settings' })"
						>
							<FeatherIcon name="settings" class="w-4 h-4 text-gray-500" />
						</Button>
						<Button
							v-if="unreadNotificationsCount.data > 0"
							variant="outline"
							size="sm"
							@click="markAllAsRead.submit()"
							:loading="markAllAsRead.loading"
						>
							<template #prefix>
								<FeatherIcon name="check-circle" class="w-3.5 h-3.5" />
							</template>
							{{ __("Mark all read") }}
						</Button>
					</div>
				</header>

				<div class="flex flex-col p-4 lg:px-10 lg:py-8 lg:max-w-3xl lg:mx-auto w-full gap-1">

					<!-- Loading skeleton -->
					<div v-if="notifications.loading && !notifications.data?.length" class="flex flex-col gap-2">
						<div v-for="n in 5" :key="n"
							class="flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-100"
						>
							<div class="w-9 h-9 rounded-full bg-gray-200 shrink-0 animate-pulse"></div>
							<div class="flex flex-col gap-2 grow">
								<div class="h-3.5 bg-gray-200 rounded animate-pulse w-3/4"></div>
								<div class="h-3 bg-gray-100 rounded animate-pulse w-1/3"></div>
							</div>
						</div>
					</div>

					<!-- Grouped notification list -->
					<template v-else-if="groupedNotifications.length">
						<div v-for="group in groupedNotifications" :key="group.label" class="flex flex-col gap-1">
							<!-- Date group label -->
							<div class="text-xs font-semibold uppercase tracking-wider text-gray-400 px-1 pt-4 pb-1">
								{{ group.label }}
							</div>

							<!-- Notifications in group -->
							<div class="flex flex-col bg-white rounded-xl border border-gray-100 overflow-hidden divide-y divide-gray-50">
								<router-link
									v-for="item in group.items"
									:key="item.name"
									:to="getItemRoute(item)"
									@click="markAsRead(item)"
									class="flex items-start gap-3 px-4 py-3.5 transition-colors hover:bg-gray-50"
									:class="item.read ? 'bg-white' : 'bg-blue-50'"
								>
									<!-- Unread dot -->
									<span class="mt-1.5 shrink-0 w-2 h-2 rounded-full transition-all"
										:class="item.read ? 'bg-transparent' : 'bg-blue-500'"
									></span>

									<!-- Type icon -->
									<span class="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
										:class="getTypeColor(item.reference_document_type)"
									>
										<FeatherIcon :name="getTypeIcon(item.reference_document_type)" class="w-4 h-4" />
									</span>

									<!-- Content -->
									<div class="flex flex-col gap-0.5 grow min-w-0">
										<div class="text-sm leading-5 text-gray-800" v-html="item.message"></div>
										<div class="flex items-center gap-2 mt-0.5">
											<span class="text-xs text-gray-400">{{ dayjs(item.creation).fromNow() }}</span>
											<span
												v-if="item.reference_document_type"
												class="text-xs px-1.5 py-0.5 rounded font-medium"
												:class="getTypeColor(item.reference_document_type)"
											>
												{{ item.reference_document_type }}
											</span>
										</div>
									</div>

									<!-- Chevron -->
									<FeatherIcon name="chevron-right" class="shrink-0 w-4 h-4 text-gray-300 mt-1" />
								</router-link>
							</div>
						</div>
					</template>

					<!-- Empty state -->
					<div v-else-if="!notifications.loading" class="flex flex-col items-center justify-center py-20 gap-3">
						<div class="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center">
							<FeatherIcon name="bell-off" class="w-7 h-7 text-gray-400" />
						</div>
						<p class="text-sm text-gray-500">{{ __("You have no notifications") }}</p>
					</div>

					<!-- Load more -->
					<div v-if="notifications.hasNextPage" class="flex justify-center pt-4">
						<Button variant="outline" @click="loadMore" :loading="notifications.loading">
							{{ __("Load more") }}
						</Button>
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
	() => window.frappe?.boot.push_relay_server_url && arePushNotificationsEnabled.data
)

// ── Mark as read ──────────────────────────────────────────────────────────────
const markAllAsRead = createResource({
	url: "hrms.api.mark_all_notifications_as_read",
	onSuccess() {
		notifications.reload()
		unreadNotificationsCount.reload()
	},
})

function markAsRead(item) {
	if (item.read) return
	item.read = 1
	unreadNotificationsCount.reload()
	notifications.setValue.submit({ name: item.name, read: 1 })
}

// ── Routing ───────────────────────────────────────────────────────────────────
const DOCTYPE_ROUTE = {
	"Leave Application":          "LeaveApplicationDetailView",
	"Attendance Request":         "AttendanceRequestDetailView",
	"Shift Request":              "ShiftRequestDetailView",
	"Employee Permission":        "EmployeePermissionDetailView",
	"Attendance Regularization":  "AttendanceRegularizationDetailView",
	"Compensatory Leave Request": "CompensatoryLeaveRequestDetailView",
	"Expense Claim":              "ExpenseClaimDetailView",
}

function getItemRoute(item) {
	if (!item.reference_document_type || !item.reference_document_name) {
		return { name: "Notifications" }
	}
	const routeName =
		DOCTYPE_ROUTE[item.reference_document_type] ||
		`${item.reference_document_type.replace(/\s+/g, "")}DetailView`
	return { name: routeName, params: { id: item.reference_document_name } }
}

// ── Type icon + colour ────────────────────────────────────────────────────────
const TYPE_CONFIG = {
	"Leave Application":          { icon: "calendar",   color: "bg-green-100 text-green-600" },
	"Attendance Request":         { icon: "clock",      color: "bg-yellow-100 text-yellow-600" },
	"Shift Request":              { icon: "repeat",     color: "bg-purple-100 text-purple-600" },
	"Employee Permission":        { icon: "unlock",     color: "bg-orange-100 text-orange-600" },
	"Attendance Regularization":  { icon: "edit-2",    color: "bg-pink-100 text-pink-600" },
	"Compensatory Leave Request": { icon: "award",      color: "bg-indigo-100 text-indigo-600" },
	"Expense Claim":              { icon: "file-text",  color: "bg-blue-100 text-blue-600" },
}

function getTypeIcon(doctype) {
	return TYPE_CONFIG[doctype]?.icon || "bell"
}

function getTypeColor(doctype) {
	return TYPE_CONFIG[doctype]?.color || "bg-gray-100 text-gray-500"
}

// ── Date grouping ─────────────────────────────────────────────────────────────
const groupedNotifications = computed(() => {
	if (!notifications.data?.length) return []

	const today     = dayjs().startOf("day")
	const yesterday = dayjs().subtract(1, "day").startOf("day")
	const thisWeek  = dayjs().subtract(7, "day").startOf("day")

	const groups = { Today: [], Yesterday: [], "This Week": [], Older: [] }

	for (const item of notifications.data) {
		const d = dayjs(item.creation)
		if (d.isAfter(today))          groups["Today"].push(item)
		else if (d.isAfter(yesterday)) groups["Yesterday"].push(item)
		else if (d.isAfter(thisWeek))  groups["This Week"].push(item)
		else                           groups["Older"].push(item)
	}

	return Object.entries(groups)
		.filter(([, items]) => items.length)
		.map(([label, items]) => ({ label, items }))
})

// ── Mount ─────────────────────────────────────────────────────────────────────
onMounted(() => {
	const user = userResource.data?.name
	notifications.filters   = { to_user: user }
	notifications.start      = 0
	notifications.pageLength = 20
	notifications.fetch()
})

function loadMore() {
	notifications.next()
}
</script>
