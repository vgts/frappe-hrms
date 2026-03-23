import { initializeApp } from "firebase/app"
import {
	getMessaging,
	getToken,
	isSupported,
	deleteToken,
	onMessage as onFCMMessage,
} from "firebase/messaging"

class FrappePushNotification {
	/**
	 * Constructor
	 *
	 * @param {string} projectName
	 */
	constructor(projectName) {
		this.projectName = projectName
		this.token = null
		this.initialized = false
		this.messaging = null
		/** @type {ServiceWorkerRegistration | null} */
		this.serviceWorkerRegistration = null
		this.onMessageHandler = null
	}

	/**
	 * Get Firebase config from boot data
	 *
	 * @returns {object|null}
	 */
	getFirebaseConfig() {
		return window.frappe?.boot?.fcm_config || null
	}

	/**
	 * Get VAPID key from boot data
	 *
	 * @returns {string}
	 */
	getVapidKey() {
		return window.frappe?.boot?.fcm_vapid_key || ""
	}

	/**
	 * Fetch web config - returns config from boot data
	 *
	 * @returns {Promise<object>}
	 */
	async fetchWebConfig() {
		const config = this.getFirebaseConfig()
		if (!config) {
			throw new Error(
				"FCM is not configured. Set fcm_config in site_config.json"
			)
		}
		return config
	}

	/**
	 * Initialize notification service client
	 *
	 * @param {ServiceWorkerRegistration} serviceWorkerRegistration
	 * @returns {Promise<void>}
	 */
	async initialize(serviceWorkerRegistration) {
		if (this.initialized) return
		this.serviceWorkerRegistration = serviceWorkerRegistration

		const config = this.getFirebaseConfig()
		if (!config) {
			console.warn("FCM config not found in boot data")
			return
		}

		this.messaging = getMessaging(initializeApp(config))
		this.onMessage(this.onMessageHandler)
		this.initialized = true
	}

	/**
	 * Register on message handler
	 *
	 * @param {function} callback
	 */
	onMessage(callback) {
		if (callback == null) return
		this.onMessageHandler = callback
		if (this.messaging == null) return
		onFCMMessage(this.messaging, this.onMessageHandler)
	}

	/**
	 * Check if notification is enabled
	 *
	 * @returns {boolean}
	 */
	isNotificationEnabled() {
		return (
			localStorage.getItem(`firebase_token_${this.projectName}`) !== null
		)
	}

	/**
	 * Enable notification
	 *
	 * @returns {Promise<{permission_granted: boolean, token: string}>}
	 */
	async enableNotification() {
		if (!(await isSupported())) {
			throw new Error(
				"Push notifications are not supported on your device"
			)
		}

		if (this.token != null) {
			return { permission_granted: true, token: this.token }
		}

		const permission = await Notification.requestPermission()
		if (permission !== "granted") {
			return { permission_granted: false, token: "" }
		}

		const vapidKey = this.getVapidKey()
		if (!vapidKey) {
			throw new Error(
				"FCM VAPID key not configured. Set fcm_vapid_key in site_config.json"
			)
		}

		let newToken = await getToken(this.messaging, {
			vapidKey: vapidKey,
			serviceWorkerRegistration: this.serviceWorkerRegistration,
		})

		let oldToken = localStorage.getItem(
			`firebase_token_${this.projectName}`
		)

		if (oldToken !== newToken) {
			if (oldToken) {
				await this.unregisterToken(oldToken)
			}
			let success = await this.registerToken(newToken)
			if (!success) {
				throw new Error(
					"Failed to register push notification token"
				)
			}
			localStorage.setItem(
				`firebase_token_${this.projectName}`,
				newToken
			)
		}

		this.token = newToken
		return { permission_granted: true, token: newToken }
	}

	/**
	 * Disable notification
	 *
	 * @returns {Promise<void>}
	 */
	async disableNotification() {
		if (this.token == null) {
			this.token = localStorage.getItem(
				`firebase_token_${this.projectName}`
			)
			if (this.token == null || this.token === "") return
		}

		try {
			await deleteToken(this.messaging)
		} catch (e) {
			console.error("Failed to delete token from firebase", e)
		}

		try {
			await this.unregisterToken(this.token)
		} catch (e) {
			console.error("Failed to unregister token", e)
		}

		localStorage.removeItem(`firebase_token_${this.projectName}`)
		this.token = null
	}

	/**
	 * Register token with the server
	 *
	 * @param {string} token
	 * @returns {Promise<boolean>}
	 */
	async registerToken(token) {
		try {
			let response = await fetch(
				"/api/method/hrms.hr.fcm_api.register_fcm_token",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token":
							window.csrf_token || window.frappe?.csrf_token,
					},
					body: JSON.stringify({ token: token }),
				}
			)
			return response.ok
		} catch (e) {
			console.error("Token registration failed", e)
			return false
		}
	}

	/**
	 * Unregister token from the server
	 *
	 * @param {string} token
	 * @returns {Promise<boolean>}
	 */
	async unregisterToken(token) {
		try {
			let response = await fetch(
				"/api/method/hrms.hr.fcm_api.unregister_fcm_token",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token":
							window.csrf_token || window.frappe?.csrf_token,
					},
					body: JSON.stringify({ token: token }),
				}
			)
			return response.ok
		} catch (e) {
			console.error("Token unregistration failed", e)
			return false
		}
	}
}

export default FrappePushNotification
