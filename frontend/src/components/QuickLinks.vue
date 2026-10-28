<template>
	<div class="flex flex-col gap-5 my-4 w-full">
		<div class="text-lg font-medium text-gray-900">{{ title || __("Quick Links") }}</div>
		<div class="bg-white rounded lg:grid lg:grid-cols-2 lg:divide-x-0 divide-y lg:divide-y-0 overflow-hidden border border-gray-100">
			<!-- `href` links open a page outside the app (e.g. /my_devices) -->
			<component
				:is="link.href ? 'a' : 'router-link'"
				class="flex flex-row flex-start p-4 items-center justify-between border-b lg:border-b lg:border-r lg:even:border-r-0 last:border-b-0 lg:last:border-b-0"
				v-for="link in props.items"
				:key="link.title"
				v-bind="link.href ? { href: link.href } : { to: { name: link.route } }"
			>
				<div class="flex flex-row items-center gap-3 grow">
					<component :is="link.icon" class="h-5 w-5 text-gray-500" />
					<div class="text-base font-normal text-gray-800">
						{{ link.title }}
					</div>
				</div>
				<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
			</component>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: {
		type: String,
		required: false,
		default: "",
	},
	items: {
		type: Array,
		required: true,
	},
})
</script>
