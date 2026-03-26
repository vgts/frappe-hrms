<template>
	<Teleport to="body">
		<transition name="modal-fade">
			<div
				v-if="isOpen"
				class="fixed inset-0 z-[9999] hidden lg:flex items-center justify-center"
			>
				<!-- Backdrop -->
				<div
					class="absolute inset-0 bg-black/40 backdrop-blur-sm"
					@click="closeForm"
				></div>

				<!-- Modal container -->
				<div class="relative w-[680px] max-w-[90vw] h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col desktop-form-modal">
					<!-- Close button -->
					<button
						@click="closeForm"
						class="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
					>
						<FeatherIcon name="x" class="h-4 w-4 text-gray-600" />
					</button>

					<!-- Form content -->
					<div class="flex-1 overflow-y-auto">
						<component :is="activeComponent" :key="componentKey" />
					</div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { ref, watch, provide } from "vue"
import { useRoute, useRouter } from "vue-router"
import { FeatherIcon } from "frappe-ui"
import { useFormModal } from "@/composables/useFormModal"

const { isOpen, activeComponent, closeForm } = useFormModal()
const route = useRoute()
const router = useRouter()
const componentKey = ref(0)

// Provide a flag so child components know they're inside a modal
provide("isInsideFormModal", true)
provide("closeFormModal", closeForm)

// Close modal on any route change (handles router.back / router.replace from FormView)
watch(() => route.fullPath, () => {
	if (isOpen.value) {
		closeForm()
	}
})

// Refresh component key when modal opens
watch(isOpen, (val) => {
	if (val) componentKey.value++
})

// Intercept router.back() — if modal is open, close it instead
const originalBack = router.back.bind(router)
router.back = function () {
	if (isOpen.value) {
		closeForm()
	} else {
		originalBack()
	}
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
	transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
	opacity: 0;
}

/* Override ion-page positioning inside modal */
.desktop-form-modal :deep(ion-page) {
	position: relative !important;
	contain: none !important;
}
.desktop-form-modal :deep(ion-content) {
	--offset-top: 0px !important;
	--offset-bottom: 0px !important;
	position: relative !important;
	contain: none !important;
}
.desktop-form-modal :deep(ion-content .inner-scroll) {
	overflow-y: visible !important;
	position: relative !important;
}
</style>
