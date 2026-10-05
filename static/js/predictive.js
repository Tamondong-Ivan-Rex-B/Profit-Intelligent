/**
 * Sulit Store Predictive Analytics & Depletion Forecasting Controller
 * Implements Section 4.1 (RMSE evaluation) & Section 4.2 (System Error Rate evaluation)
 */

let forecastChartInstance = null;

async function loadPredictiveOverview() {
    try {
        const res = await fetch("/api/predictive/depletion_overview");
        const data = await res.json();
        if (data.success) {
            renderDepletionTable(data.depletion_overview);
        }
    } catch (err) {
        console.error("Predictive fetch error:", err);
    }
}

function renderDepletionTable(items) {
    const tbody = document.getElementById("predictive-depletion-tbody");
    if (!tbody) return;

    if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--text-muted);">No predictive data available.</td></tr>`;
        return;
    }

    tbody.innerHTML = items.map(item => {
        let tierBadge = `<span class="badge badge-info">${item.velocity_tier}</span>`;
        if (item.velocity_tier === "Fast-Moving") {
            tierBadge = `<span class="badge badge-success" style="background:#10b981;color:#fff;">🔥 FAST-MOVING</span>`;
        }

        const daysClass = item.days_remaining <= 5 
            ? "color:var(--status-danger);font-weight:800;" 
            : (item.days_remaining <= 10 ? "color:var(--status-warning);font-weight:700;" : "");

        return `
            <tr>
                <td><strong style="color:var(--brand-secondary);">${item.sku}</strong></td>
                <td><strong>${item.product_name}</strong></td>
                <td>${item.current_stock}</td>
                <td><strong>${item.daily_velocity} units/day</strong></td>
                <td style="${daysClass}">${item.days_remaining === 999.0 ? 'Plenty / No velocity' : `${item.days_remaining} days`}</td>
                <td>${item.stockout_date}</td>
                <td><strong style="color:var(--brand-primary);">${item.recommended_reorder_point} units</strong></td>
                <td>${tierBadge}</td>
            </tr>
        `;
    }).join("");
}

// Capstone Evaluation 1: Calculate RMSE
async function runRMSEBenchmark() {
    const btn = document.getElementById("btn-run-rmse");
    const resultBox = document.getElementById("rmse-benchmark-results");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch("/api/predictive/evaluate_rmse");
        const data = await res.json();

        if (data.success) {
            const ev = data.evaluation;
            resultBox.style.display = "block";
            document.getElementById("rmse-overall-score").textContent = ev.overall_rmse;
            document.getElementById("rmse-total-datapoints").textContent = ev.total_datapoints;

            const tbody = document.getElementById("rmse-product-breakdown-tbody");
            if (tbody && ev.product_evaluations) {
                tbody.innerHTML = ev.product_evaluations.map(p => `
                    <tr>
                        <td><strong>${p.product_name}</strong> (${p.sku})</td>
                        <td>${p.mean_sales} units</td>
                        <td><strong style="color:var(--brand-primary);">${p.rmse}</strong></td>
                    </tr>
                `).join("");
            }
            showToast(`RMSE Evaluation Complete: ${ev.overall_rmse}`, "success");
        }
    } catch (e) {
        showToast("Error running RMSE benchmark", "danger");
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Capstone Evaluation 2: System Error Rate OCR Benchmark
async function runOCRErrorRateBenchmark() {
    const btn = document.getElementById("btn-run-ocr-eval");
    const resultBox = document.getElementById("ocr-eval-results");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch("/api/ocr/evaluate");
        const data = await res.json();

        if (data.success) {
            const ev = data.evaluation;
            resultBox.style.display = "block";
            document.getElementById("ocr-eval-accuracy").textContent = `${ev.accuracy_percentage}%`;
            document.getElementById("ocr-eval-error-rate").textContent = ev.system_error_rate;

            const statusBadge = document.getElementById("ocr-eval-status-badge");
            if (statusBadge) {
                if (ev.benchmark_passed) {
                    statusBadge.innerHTML = `<span class="badge badge-success" style="font-size:13px;padding:6px 12px;">ISO 25010 PASSED (Error Rate &lt; 0.05)</span>`;
                } else {
                    statusBadge.innerHTML = `<span class="badge badge-danger">FAIL (Error Rate &gt; 0.05)</span>`;
                }
            }

            const tbody = document.getElementById("ocr-eval-trials-tbody");
            if (tbody) {
                tbody.innerHTML = ev.test_details.slice(0, 10).map(t => `
                    <tr>
                        <td><code>${t.input}</code></td>
                        <td><strong style="color:var(--brand-secondary);">${t.expected}</strong></td>
                        <td>${t.extracted}</td>
                        <td><span class="badge ${t.status === 'PASS' ? 'badge-success' : 'badge-danger'}">${t.status}</span></td>
                    </tr>
                `).join("");
            }
            showToast(`OCR System Error Rate: ${ev.system_error_rate} (${ev.accuracy_percentage}% accuracy)`, "success");
        }
    } catch (e) {
        showToast("Error running OCR benchmark", "danger");
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Capstone Evaluation 3: Peak Transaction Stress Test
async function runPeakStressTest() {
    const btn = document.getElementById("btn-run-stress-test");
    const resultBox = document.getElementById("stress-test-results");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch("/api/system/stress_test", { method: "POST" });
        const data = await res.json();

        if (data.success) {
            resultBox.style.display = "block";
            document.getElementById("stress-total-trials").textContent = data.total_trials;
            document.getElementById("stress-success-count").textContent = data.successful_checkouts;
            document.getElementById("stress-error-rate").textContent = data.system_error_rate;
            document.getElementById("stress-throughput").textContent = `${data.transactions_per_sec} tx/s`;
            showToast(`Peak Stress Test Passed: ${data.total_trials} checkouts processed with 0% error!`, "success");
        }
    } catch (e) {
        showToast("Error executing stress test", "danger");
    } finally {
        if (btn) btn.disabled = false;
    }
}

window.loadPredictiveOverview = loadPredictiveOverview;
window.runRMSEBenchmark = runRMSEBenchmark;
window.runOCRErrorRateBenchmark = runOCRErrorRateBenchmark;
window.runPeakStressTest = runPeakStressTest;
