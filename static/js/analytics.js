/**
 * Sulit Store Profit Intelligence & Financial Analytics Controller
 * Interactive Chart.js graphs displaying daily, weekly, and monthly gross profit
 * ISO/IEC 27001: Strict role restriction (Admin only)
 */

let revenueMarginChartInstance = null;
let categoryDonutChartInstance = null;

async function loadAnalytics() {
    if (window.AppState.currentUser.role !== "admin") {
        showToast("Access Denied: Financial analytics are restricted to store administrators.", "danger");
        window.switchTab("pos-view");
        return;
    }

    try {
        const res = await fetch("/api/analytics/summary");
        const data = await res.json();

        if (data.success) {
            renderKPICards(data.kpis);
            renderRevenueMarginChart(data.daily_trends);
            renderCategoryDonutChart(data.category_profits);
            renderTopSellers(data.top_sellers);
        } else {
            showToast(data.message || "Failed to load financial metrics", "danger");
        }
    } catch (err) {
        console.error("Analytics fetch error:", err);
    }
}

function renderKPICards(kpis) {
    const revEl = document.getElementById("kpi-gross-revenue");
    const cogsEl = document.getElementById("kpi-total-cogs");
    const marginEl = document.getElementById("kpi-gross-margin");
    const marginPctEl = document.getElementById("kpi-margin-pct");
    const ordersEl = document.getElementById("kpi-total-orders");

    if (revEl) revEl.textContent = `₱${kpis.gross_revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    if (cogsEl) cogsEl.textContent = `₱${kpis.total_cogs.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    if (marginEl) marginEl.textContent = `₱${kpis.gross_margin.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    if (marginPctEl) marginPctEl.textContent = `${kpis.margin_percentage.toFixed(1)}%`;
    if (ordersEl) ordersEl.textContent = kpis.total_orders;
}

function renderRevenueMarginChart(trends) {
    const canvas = document.getElementById("financial-trends-chart");
    if (!canvas) return;

    if (revenueMarginChartInstance) {
        revenueMarginChartInstance.destroy();
    }

    const isDark = window.AppState.theme === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
    const textColor = isDark ? "#94a3b8" : "#475569";

    const ctx = canvas.getContext("2d");
    revenueMarginChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: trends.labels,
            datasets: [
                {
                    label: "Gross Revenue (₱)",
                    data: trends.revenue,
                    backgroundColor: "rgba(6, 182, 212, 0.7)", // Cyan
                    borderColor: "#06b6d4",
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: "Cost of Goods Sold (COGS)",
                    data: trends.cogs,
                    backgroundColor: "rgba(245, 158, 11, 0.6)", // Amber
                    borderColor: "#f59e0b",
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: "Gross Profit Margin (₱)",
                    data: trends.gross_margin,
                    type: "line",
                    borderColor: "#10b981", // Emerald
                    backgroundColor: "rgba(16, 185, 129, 0.15)",
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointBackgroundColor: "#10b981",
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    position: "top",
                    labels: { color: textColor, font: { family: "Inter", size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ₱${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { family: "Inter", size: 11 } }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textColor,
                        callback: val => `₱${val}`
                    }
                }
            }
        }
    });
}

function renderCategoryDonutChart(catData) {
    const canvas = document.getElementById("category-profit-chart");
    if (!canvas) return;

    if (categoryDonutChartInstance) {
        categoryDonutChartInstance.destroy();
    }

    const isDark = window.AppState.theme === "dark";
    const textColor = isDark ? "#f8fafc" : "#0f172a";

    const ctx = canvas.getContext("2d");
    categoryDonutChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.margins,
                backgroundColor: [
                    "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6",
                    "#ec4899", "#f59e0b", "#14b8a6", "#6366f1"
                ],
                borderWidth: 2,
                borderColor: isDark ? "#111827" : "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: textColor, font: { family: "Inter", size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ₱${context.raw.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            cutout: "68%"
        }
    });
}

function renderTopSellers(sellers) {
    const tbody = document.getElementById("top-sellers-table-body");
    if (!tbody) return;

    tbody.innerHTML = sellers.map((s, idx) => `
        <tr>
            <td><strong style="color:var(--brand-primary);">${idx + 1}</strong></td>
            <td><strong>${s.product_name}</strong></td>
            <td><span class="badge badge-info">${s.sku}</span></td>
            <td><strong>${s.total_qty} units</strong></td>
            <td><strong style="color:var(--brand-secondary);">₱${s.total_revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong></td>
        </tr>
    `).join("");
}

window.loadAnalytics = loadAnalytics;
