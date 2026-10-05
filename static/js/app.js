/**
 * Sulit Store Profit-Intelligent POS & Inventory System
 * Master Application State & View Navigation Controller
 * Developer: Team 8
 */

const AppState = {
    currentUser: {
        role: "admin",
        username: "admin",
        full_name: "Store Manager"
    },
    currentTab: "pos-view",
    theme: localStorage.getItem("sulit_theme") || "dark"
};

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initNavigation();
    initRoleSwitcher();
    checkCurrentUser();

    // Default load POS view
    switchTab("pos-view");
});

function initTheme() {
    document.documentElement.setAttribute("data-theme", AppState.theme);
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            AppState.theme = AppState.theme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", AppState.theme);
            localStorage.setItem("sulit_theme", AppState.theme);
            updateThemeIcon();
        });
        updateThemeIcon();
    }
}

function updateThemeIcon() {
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (!themeBtn) return;
    if (AppState.theme === "light") {
        themeBtn.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>`;
    } else {
        themeBtn.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>`;
    }
}

function initNavigation() {
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const targetTab = link.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });
}

function switchTab(tabId) {
    AppState.currentTab = tabId;

    // Update active nav link
    document.querySelectorAll(".nav-link").forEach(link => {
        if (link.getAttribute("data-tab") === tabId) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    // Update active view
    document.querySelectorAll(".tab-view").forEach(view => {
        if (view.id === tabId) {
            view.classList.add("active");
        } else {
            view.classList.remove("active");
        }
    });

    // Trigger tab-specific loaders
    if (tabId === "pos-view" && window.loadPOSCatalog) {
        window.loadPOSCatalog();
    } else if (tabId === "inventory-view" && window.loadInventory) {
        window.loadInventory();
    } else if (tabId === "analytics-view" && window.loadAnalytics) {
        window.loadAnalytics();
    } else if (tabId === "predictive-view" && window.loadPredictiveOverview) {
        window.loadPredictiveOverview();
    } else if (tabId === "storefront-view" && window.loadStorefront) {
        window.loadStorefront();
    } else if (tabId === "srp-view" && window.loadSRPOverview) {
        window.loadSRPOverview();
    } else if (tabId === "audit-view" && window.loadAuditLogs) {
        window.loadAuditLogs();
    }
}

function initRoleSwitcher() {
    const selector = document.getElementById("active-role-selector");
    if (!selector) return;

    selector.addEventListener("change", async (e) => {
        const selectedRole = e.target.value;
        try {
            const res = await fetch("/api/auth/switch_demo_role", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role: selectedRole })
            });
            const data = await res.json();
            if (data.success) {
                AppState.currentUser = data.user;
                applyRBAC(data.user.role);
                // Reload current view with new permissions
                switchTab(AppState.currentTab);
                showToast(`Switched active role to: ${data.user.role.toUpperCase()}`, "info");
            }
        } catch (err) {
            console.error("Role switch error:", err);
        }
    });
}

async function checkCurrentUser() {
    try {
        const res = await fetch("/api/auth/current_user");
        const data = await res.json();
        if (data.authenticated) {
            AppState.currentUser = data.user;
            const selector = document.getElementById("active-role-selector");
            if (selector) selector.value = data.user.role;
            applyRBAC(data.user.role);
        }
    } catch (e) {
        console.warn("Could not verify session:", e);
    }
}

function applyRBAC(role) {
    // Hide or show confidential tabs/columns based on ISO/IEC 27001 RBAC rules
    const adminOnlyElements = document.querySelectorAll(".admin-only");
    const cashierOnlyElements = document.querySelectorAll(".cashier-only");

    if (role === "admin") {
        adminOnlyElements.forEach(el => el.style.display = "");
    } else {
        // Cashiers and Customers cannot see profit analytics or audit logs
        adminOnlyElements.forEach(el => el.style.display = "none");
        if (AppState.currentTab === "analytics-view" || AppState.currentTab === "audit-view") {
            switchTab("pos-view");
        }
    }
}

// Global Toast Notification Helper
function showToast(message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    const bg = type === "danger" ? "#f43f5e" : (type === "warning" ? "#f59e0b" : (type === "info" ? "#3b82f6" : "#10b981"));
    toast.style.cssText = `background:${bg};color:#fff;padding:12px 18px;border-radius:8px;font-size:14px;font-weight:600;box-shadow:0 4px 15px rgba(0,0,0,0.3);display:flex;align-items:center;gap:10px;animation:fadeIn 0.2s ease-out;`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

window.AppState = AppState;
window.switchTab = switchTab;
window.showToast = showToast;
