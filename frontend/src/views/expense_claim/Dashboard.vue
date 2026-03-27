<template>
	<BaseLayout :pageTitle="__('Expense Claims')">
		<template #body>
			<div class="px-4 pt-4 pb-8 lg:px-8 lg:pt-6 lg:pb-12 lg:max-w-6xl lg:mx-auto">

				<!-- Mobile: single column -->
				<div class="lg:hidden flex flex-col gap-7 mt-3">
					<ExpenseClaimSummary />
					<router-link :to="{ name: 'ExpenseClaimFormView' }" v-slot="{ navigate }">
						<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
							{{ __("Claim an Expense") }}
						</Button>
					</router-link>
					<div>
						<div class="section-title mb-2">{{ __("Recent Expenses") }}</div>
						<RequestList
							:component="markRaw(ExpenseClaimItem)"
							:items="myClaims.data"
							:addListButton="true"
							listButtonRoute="ExpenseClaimListView"
						/>
					</div>
					<div>
						<div class="flex flex-row justify-between items-center mb-2">
							<div class="section-title">{{ __("Employee Advance Balance") }}</div>
							<router-link
								:to="{ name: 'EmployeeAdvanceListView' }"
								class="text-sm text-gray-700 font-semibold underline underline-offset-2"
							>
								{{ __("View List") }}
							</router-link>
						</div>
						<EmployeeAdvanceBalance :items="advanceBalance.data" />
					</div>
				</div>

				<!-- Desktop: two-column -->
				<div class="hidden lg:grid lg:grid-cols-2 lg:gap-8 lg:items-start lg:mt-2">

					<!-- Left: summary + claim button -->
					<div class="flex flex-col gap-5">
						<div class="desk-card p-6">
							<div class="section-title mb-4">{{ __("Expense Summary") }}</div>
							<ExpenseClaimSummary />
						</div>

						<div class="desk-card p-6 flex flex-col gap-4">
							<div class="section-title">{{ __("Employee Advance Balance") }}</div>
							<div class="flex justify-end">
								<router-link
									:to="{ name: 'EmployeeAdvanceListView' }"
									class="text-sm text-blue-600 font-medium hover:text-blue-700"
								>
									{{ __("View All") }}
								</router-link>
							</div>
							<EmployeeAdvanceBalance :items="advanceBalance.data" />
						</div>
					</div>

					<!-- Right: recent expenses -->
					<div class="flex flex-col gap-5">
						<div class="desk-card p-6 flex flex-col gap-4">
							<div class="section-title">{{ __("Expense Claims") }}</div>
							<router-link :to="{ name: 'ExpenseClaimFormView' }" v-slot="{ navigate }">
								<Button @click="navigate" variant="solid" class="w-full py-4 text-sm">
									{{ __("+ Claim an Expense") }}
								</Button>
							</router-link>
							<RequestList
								:component="markRaw(ExpenseClaimItem)"
								:items="myClaims.data"
								:addListButton="true"
								listButtonRoute="ExpenseClaimListView"
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
import ExpenseClaimSummary from "@/components/ExpenseClaimSummary.vue"
import RequestList from "@/components/RequestList.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import EmployeeAdvanceBalance from "@/components/EmployeeAdvanceBalance.vue"

import { myClaims } from "@/data/claims"
import { advanceBalance } from "@/data/advances"

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
