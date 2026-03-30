<template>
	<BaseLayout :pageTitle="__('Leaves & Holidays')">
		<template #body>
			<div class="px-4 pt-4 pb-8 lg:px-10 lg:pt-8 lg:pb-16 lg:max-w-7xl lg:mx-auto w-full">

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

				<!-- Desktop: two-column layout -->
				<div class="hidden lg:flex lg:flex-col lg:gap-6">

					<!-- Top: Leave Balance full width -->
					<div class="desk-card p-6">
						<LeaveBalance />
					</div>

					<!-- Bottom: two columns -->
					<div class="grid grid-cols-5 gap-6 items-start">

						<!-- Left: Recent Leave Requests -->
						<div class="col-span-3 desk-card p-6 flex flex-col gap-4">
							<div class="flex items-center justify-between">
								<div class="section-title">{{ __("Leave Requests") }}</div>
								<Button
									@click="openForm('LeaveApplicationFormView')"
									variant="solid"
									class="px-5 py-2 text-sm"
								>
									+ {{ __("Request a Leave") }}
								</Button>
							</div>
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
								:addListButton="true"
								listButtonRoute="LeaveApplicationListView"
							/>
						</div>

						<!-- Right: Holidays -->
						<div class="col-span-2 desk-card p-6 flex flex-col gap-4">
							<div class="section-title">{{ __("Holidays") }}</div>
							<Holidays />
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
import { useFormModal } from "@/composables/useFormModal"

import { myLeaves } from "@/data/leaves"

const __ = inject("$translate")
const { openForm } = useFormModal()
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
