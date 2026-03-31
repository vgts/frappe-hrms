<template>
	<BaseLayout :pageTitle="__('Salary Slips')">
		<template #body>
			<div class="px-4 pt-4 pb-8 lg:px-10 lg:pt-8 lg:pb-16 lg:max-w-7xl lg:mx-auto w-full">

				<!-- Mobile layout -->
				<div class="lg:hidden flex flex-col gap-5 mt-3">
					<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex flex-col gap-5">
						<div v-if="lastSalarySlip && lastSalarySlip.year_to_date" class="flex flex-col gap-1">
							<span class="text-gray-500 text-sm font-medium">{{ __("Year To Date") }}</span>
							<span class="text-gray-800 text-xl font-bold">
								{{ formatCurrency(lastSalarySlip.year_to_date, lastSalarySlip.currency) }}
							</span>
						</div>
						<Autocomplete
							:label="__('Payroll Period')"
							class="w-full"
							:placeholder="__('Select Payroll Period')"
							v-model="selectedPeriod"
							:options="payrollPeriods.data"
						/>
					</div>
					<div v-if="documents.data?.length" class="flex flex-col bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
						<div class="p-3.5 border-b border-gray-100 last:border-b-0 cursor-pointer hover:bg-gray-50" v-for="link in documents.data" :key="link.name">
							<router-link :to="{ name: 'SalarySlipDetailView', params: { id: link.name } }" v-slot="{ navigate }">
								<SalarySlipItem :doc="link" @click="navigate" />
							</router-link>
						</div>
					</div>
					<EmptyState :message="__('No salary slips found')" v-else />
				</div>

				<!-- Desktop layout -->
				<div class="hidden lg:grid lg:grid-cols-5 lg:gap-6 lg:items-start mt-3">
					<!-- Left: YTD + Period selector -->
					<div class="col-span-2 flex flex-col gap-5 bg-white rounded-xl border border-gray-100 shadow-sm p-6">
						<div class="text-lg font-bold text-gray-800">{{ __("Salary Overview") }}</div>
						<div v-if="lastSalarySlip && lastSalarySlip.year_to_date" class="flex flex-col gap-1">
							<span class="text-gray-500 text-sm font-medium">{{ __("Year To Date") }}</span>
							<span class="text-gray-800 text-2xl font-bold">
								{{ formatCurrency(lastSalarySlip.year_to_date, lastSalarySlip.currency) }}
							</span>
						</div>
						<Autocomplete
							:label="__('Payroll Period')"
							class="w-full"
							:placeholder="__('Select Payroll Period')"
							v-model="selectedPeriod"
							:options="payrollPeriods.data"
						/>
					</div>
					<!-- Right: Salary Slip list -->
					<div class="col-span-3 bg-white rounded-xl border border-gray-100 shadow-sm p-6 flex flex-col gap-4">
						<div class="text-lg font-bold text-gray-800">{{ __("Salary Slips") }}</div>
						<div v-if="documents.data?.length" class="flex flex-col overflow-hidden rounded-lg border border-gray-100">
							<div class="p-3.5 border-b border-gray-100 last:border-b-0 cursor-pointer hover:bg-gray-50" v-for="link in documents.data" :key="link.name">
								<router-link :to="{ name: 'SalarySlipDetailView', params: { id: link.name } }" v-slot="{ navigate }">
									<SalarySlipItem :doc="link" @click="navigate" />
								</router-link>
							</div>
						</div>
						<EmptyState :message="__('No salary slips found')" v-else />
					</div>
				</div>

			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, ref, computed, watch, onMounted, onBeforeUnmount } from "vue"
import { Autocomplete, createListResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import SalarySlipItem from "@/components/SalarySlipItem.vue"

import { formatCurrency } from "@/utils/formatters"

let selectedPeriod = ref({})
let periodsByName = ref({})

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const __ = inject("$translate")

const payrollPeriods = createListResource({
	doctype: "Payroll Period",
	fields: ["name", "start_date", "end_date"],
	filters: {
		company: employee.data?.company,
	},
	orderBy: "start_date desc",
	auto: true,
	transform(data) {
		return data.map((period) => {
			periodsByName.value[period.name] = period
			return {
				label: getPeriodLabel(period),
				value: period.name,
			}
		})
	},
	onSuccess: (data) => {
		selectedPeriod.value = data[0]
	},
})

const documents = createListResource({
	doctype: "Salary Slip",
	fields: [
		"name",
		"start_date",
		"end_date",
		"currency",
		"gross_pay",
		"net_pay",
		"year_to_date",
	],
	filters: {
		employee: employee.data?.name,
		docstatus: 1,
	},
	orderBy: "end_date desc",
})

const lastSalarySlip = computed(() => documents.data?.[0])

function getPeriodLabel(period) {
	return `${dayjs(period?.start_date).format("MMM YYYY")} - ${dayjs(
		period?.end_date
	).format("MMM YYYY")}`
}

watch(
	() => selectedPeriod.value,
	(value) => {
		let period = periodsByName.value[value?.value]
		documents.filters.start_date = [
			"between",
			[period?.start_date, period?.end_date],
		]
		documents.reload()
	}
)

onMounted(() => {
	socket.on("hrms:update_salary_slips", (data) => {
		if (data.employee === employee.data.name) {
			documents.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.off("hrms:update_salary_slips")
})
</script>
