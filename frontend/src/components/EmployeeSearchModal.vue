<template>
	<ion-modal
		:is-open="modelValue"
		@didDismiss="$emit('update:modelValue', false)"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="emp-search-modal">
			<!-- Header -->
			<div class="emp-search-header">
				<h3 class="emp-search-title">{{ __("Search Employee") }}</h3>
				<button class="emp-close-btn" @click="$emit('update:modelValue', false)">
					<FeatherIcon name="x" class="h-5 w-5" />
				</button>
			</div>

			<!-- Search Input -->
			<div class="emp-search-input-wrap">
				<FeatherIcon name="search" class="emp-search-icon" />
				<input
					ref="searchInputRef"
					v-model="searchQuery"
					type="text"
					:placeholder="__('Name, ID, department…')"
					class="emp-search-input"
					@input="onInput"
				/>
				<button v-if="searchQuery" class="emp-clear-btn" @click="searchQuery = ''">
					<FeatherIcon name="x-circle" class="h-4 w-4 text-gray-400" />
				</button>
			</div>

			<!-- Results -->
			<div class="emp-results-list">
				<!-- Loading -->
				<div v-if="loading" class="emp-state-msg">
					<div class="emp-spinner"></div>
				</div>

				<!-- Empty -->
				<div v-else-if="results.length === 0 && searchQuery.length > 0" class="emp-state-msg">
					<FeatherIcon name="users" class="h-8 w-8 text-gray-300 mb-2" />
					<p class="text-sm text-gray-400">{{ __("No employees found") }}</p>
				</div>

				<!-- Hint before typing -->
				<div v-else-if="results.length === 0 && searchQuery.length === 0" class="emp-state-msg">
					<FeatherIcon name="search" class="h-8 w-8 text-gray-300 mb-2" />
					<p class="text-sm text-gray-400">{{ __("Type to search employees") }}</p>
				</div>

				<!-- Employee rows -->
				<div
					v-for="emp in results"
					:key="emp.name"
					class="emp-row"
					@click="selectEmployee(emp)"
				>
					<!-- Avatar -->
					<div class="emp-row-avatar">
						<img
							v-if="emp.user_image"
							:src="emp.user_image"
							class="emp-avatar-img"
							:alt="emp.employee_name"
						/>
						<div v-else class="emp-avatar-fallback">
							{{ (emp.employee_name || "?")[0].toUpperCase() }}
						</div>
					</div>

					<!-- Info -->
					<div class="emp-row-info">
						<p class="emp-row-name">{{ emp.employee_name }}</p>
						<p class="emp-row-sub">
							<span v-if="emp.employee_number">#{{ emp.employee_number }} · </span>
							{{ emp.designation || emp.department || "" }}
						</p>
					</div>

					<!-- Check-in badge -->
					<div
						class="emp-checkin-badge"
						:class="emp.is_checked_in ? 'badge-in' : 'badge-out'"
					>
						{{ emp.is_checked_in ? __("IN") : __("Out") }}
					</div>
				</div>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { ref, watch, nextTick } from "vue"
import { useRouter } from "vue-router"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, createResource } from "frappe-ui"
import { inject } from "vue"

const __ = inject("$translate")
const router = useRouter()

const props = defineProps({
	modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue"])

const searchQuery   = ref("")
const results       = ref([])
const loading       = ref(false)
const searchInputRef = ref(null)

let debounceTimer = null

const searchResource = createResource({
	url: "vgts.api.search_employees",
	onSuccess(data) {
		results.value = data || []
		loading.value = false
	},
	onError() {
		results.value = []
		loading.value = false
	},
})

function onInput() {
	clearTimeout(debounceTimer)
	if (!searchQuery.value) {
		results.value = []
		loading.value = false
		return
	}
	loading.value = true
	debounceTimer = setTimeout(() => {
		searchResource.submit({ query: searchQuery.value, limit: 30 })
	}, 350)
}

function selectEmployee(emp) {
	emit("update:modelValue", false)
	router.push({ name: "EmployeeProfile", params: { employeeName: emp.name } })
}

// Focus input when modal opens
watch(() => props.modelValue, (val) => {
	if (val) {
		searchQuery.value = ""
		results.value = []
		nextTick(() => searchInputRef.value?.focus())
	}
})
</script>

<style scoped>
.emp-search-modal {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: #f9fafb;
}

.emp-search-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 16px 12px;
	background: #fff;
	border-bottom: 1px solid #f3f4f6;
}

.emp-search-title {
	font-size: 1rem;
	font-weight: 600;
	color: #111827;
	margin: 0;
}

.emp-close-btn {
	background: none;
	border: none;
	cursor: pointer;
	color: #6b7280;
	padding: 4px;
	display: flex;
	align-items: center;
}

.emp-search-input-wrap {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 12px 16px;
	background: #fff;
	border: 1px solid #e5e7eb;
	border-radius: 10px;
	padding: 10px 12px;
}

.emp-search-icon {
	height: 16px;
	width: 16px;
	color: #9ca3af;
	flex-shrink: 0;
}

.emp-search-input {
	flex: 1;
	border: none;
	outline: none;
	font-size: 0.9375rem;
	color: #111827;
	background: transparent;
}

.emp-search-input::placeholder {
	color: #9ca3af;
}

.emp-clear-btn {
	background: none;
	border: none;
	cursor: pointer;
	padding: 0;
	display: flex;
	align-items: center;
}

.emp-results-list {
	flex: 1;
	overflow-y: auto;
	padding: 0 16px 32px;
}

.emp-state-msg {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 48px 0;
	color: #9ca3af;
}

.emp-spinner {
	width: 28px;
	height: 28px;
	border: 3px solid #e5e7eb;
	border-top-color: #6b7280;
	border-radius: 50%;
	animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.emp-row {
	display: flex;
	align-items: center;
	gap: 12px;
	background: #fff;
	border-radius: 12px;
	padding: 12px;
	margin-bottom: 8px;
	cursor: pointer;
	border: 1px solid #f3f4f6;
	transition: background 0.1s;
}

.emp-row:active {
	background: #f9fafb;
}

.emp-row-avatar {
	flex-shrink: 0;
}

.emp-avatar-img {
	width: 44px;
	height: 44px;
	border-radius: 50%;
	object-fit: cover;
}

.emp-avatar-fallback {
	width: 44px;
	height: 44px;
	border-radius: 50%;
	background: #e5e7eb;
	color: #6b7280;
	font-size: 1.125rem;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
	text-transform: uppercase;
}

.emp-row-info {
	flex: 1;
	min-width: 0;
}

.emp-row-name {
	font-size: 0.9375rem;
	font-weight: 600;
	color: #111827;
	margin: 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.emp-row-sub {
	font-size: 0.75rem;
	color: #9ca3af;
	margin: 2px 0 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.emp-checkin-badge {
	flex-shrink: 0;
	font-size: 0.6875rem;
	font-weight: 700;
	letter-spacing: 0.05em;
	padding: 3px 8px;
	border-radius: 999px;
}

.badge-in {
	background: #dcfce7;
	color: #16a34a;
	border: 1px solid #bbf7d0;
}

.badge-out {
	background: #f3f4f6;
	color: #9ca3af;
	border: 1px solid #e5e7eb;
}
</style>
