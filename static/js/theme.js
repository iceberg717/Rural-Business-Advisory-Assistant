/**
 * RuralBiz Advisor — Theme Switcher Controller
 * Manages Dark Mode and Light Mode with localStorage persistence and fail-safe click handlers.
 */

(function () {
    const STORAGE_KEY = 'ruralbiz_theme';

    function getPreferredTheme() {
        try {
            const savedTheme = localStorage.getItem(STORAGE_KEY);
            if (savedTheme === 'dark' || savedTheme === 'light') {
                return savedTheme;
            }
        } catch (e) {}

        return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
            ? 'dark'
            : 'light';
    }

    function applyTheme(theme) {
        const targetTheme = (theme === 'dark') ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', targetTheme);
        
        try {
            localStorage.setItem(STORAGE_KEY, targetTheme);
        } catch (e) {}

        const iconEl = document.getElementById('theme-icon');
        const textEl = document.getElementById('theme-text');
        if (iconEl) {
            iconEl.textContent = targetTheme === 'dark' ? '☀️' : '🌙';
        }
        if (textEl) {
            textEl.textContent = targetTheme === 'dark' ? 'Light' : 'Dark';
        }
    }

    // Global toggle function exposed on window for inline onclick & external triggers
    window.toggleRuralTheme = function () {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);
        return nextTheme;
    };

    // Apply theme immediately
    applyTheme(getPreferredTheme());

    function setupThemeToggleListener() {
        const toggleBtn = document.getElementById('theme-toggle-btn');
        if (toggleBtn) {
            // Remove previous listener clone to prevent duplicates if re-run
            toggleBtn.onclick = function (e) {
                if (e) e.preventDefault();
                window.toggleRuralTheme();
            };
            
            // Sync initial button icon/text
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            applyTheme(current);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupThemeToggleListener);
    } else {
        setupThemeToggleListener();
    }

    // Also listen for OS system theme changes if user hasn't explicitly set preference
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            try {
                if (!localStorage.getItem(STORAGE_KEY)) {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            } catch (err) {}
        });
    }
})();
