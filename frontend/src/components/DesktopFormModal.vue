<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="closeForm"
		:class="['desktop-form-modal']"
	>
		<component v-if="isOpen" :is="activeComponent" :key="componentKey" />
	</ion-modal>
</template>

<script setup>
import { ref, watch, provide } from "vue"
import { useRoute, useRouter } from "vue-router"
import { IonModal } from "@ionic/vue"
import { useFormModal } from "@/composables/useFormModal"

const { isOpen, activeComponent, closeForm } = useFormModal()
const route = useRoute()
const router = useRouter()
const componentKey = ref(0)

provide("isInsideFormModal", true)
provide("closeFormModal", closeForm)

watch(() => route.fullPath, () => {
	if (isOpen.value) closeForm()
})

watch(isOpen, (val) => {
	if (val) componentKey.value++
})

const originalBack = router.back.bind(router)
router.back = function () {
	if (isOpen.value) {
		closeForm()
	} else {
		originalBack()
	}
}
</script>

<style>
/* ===== Desktop: centered card modal ===== */
@media (min-width: 1024px) {
	ion-modal.desktop-form-modal {
		--width: 560px;
		--max-width: 90vw;
		--height: 85vh;
		--border-radius: 14px;
		--box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
	}

	ion-modal.desktop-form-modal::part(backdrop) {
		background: rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(6px);
		-webkit-backdrop-filter: blur(6px);
	}

	ion-modal.desktop-form-modal::part(content) {
		border-radius: 14px;
		overflow: hidden;
	}

	/* Restyle the FormView header inside modal */
	ion-modal.desktop-form-modal ion-page ion-content header,
	ion-modal.desktop-form-modal header {
		background: linear-gradient(to right, #f8fafc, #ffffff) !important;
		border-bottom: 1px solid #f1f5f9 !important;
		padding: 16px 20px !important;
		box-shadow: none !important;
	}

	/* Turn back arrow into X close button style */
	ion-modal.desktop-form-modal header button:first-child,
	ion-modal.desktop-form-modal header .ghost {
		padding: 0 !important;
		margin-right: 4px !important;
	}

	/* Refine the title text */
	ion-modal.desktop-form-modal header h2 {
		font-size: 1.125rem !important;
		font-weight: 700 !important;
		color: #1e293b !important;
	}

	/* Form fields area - nicer padding */
	ion-modal.desktop-form-modal .flex.flex-col.space-y-4.p-4 {
		padding: 20px 24px !important;
	}

	/* Form field labels */
	ion-modal.desktop-form-modal .flex.flex-col.space-y-4 label {
		font-size: 0.8125rem !important;
		font-weight: 500 !important;
		color: #475569 !important;
	}

	/* Section headers inside form (like "Reason") */
	ion-modal.desktop-form-modal .flex.flex-col.space-y-4 .text-base.font-bold,
	ion-modal.desktop-form-modal .flex.flex-col.space-y-4 .font-bold {
		font-size: 0.8125rem !important;
		font-weight: 600 !important;
		color: #334155 !important;
		text-transform: uppercase !important;
		letter-spacing: 0.025em !important;
		padding-top: 8px !important;
		margin-top: 4px !important;
		border-top: 1px solid #f1f5f9 !important;
	}

	/* Save/Submit button footer */
	ion-modal.desktop-form-modal .sticky.bottom-0 {
		background: #f8fafc !important;
		border-top: 1px solid #e2e8f0 !important;
		padding: 14px 24px !important;
		box-shadow: none !important;
		drop-shadow: none !important;
		filter: none !important;
	}

	ion-modal.desktop-form-modal .sticky.bottom-0 button {
		border-radius: 10px !important;
		font-weight: 600 !important;
		font-size: 0.875rem !important;
		padding-top: 12px !important;
		padding-bottom: 12px !important;
	}

	/* Inputs refinement */
	ion-modal.desktop-form-modal input,
	ion-modal.desktop-form-modal select,
	ion-modal.desktop-form-modal textarea {
		border-radius: 8px !important;
		font-size: 0.875rem !important;
	}

	/* Checkbox styling */
	ion-modal.desktop-form-modal input[type="checkbox"] {
		border-radius: 4px !important;
	}
}

/* ===== Mobile: full screen ===== */
@media (max-width: 1023px) {
	ion-modal.desktop-form-modal {
		--width: 100%;
		--height: 100%;
		--border-radius: 0;
	}
}
</style>
