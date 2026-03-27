<template>
	<div class="modal-wrap">
		<!-- Header -->
		<div class="modal-header">
			<span class="modal-title">{{ title }}</span>
		</div>

		<!-- Fields -->
		<div class="modal-body">
			<div
				v-for="item in data"
				:key="item.fieldname"
				class="field-row"
			>
				<div class="field-label">{{ item.label }}</div>
				<div class="field-value">
					<FormattedField
						:value="item.value"
						:fieldtype="item.fieldtype"
						:fieldname="item.fieldname"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import FormattedField from "@/components/FormattedField.vue"

const props = defineProps({
	title: {
		type: String,
		required: true,
	},
	data: {
		type: Array,
		required: true,
	},
})
</script>

<style scoped>
.modal-wrap {
	background: #ffffff;
	width: 100%;
	display: flex;
	flex-direction: column;
	padding-bottom: 24px;
	max-height: calc(100vh - 5rem);
}

.modal-header {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 24px 16px 16px;
	border-bottom: 1px solid #f3f4f6;
	position: sticky;
	top: 0;
	z-index: 100;
	background: #ffffff;
}

.modal-title {
	font-size: 1.125rem;
	font-weight: 700;
	color: #111827;
}

.modal-body {
	display: flex;
	flex-direction: column;
	padding: 8px 20px;
}

.field-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 14px 0;
	border-bottom: 1px solid #f9fafb;
	gap: 12px;
}

.field-row:last-child {
	border-bottom: none;
}

.field-label {
	font-size: 0.8125rem;
	color: #6b7280;
	flex-shrink: 0;
}

.field-value {
	font-size: 0.875rem;
	font-weight: 500;
	color: #111827;
	text-align: right;
	word-break: break-word;
}
</style>
