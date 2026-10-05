/**
 * Sulit Store E-Commerce Pre-Ordering Storefront & SRP Price Monitor Controller
 * Allows customers to order items ahead of time for in-store pickup
 */

const Storefront = {
    catalog: [],
    cart: []
};

document.addEventListener("DOMContentLoaded", () => {
    initStorefrontEvents();
});

function initStorefrontEvents() {
    const payMethodSelect = document.getElementById("storefront-payment-method");
    if (payMethodSelect) {
        payMethodSelect.addEventListener("change", (e) => {
            const gcashBox = document.getElementById("storefront-gcash-box");
            if (gcashBox) {
                gcashBox.style.display = e.target.value === "GCash" ? "block" : "none";
            }
        });
    }
}

async function loadStorefront() {
    try {
        const res = await fetch("/api/storefront/catalog");
        const data = await res.json();
        if (data.success) {
            Storefront.catalog = data.catalog;
            renderStorefrontCatalog();
            loadPickupOrdersList();
        }
    } catch (e) {
        console.error("Storefront catalog load error:", e);
    }
}

function renderStorefrontCatalog() {
    const grid = document.getElementById("storefront-product-grid");
    if (!grid) return;

    if (Storefront.catalog.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:32px;color:var(--text-muted);">No in-stock items available right now.</div>`;
        return;
    }

    grid.innerHTML = Storefront.catalog.map(item => `
        <div class="product-tile glass-card">
            <div>
                <span class="tile-category">${item.category}</span>
                <h4 class="tile-title" style="font-size:15px;margin:8px 0;">${item.product_name}</h4>
                <div style="font-size:11px;color:var(--text-secondary);">SKU: ${item.sku}</div>
            </div>
            <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div class="tile-price">₱${item.retail_price.toFixed(2)}</div>
                    <div style="font-size:11px;color:var(--brand-primary);">In Stock: ${item.current_stock_qty} ${item.unit_measure || 'pcs'}</div>
                </div>
                <button class="btn btn-primary btn-sm" onclick="addStorefrontCart('${item.sku}')">
                    + Add to Cart
                </button>
            </div>
        </div>
    `).join("");
}

function addStorefrontCart(sku) {
    const item = Storefront.catalog.find(p => p.sku === sku);
    if (!item) return;

    const existing = Storefront.cart.find(c => c.sku === sku);
    if (existing) {
        if (existing.quantity + 1 > item.current_stock_qty) {
            showToast(`Cannot exceed in-store stock (${item.current_stock_qty})`, "warning");
            return;
        }
        existing.quantity += 1;
    } else {
        Storefront.cart.push({
            sku: item.sku,
            product_name: item.product_name,
            retail_price: item.retail_price,
            quantity: 1,
            max_stock: item.current_stock_qty
        });
    }

    renderStorefrontCart();
    showToast(`Added '${item.product_name}' to pickup cart!`, "info");
}

function updateStorefrontQty(sku, delta) {
    const existing = Storefront.cart.find(c => c.sku === sku);
    if (!existing) return;

    const newQty = existing.quantity + delta;
    if (newQty <= 0) {
        Storefront.cart = Storefront.cart.filter(c => c.sku !== sku);
    } else if (newQty > existing.max_stock) {
        showToast("Maximum available stock reached", "warning");
        return;
    } else {
        existing.quantity = newQty;
    }
    renderStorefrontCart();
}

function renderStorefrontCart() {
    const list = document.getElementById("storefront-cart-items");
    const totalEl = document.getElementById("storefront-cart-total");
    if (!list) return;

    if (Storefront.cart.length === 0) {
        list.innerHTML = `<div style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">Your pickup cart is empty.</div>`;
        if (totalEl) totalEl.textContent = "₱0.00";
        return;
    }

    let total = 0;
    list.innerHTML = Storefront.cart.map(item => {
        const lineTotal = item.retail_price * item.quantity;
        total += lineTotal;
        return `
            <div class="cart-item-row">
                <div class="cart-item-info">
                    <div class="cart-item-title">${item.product_name}</div>
                    <div class="cart-item-sub">₱${item.retail_price.toFixed(2)} each</div>
                </div>
                <div class="cart-qty-controls">
                    <button class="qty-btn" onclick="updateStorefrontQty('${item.sku}', -1)">-</button>
                    <span style="font-weight:700;font-size:13px;width:20px;text-align:center;">${item.quantity}</span>
                    <button class="qty-btn" onclick="updateStorefrontQty('${item.sku}', 1)">+</button>
                </div>
                <div class="cart-item-total">₱${lineTotal.toFixed(2)}</div>
            </div>
        `;
    }).join("");

    if (totalEl) totalEl.textContent = `₱${total.toFixed(2)}`;
}

async function submitStorefrontOrder() {
    if (Storefront.cart.length === 0) {
        showToast("Please add items to your cart first", "warning");
        return;
    }

    const name = document.getElementById("storefront-cust-name").value.trim();
    const phone = document.getElementById("storefront-cust-phone").value.trim();
    const payMethod = document.getElementById("storefront-payment-method").value;
    const gcashRef = document.getElementById("storefront-gcash-ref").value.trim();

    if (!name || !phone) {
        showToast("Please enter your name and contact phone number", "warning");
        return;
    }

    const payload = {
        customer_name: name,
        customer_phone: phone,
        payment_method: payMethod,
        gcash_ref_number: gcashRef,
        items: Storefront.cart.map(c => ({ sku: c.sku, quantity: c.quantity }))
    };

    try {
        const res = await fetch("/api/storefront/place_order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            Storefront.cart = [];
            renderStorefrontCart();
            loadStorefront();

            // Display Order Confirmation Modal
            document.getElementById("pickup-ref-number").textContent = data.order_reference;
            document.getElementById("pickup-cust-name").textContent = name;
            document.getElementById("pickup-total-amount").textContent = `₱${data.total_amount.toFixed(2)}`;
            document.getElementById("pickup-modal").classList.add("active");
            showToast("Pre-order placed successfully!", "success");
        } else {
            showToast(data.message || "Failed to place order", "danger");
        }
    } catch (e) {
        showToast("Error processing online pre-order", "danger");
    }
}

function closePickupModal() {
    const modal = document.getElementById("pickup-modal");
    if (modal) modal.classList.remove("active");
}

// Cashier Pickup Orders Queue
async function loadPickupOrdersList() {
    const tbody = document.getElementById("pickup-orders-queue-tbody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/pos/orders");
        const data = await res.json();

        if (data.success && data.orders) {
            if (data.orders.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-muted);">No online pre-orders in queue.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.orders.map(o => `
                <tr>
                    <td><strong style="font-family:monospace;color:var(--brand-secondary);">${o.receipt_number}</strong></td>
                    <td><strong>${o.customer_name}</strong><br><span style="font-size:11px;color:var(--text-muted);">${o.customer_phone || ''}</span></td>
                    <td><strong>₱${o.total_amount.toFixed(2)}</strong></td>
                    <td><span class="badge badge-info">${o.payment_method}</span></td>
                    <td><span class="badge ${o.order_status === 'Completed' ? 'badge-success' : 'badge-warning'}">${o.order_status}</span></td>
                    <td><span style="font-size:11px;">${o.transaction_timestamp}</span></td>
                    <td>
                        ${o.order_status === 'PendingPickup' ? `
                            <button class="btn btn-primary btn-sm" onclick="setOrderStatus('${o.receipt_number}', 'ReadyForPickup')">Mark Ready</button>
                        ` : ''}
                        ${o.order_status === 'ReadyForPickup' ? `
                            <button class="btn btn-primary btn-sm" onclick="setOrderStatus('${o.receipt_number}', 'Completed')">Complete Pickup</button>
                        ` : ''}
                        ${o.order_status === 'Completed' ? `<span style="color:var(--status-success);font-weight:700;">Claimed</span>` : ''}
                    </td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.warn("Error loading pickup queue:", e);
    }
}

async function setOrderStatus(refNo, status) {
    try {
        const res = await fetch(`/api/pos/orders/${refNo}/status`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: status })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Order status updated to ${status}!`, "success");
            loadPickupOrdersList();
        }
    } catch (e) {
        showToast("Error updating order status", "danger");
    }
}

// -----------------------------------------------------------------------------
// Suggested Retail Price (SRP) Monitor
// -----------------------------------------------------------------------------
async function loadSRPOverview() {
    try {
        const res = await fetch("/api/srp/overview");
        const data = await res.json();
        if (data.success) {
            renderSRPTable(data.srp_comparisons);
        }
    } catch (e) {
        console.error("SRP load error:", e);
    }
}

function renderSRPTable(items) {
    const tbody = document.getElementById("srp-comparison-tbody");
    if (!tbody) return;

    tbody.innerHTML = items.map(p => {
        let statusBadge = `<span class="badge badge-success">OPTIMAL</span>`;
        if (p.pricing_status.includes("Overpriced")) {
            statusBadge = `<span class="badge badge-danger">OVERPRICED</span>`;
        } else if (p.pricing_status.includes("Underpriced")) {
            statusBadge = `<span class="badge badge-warning">UNDERPRICED</span>`;
        }

        return `
            <tr>
                <td><strong style="color:var(--brand-secondary);">${p.sku}</strong></td>
                <td><strong>${p.product_name}</strong></td>
                <td>₱${p.cost_price.toFixed(2)}</td>
                <td><strong style="color:var(--brand-primary);">₱${p.current_retail_price.toFixed(2)}</strong></td>
                <td>₱${p.srp_min.toFixed(2)} - ₱${p.srp_max.toFixed(2)}</td>
                <td>${statusBadge}</td>
                <td style="font-size:12px;color:var(--text-secondary);">${p.recommendation}</td>
            </tr>
        `;
    }).join("");
}

async function syncSRPBenchmarks() {
    try {
        const res = await fetch("/api/srp/sync", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Synchronized DTI SRP benchmarks!", "success");
            loadSRPOverview();
        }
    } catch (e) {
        showToast("Error syncing SRP", "danger");
    }
}

// -----------------------------------------------------------------------------
// Security Audit Log (ISO/IEC 27001)
// -----------------------------------------------------------------------------
async function loadAuditLogs() {
    if (window.AppState.currentUser.role !== "admin") return;
    try {
        const res = await fetch("/api/audit/logs");
        const data = await res.json();
        if (data.success) {
            const tbody = document.getElementById("audit-logs-tbody");
            if (tbody) {
                tbody.innerHTML = data.logs.map(l => `
                    <tr>
                        <td style="font-size:11px;font-family:monospace;">${l.timestamp}</td>
                        <td><strong>${l.username}</strong></td>
                        <td><span class="badge badge-info">${l.action}</span></td>
                        <td><code>${l.resource}</code></td>
                        <td><span class="badge ${l.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${l.status}</span></td>
                        <td style="font-size:11px;color:var(--text-secondary);">${l.details}</td>
                    </tr>
                `).join("");
            }
        }
    } catch (e) {
        console.error("Audit log error:", e);
    }
}

window.loadStorefront = loadStorefront;
window.addStorefrontCart = addStorefrontCart;
window.updateStorefrontQty = updateStorefrontQty;
window.submitStorefrontOrder = submitStorefrontOrder;
window.closePickupModal = closePickupModal;
window.loadPickupOrdersList = loadPickupOrdersList;
window.setOrderStatus = setOrderStatus;
window.loadSRPOverview = loadSRPOverview;
window.syncSRPBenchmarks = syncSRPBenchmarks;
window.loadAuditLogs = loadAuditLogs;
