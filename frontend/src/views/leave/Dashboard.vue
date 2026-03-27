<template>
	<BaseLayout :pageTitle="__('Leaves & Holidays')">
		<template #body>
			<div class="px-4 pt-4 pb-8 lg:px-8 lg:pt-6 lg:pb-12 lg:max-w-6xl lg:mx-auto">

				<!-- Mobile: single column -->
				<div class="lg:hidden flex flex-col gap-7 mt-3">
					<LeaveBalance />
					<router-link :to="{ name: 'LeaveApplicationFormView' }" v-slot="{ navigate }">
						<Button @click="navigate" variant="solid" class="py-5 text-base w-full">
							{{ __("Request a Leave") }}
						</Button>
					</router-link>
					<div>
						<div class="section-title mb-2">{{ __("Recent Leaves") }}</div>
						<RequestList
							:component="markRaw(LeaveRequestItem)"
							:items="myLeaves.data"
							:addListButton="true"
							listButtonRoute="LeaveApplicationListView"
						/>
					</div>
					<Holidays />
				</div>

				<!-- Desktop: two-column -->
				<div class="hidden lg:grid lg:grid-cols-5 lg:gap-8 lg:items-start lg:mt-2">

					<!-- Left: leave balance (wider) -->
					<div class="lg:col-span-3 flex flex-col gap-5">
						<div class="desk-card p-6">
							<LeaveBalance />
						</div>
						<div class="desk-card p-6">
							<div class="section-title mb-4">{{ __("Holidays") }}</div>
							<Holidays />
						</div>
					</div>

					<!-- Right: request + recent leaves -->
					<div class="lg:col-span-2 flex flex-col gap-5">
						<div class="desk-card p-6 flex flex-col gap-4">
							<div class="section-title">{{ __("Leave Requests") }}</div>
							<router-link :to="{ name: 'LeaveApplicationFormView' }" v-slot="{ navigate }">
								<Button @click="navigate" variant="solid" class="w-full py-4 text-sm">
									{{ __("+ Request a Leave") }}
								</Button>
							</router-link>
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
								:addListButton="true"
								listButtonRoute="LeaveApplicationListView"
							/>
						</div>
					</div>
				</div>

			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw, inject } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import LeaveBalance from "@/components/LeaveBalance.vue"
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import Holidays from "@/components/Holidays.vue"

import { myLeaves } from "@/data/leaves"

const __ = inject("$translate")
</script>

<style scoped>
.section-title {
	font-size: 1rem;
	font-weight: 700;
	color: #1f2937;
}

.desk-card {
	background: #ffffff;
	border: 1px solid #e5e7eb;
	border-radius: 12px;
	box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
</style>
