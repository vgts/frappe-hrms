// Dark mode removed — always light
const THEME_KEY = "hrms-theme"

// Clear any stored dark preference
localStorage.removeItem(THEME_KEY)
document.documentElement.classList.remove("dark")

export function useTheme() {
	const isDark = () => false
	function toggle() {}
	return { theme: { value: "light" }, isDark, toggle }
}
