/**
 * Sulit Store Inventory Management & Expiration Tracking Controller
 * RBAC: Hides COGS and profit data from Cashier role (ISO/IEC 27001)
 * Integrates Computer Vision OCR for auto-filling expiration dates
 */

const Inventory = {
    products: [],
    alerts: {}
};

document.addEventListener("DOMContentLoaded", () => {
    initInventoryEvents();
});

function initInventoryEvents() {
    const searchInput = document.getElementById("inv-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            renderInventoryTable(e.target.value.toLowerCase());
        });
    }

    const filterCategory = document.getElementById("inv-filter-category");
    if (filterCategory) {
        filterCategory.addEventListener("change", () => {
            renderInventoryTable();
        });
    }

    const filterExpiry = document.getElementById("inv-filter-expiry");
    if (filterExpiry) {
        filterExpiry.addEventListener("change", () => {
            renderInventoryTable();
        });
    }
}

async function loadInventory() {
    try {
        const [prodRes, alertRes] = await Promise.all([
            fetch("/api/products"),
            fetch("/api/products/expiry_alerts")
        ]);

        const prodData = await prodRes.json();
        const alertData = await alertRes.json();

        if (prodData.success) {
            Inventory.products = prodData.products;
            populateCategoryFilter();
        }

        if (alertData.success) {
            Inventory.alerts = alertData;
            renderExpiryAlertCounters();
        }

        renderInventoryTable();
    } catch (err) {
        console.error("Failed to load inventory:", err);
    }
}

function renderExpiryAlertCounters() {
    const counts = Inventory.alerts.counts || { expired: 0, critical: 0, warning: 0, fresh: 0 };
    const expiredEl = document.getElementById("kpi-inv-expired");
    const nearExpiryEl = document.getElementById("kpi-inv-nearexpiry");
    const totalItemsEl = document.getElementById("kpi-inv-total");

    if (expiredEl) expiredEl.textContent = counts.expired;
    if (nearExpiryEl) nearExpiryEl.textContent = counts.critical + counts.warning;
    if (totalItemsEl) totalItemsEl.textContent = Inventory.products.length;
}

function populateCategoryFilter() {
    const filter = document.getElementById("inv-filter-category");
    if (!filter) return;

    const categories = [...new Set(Inventory.products.map(p => p.category))];
    filter.innerHTML = `<option value="ALL">All Categories</option>` + 
        categories.map(c => `<option value="${c}">${c}</option>`).join("");
}

function renderInventoryTable(searchQuery = "") {
    const tbody = document.getElementById("inventory-table-body");
    if (!tbody) return;

    const catFilter = document.getElementById("inv-filter-category")?.value || "ALL";
    const expFilter = document.getElementById("inv-filter-expiry")?.value || "ALL";
    const isAdmin = window.AppState.currentUser.role === "admin";

    const today = new Date();

    let filtered = Inventory.products.filter(p => {
        const matchSearch = p.product_name.toLowerCase().includes(searchQuery) ||
                            p.sku.toLowerCase().includes(searchQuery) ||
                            p.category.toLowerCase().includes(searchQuery);
        const matchCat = catFilter === "ALL" || p.category === catFilter;
        
        // Expiry filter
        let matchExp = true;
        if (expFilter !== "ALL" && p.expiration_date) {
            const expDate = new Date(p.expiration_date);
            const daysLeft = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
            if (expFilter === "EXPIRED") matchExp = daysLeft < 0;
            else if (expFilter === "CRITICAL") matchExp = daysLeft >= 0 && daysLeft <= 14;
            else if (expFilter === "WARNING") matchExp = daysLeft > 14 && daysLeft <= 30;
            else if (expFilter === "SAFE") matchExp = daysLeft > 30;
        }

        return matchSearch && matchCat && matchExp;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted);">No inventory records found.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => {
        // Compute Expiration Badge
        let expBadge = `<span class="badge badge-info">NO DATE</span>`;
        if (p.expiration_date) {
            const expDate = new Date(p.expiration_date);
            const daysLeft = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
            if (daysLeft < 0) {
                expBadge = `<span class="badge badge-danger">EXPIRED (${Math.abs(daysLeft)}d ago)</span>`;
            } else if (daysLeft <= 14) {
                expBadge = `<span class="badge badge-danger" style="background:#dc2626;color:#fff;">CRITICAL (${daysLeft}d left)</span>`;
            } else if (daysLeft <= 30) {
                expBadge = `<span class="badge badge-warning">WARN (${daysLeft}d left)</span>`;
            } else {
                expBadge = `<span class="badge badge-success">FRESH (${daysLeft}d)</span>`;
            }
        }

        // Low stock highlight
        const isLow = p.current_stock_qty <= p.reorder_threshold;
        const stockDisplay = isLow 
            ? `<span style="color:var(--status-danger);font-weight:700;">${p.current_stock_qty} (LOW)</span>`
            : `<span>${p.current_stock_qty}</span>`;

        return `
            <tr>
                <td><strong style="font-family:monospace;color:var(--brand-secondary);">${p.sku}</strong></td>
                <td>
                    <div style="font-weight:600;">${p.product_name}</div>
                    <div style="font-size:11px;color:var(--text-muted);">${p.barcode || ''}</div>
                </td>
                <td><span class="badge badge-info">${p.category}</span></td>
                ${isAdmin ? `<td>₱${p.cost_price ? p.cost_price.toFixed(2) : '0.00'}</td>` : ''}
                <td><strong style="color:var(--brand-primary);">₱${p.retail_price.toFixed(2)}</strong></td>
                <td>${stockDisplay}</td>
                <td>
                    <div>${p.expiration_date || 'N/A'}</div>
                    <div style="margin-top:2px;">${expBadge}</div>
                </td>
                <td>
                    <div style="display:flex;gap:6px;">
                        <button class="btn btn-secondary btn-sm" onclick="openRestockModal('${p.sku}')">+ Stock</button>
                        ${isAdmin ? `<button class="btn btn-secondary btn-sm" onclick="openEditProductModal('${p.sku}')">Edit</button>` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

// Modal: Restock Inventory
function openRestockModal(sku) {
    const prod = Inventory.products.find(p => p.sku === sku);
    if (!prod) return;

    document.getElementById("restock-sku").value = prod.sku;
    document.getElementById("restock-title").textContent = prod.product_name;
    document.getElementById("restock-current-stock").textContent = prod.current_stock_qty;
    document.getElementById("restock-adjustment-input").value = "10";

    const modal = document.getElementById("restock-modal");
    if (modal) modal.classList.add("active");
}

function closeRestockModal() {
    const modal = document.getElementById("restock-modal");
    if (modal) modal.classList.remove("active");
}

async function submitRestock() {
    const sku = document.getElementById("restock-sku").value;
    const qty = parseInt(document.getElementById("restock-adjustment-input").value) || 0;
    const reason = document.getElementById("restock-reason").value;

    if (qty <= 0) {
        showToast("Restock quantity must be greater than zero", "warning");
        return;
    }

    try {
        const res = await fetch("/api/products/adjust_stock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sku: sku, adjustment: qty, reason: reason })
        });
        const data = await res.json();
        if (data.success) {
            closeRestockModal();
            loadInventory();
            showToast(`Added +${qty} units to inventory!`, "success");
        }
    } catch (e) {
        showToast("Error updating stock", "danger");
    }
}

// Modal: Add / Edit Product
function openAddProductModal() {
    document.getElementById("prod-modal-title").textContent = "Register New Retail Product";
    document.getElementById("prod-form-sku").value = `SKU-${Date.now().toString().slice(-6)}`;
    document.getElementById("prod-form-sku").readOnly = false;
    document.getElementById("prod-form-barcode").value = "";
    document.getElementById("prod-form-name").value = "";
    document.getElementById("prod-form-category").value = "Canned Goods";
    document.getElementById("prod-form-cost").value = "25.00";
    document.getElementById("prod-form-retail").value = "35.00";
    document.getElementById("prod-form-stock").value = "50";
    document.getElementById("prod-form-reorder").value = "15";
    document.getElementById("prod-form-expiry").value = "";

    const modal = document.getElementById("product-form-modal");
    if (modal) modal.classList.add("active");
}

function openEditProductModal(sku) {
    const prod = Inventory.products.find(p => p.sku === sku);
    if (!prod) return;

    document.getElementById("prod-modal-title").textContent = `Edit Product: ${prod.sku}`;
    document.getElementById("prod-form-sku").value = prod.sku;
    document.getElementById("prod-form-sku").readOnly = true;
    document.getElementById("prod-form-barcode").value = prod.barcode || "";
    document.getElementById("prod-form-name").value = prod.product_name;
    document.getElementById("prod-form-category").value = prod.category;
    document.getElementById("prod-form-cost").value = prod.cost_price || 0;
    document.getElementById("prod-form-retail").value = prod.retail_price;
    document.getElementById("prod-form-stock").value = prod.current_stock_qty;
    document.getElementById("prod-form-reorder").value = prod.reorder_threshold;
    document.getElementById("prod-form-expiry").value = prod.expiration_date || "";

    const modal = document.getElementById("product-form-modal");
    if (modal) modal.classList.add("active");
}

function closeProductFormModal() {
    const modal = document.getElementById("product-form-modal");
    if (modal) modal.classList.remove("active");
}

async function submitProductForm() {
    const sku = document.getElementById("prod-form-sku").value.trim();
    const barcode = document.getElementById("prod-form-barcode").value.trim();
    const name = document.getElementById("prod-form-name").value.trim();
    const category = document.getElementById("prod-form-category").value;
    const cost = parseFloat(document.getElementById("prod-form-cost").value) || 0;
    const retail = parseFloat(document.getElementById("prod-form-retail").value) || 0;
    const stock = parseInt(document.getElementById("prod-form-stock").value) || 0;
    const reorder = parseInt(document.getElementById("prod-form-reorder").value) || 10;
    const expiry = document.getElementById("prod-form-expiry").value || null;

    if (!sku || !name) {
        showToast("SKU and Product Name are required", "warning");
        return;
    }

    const payload = {
        sku, barcode, product_name: name, category,
        cost_price: cost, retail_price: retail,
        current_stock_qty: stock, reorder_threshold: reorder,
        expiration_date: expiry
    };

    const isEdit = document.getElementById("prod-form-sku").readOnly;
    const url = isEdit ? `/api/products/${sku}` : `/api/products`;
    const method = isEdit ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeProductFormModal();
            loadInventory();
            showToast(isEdit ? "Product updated successfully!" : "New product registered!", "success");
        } else {
            showToast(data.message || "Failed to save product", "danger");
        }
    } catch (e) {
        showToast("Server error saving product", "danger");
    }
}

window.loadInventory = loadInventory;
window.renderInventoryTable = renderInventoryTable;
window.openRestockModal = openRestockModal;
window.closeRestockModal = closeRestockModal;
window.submitRestock = submitRestock;
window.openAddProductModal = openAddProductModal;
window.openEditProductModal = openEditProductModal;
window.closeProductFormModal = closeProductFormModal;
window.submitProductForm = submitProductForm;
