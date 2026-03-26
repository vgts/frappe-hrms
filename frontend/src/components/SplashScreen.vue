<template>
	<Transition name="splash-fade">
		<div
			v-if="visible"
			class="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-white"
		>
			<div class="flex flex-col items-center gap-4">
				<VGTSLogo class="h-16 w-auto" />
				<span class="text-xl font-bold text-gray-900 tracking-tight">VGTS-HRMS</span>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { ref, onMounted } from "vue"
import VGTSLogo from "@/components/icons/FrappeHRLogo.vue"

const visible = ref(true)

onMounted(() => {
	setTimeout(() => {
		visible.value = false
	}, 1400)
})
</script>

<style scoped>
.splash-fade-leave-active {
	transition: opacity 0.5s ease;
}
.splash-fade-leave-to {
	opacity: 0;
}
</style>
