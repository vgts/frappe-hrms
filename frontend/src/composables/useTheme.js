import { ref, watch } from "vue"

const THEME_KEY = "hrms-theme"

// Singleton reactive theme state — shared across all uses
const theme = ref(
	localStorage.getItem(THEME_KEY) ||
		(window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
)

function applyTheme(t) {
	if (t === "dark") {
		document.documentElement.classList.add("dark")
	} else {
		document.documentElement.classList.remove("dark")
	}
}

// Apply immediately on module load
applyTheme(theme.value)

watch(theme, (t) => {
	applyTheme(t)
	localStorage.setItem(THEME_KEY, t)
})

export function useTheme() {
	const isDark = () => theme.value === "dark"

	function toggle() {
		theme.value = theme.value === "dark" ? "light" : "dark"
	}

	return { theme, isDark, toggle }
}
