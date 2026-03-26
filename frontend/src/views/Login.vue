<template>
	<ion-page>
		<ion-content :scroll-y="true">
			<div class="login-wrap">
				<div class="login-container">

					<!-- Logo + Title -->
					<div class="logo-section">
						<VGTSLogo class="logo-icon" />
						<div class="logo-text-wrap">
							<h1 class="login-title">{{ __("Welcome back") }}</h1>
							<p class="login-subtitle">{{ __("Sign in to VGTS-HRMS") }}</p>
						</div>
					</div>

					<!-- Login Form Card -->
					<div class="login-card">
						<form v-if="!user_pass_login_disabled.data" class="login-form" @submit.prevent="submit">

							<!-- Email -->
							<div class="field-group">
								<label class="field-label">{{ __("Email") }}</label>
								<input
									type="text"
									v-model="email"
									:placeholder="__('Enter your email')"
									autocomplete="username"
									class="field-input"
								/>
							</div>

							<!-- Password -->
							<div class="field-group">
								<label class="field-label">{{ __("Password") }}</label>
								<div class="password-wrap">
									<input
										:type="showPassword ? 'text' : 'password'"
										v-model="password"
										placeholder="••••••••"
										autocomplete="current-password"
										class="field-input password-input"
									/>
									<button
										type="button"
										@click="showPassword = !showPassword"
										class="eye-btn"
									>
										<FeatherIcon :name="showPassword ? 'eye-off' : 'eye'" class="eye-icon" />
									</button>
								</div>
							</div>

							<ErrorMessage :message="errorMessage" />

							<button type="submit" class="submit-btn" :disabled="session.login.loading">
								<span v-if="session.login.loading" class="spinner"></span>
								<span v-else>{{ __("Sign in") }}</span>
							</button>
						</form>

						<!-- OAuth divider -->
						<template v-if="authProviders.data?.length">
							<div v-if="!user_pass_login_disabled.data" class="divider">
								<div class="divider-line"></div>
								<span class="divider-text">{{ __("or") }}</span>
								<div class="divider-line"></div>
							</div>
							<div class="oauth-list">
								<a
									v-for="provider in authProviders.data"
									:key="provider.name"
									class="oauth-btn"
									:href="provider.auth_url"
								>
									<img class="oauth-icon" :src="provider.icon" :alt="provider.provider_name" />
									<span>{{ __("Continue with {0}", [provider.provider_name]) }}</span>
								</a>
							</div>
						</template>

						<div v-else-if="user_pass_login_disabled.data" class="no-login-msg">
							{{ __("No login methods are available. Please contact your administrator.") }}
						</div>
					</div>

				</div>
			</div>

			<!-- Reset Password Dialog -->
			<Dialog v-model="resetPassword.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("Reset Password") }}</h2>
				</template>
				<template #body-content>
					<p>{{ __("Your password has expired. Please reset your password to continue") }}</p>
				</template>
				<template #actions>
					<a
						class="inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-white bg-gray-900 hover:bg-gray-800 h-7 text-base px-2 rounded"
						:href="resetPassword.link"
						target="_blank"
					>
						{{ __("Go to Reset Password page") }}
					</a>
				</template>
			</Dialog>

			<!-- OTP Dialog -->
			<Dialog v-model="otp.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("OTP Verification") }}</h2>
				</template>
				<template #body-content>
					<p class="mb-4" v-if="otp.verification.prompt">{{ otp.verification.prompt }}</p>
					<form class="flex flex-col space-y-4" @submit.prevent="submit">
						<Input
							:label="__('OTP Code')"
							type="text"
							placeholder="000000"
							v-model="otp.code"
							autocomplete="one-time-code"
						/>
						<ErrorMessage :message="errorMessage" />
						<Button :loading="session.otp.loading" variant="solid" class="disabled:bg-gray-700 disabled:text-white !mt-6">
							{{ __("Verify") }}
						</Button>
					</form>
				</template>
			</Dialog>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { inject, reactive, ref } from "vue"
import { Input, Button, ErrorMessage, Dialog, createResource, FeatherIcon } from "frappe-ui"

import VGTSLogo from "@/components/icons/FrappeHRLogo.vue"

const email = ref(null)
const password = ref(null)
const showPassword = ref(false)
const errorMessage = ref("")

const resetPassword = reactive({ showDialog: false, link: "" })
const otp = reactive({ showDialog: false, tmp_id: "", code: "", verification: {} })

const session = inject("$session")
const __ = inject("$translate")

async function submit() {
	try {
		let response
		if (otp.showDialog) {
			response = await session.otp(otp.tmp_id, otp.code)
		} else {
			response = await session.login(email.value, password.value)
		}

		if (response.message === "Password Reset") {
			resetPassword.showDialog = true
			resetPassword.link = response.redirect_to
		} else {
			resetPassword.showDialog = false
			resetPassword.link = ""
		}

		if (response.verification) {
			if (response.verification.setup) {
				otp.showDialog = true
				otp.tmp_id = response.tmp_id
				otp.verification = response.verification
			} else {
				window.open("/login?redirect-to=" + encodeURIComponent(window.location.pathname), "_blank")
			}
		}
	} catch (error) {
		errorMessage.value = error.messages.join("\n")
	}
}

const user_pass_login_disabled = createResource({
	url: "hrms.api.system_settings.get_user_pass_login_disabled",
	method: "GET",
	initialData: 1,
	auto: true,
})

const authProviders = createResource({
	url: "hrms.api.oauth.oauth_providers",
	auto: true,
})
</script>

<style scoped>
/* Force light mode on login page — never dark */
ion-content {
	--background: #f4f6f8;
}

.login-wrap {
	min-height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	background: linear-gradient(145deg, #f0fdf4 0%, #f4f6f8 50%, #ffffff 100%);
	padding: 40px 20px;
}

.login-container {
	width: 100%;
	max-width: 400px;
	margin: 0 auto;
}

/* Logo section */
.logo-section {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 16px;
	margin-bottom: 32px;
}

.logo-icon {
	height: 52px;
	width: auto;
}

.logo-text-wrap {
	text-align: center;
}

.login-title {
	font-size: 1.5rem;
	font-weight: 700;
	color: #111827;
	margin: 0;
}

.login-subtitle {
	font-size: 0.875rem;
	color: #6b7280;
	margin: 4px 0 0;
}

/* Card */
.login-card {
	background: #ffffff;
	border-radius: 16px;
	border: 1px solid #e5e7eb;
	box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0,0,0,0.04);
	padding: 28px 24px;
}

/* Form */
.login-form {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.field-group {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.field-label {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #374151;
}

.field-input {
	width: 100%;
	padding: 10px 14px;
	font-size: 0.875rem;
	border: 1.5px solid #e5e7eb;
	border-radius: 10px;
	background: #f9fafb;
	color: #111827;
	outline: none;
	transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
	box-sizing: border-box;
}

.field-input:focus {
	background: #ffffff;
	border-color: #22c55e;
	box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15);
}

.field-input::placeholder {
	color: #9ca3af;
}

/* Password */
.password-wrap {
	position: relative;
}

.password-input {
	padding-right: 44px;
}

.eye-btn {
	position: absolute;
	right: 12px;
	top: 50%;
	transform: translateY(-50%);
	background: none;
	border: none;
	padding: 4px;
	cursor: pointer;
	color: #9ca3af;
	display: flex;
	align-items: center;
}

.eye-btn:hover {
	color: #6b7280;
}

.eye-icon {
	height: 16px;
	width: 16px;
}

/* Submit button */
.submit-btn {
	width: 100%;
	padding: 12px;
	font-size: 0.9375rem;
	font-weight: 600;
	color: #ffffff;
	background: #111827;
	border: none;
	border-radius: 10px;
	cursor: pointer;
	transition: background 0.15s;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
}

.submit-btn:hover:not(:disabled) {
	background: #1f2937;
}

.submit-btn:disabled {
	background: #9ca3af;
	cursor: not-allowed;
}

.spinner {
	width: 16px;
	height: 16px;
	border: 2px solid rgba(255,255,255,0.3);
	border-top-color: #ffffff;
	border-radius: 50%;
	animation: spin 0.7s linear infinite;
}

@keyframes spin {
	to { transform: rotate(360deg); }
}

/* Divider */
.divider {
	display: flex;
	align-items: center;
	gap: 12px;
	margin: 20px 0;
}

.divider-line {
	flex: 1;
	height: 1px;
	background: #e5e7eb;
}

.divider-text {
	font-size: 0.75rem;
	color: #9ca3af;
	text-transform: uppercase;
	letter-spacing: 0.05em;
}

/* OAuth */
.oauth-list {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.oauth-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 10px;
	padding: 10px 16px;
	font-size: 0.875rem;
	font-weight: 500;
	color: #374151;
	background: #ffffff;
	border: 1.5px solid #e5e7eb;
	border-radius: 10px;
	text-decoration: none;
	transition: background 0.15s, border-color 0.15s;
}

.oauth-btn:hover {
	background: #f9fafb;
	border-color: #d1d5db;
}

.oauth-icon {
	height: 18px;
	width: 18px;
}

.no-login-msg {
	text-align: center;
	font-size: 0.875rem;
	color: #6b7280;
	padding: 24px 0;
}
</style>
