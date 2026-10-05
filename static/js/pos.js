/**
 * Sulit Store Point-of-Sale (POS) Cashier Controller
 * Multi-method payment: Cash (change math), GCash (QR code & ref), Debit
 * Instant 80mm Thermal Receipt Generator
 */

const POS = {
    products: [],
    cart: [],
    activeCategory: "ALL",
    paymentMethod: "Cash"
};

document.addEventListener("DOMContentLoaded", () => {
    initPOSEvents();
});

function initPOSEvents() {
    // Barcode & SKU text scanner input
    const barcodeInput = document.getElementById("pos-barcode-input");
    if (barcodeInput) {
        barcodeInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                const code = barcodeInput.value.trim();
                if (code) {
                    lookupAndAddToCart(code);
                    barcodeInput.value = "";
                }
            }
        });
    }

    // Live search filter
    const searchInput = document.getElementById("pos-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            renderPOSCatalog(e.target.value.toLowerCase());
        });
    }

    // Checkout modal trigger
    const checkoutBtn = document.getElementById("pos-checkout-btn");
    if (checkoutBtn) {
        checkoutBtn.addEventListener("click", () => {
            if (POS.cart.length === 0) {
                showToast("Cart is empty. Please add items first.", "warning");
                return;
            }
            openPaymentModal();
        });
    }

    // Clear cart button
    const clearBtn = document.getElementById("pos-clear-cart-btn");
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            POS.cart = [];
            renderCart();
            showToast("Cart cleared", "info");
        });
    }
}

async function loadPOSCatalog() {
    try {
        const res = await fetch("/api/products");
        const data = await res.json();
        if (data.success) {
            POS.products = data.products;
            renderCategories();
            renderPOSCatalog();
        }
    } catch (err) {
        console.error("Failed to load catalog:", err);
    }
}

function renderCategories() {
    const container = document.getElementById("pos-category-pills");
    if (!container) return;

    const categories = ["ALL", ...new Set(POS.products.map(p => p.category))];
    container.innerHTML = categories.map(cat => `
        <button class="category-pill ${cat === POS.activeCategory ? 'active' : ''}" 
                onclick="filterCategory('${cat}')">
            ${cat}
        </button>
    `).join("");
}

function filterCategory(cat) {
    POS.activeCategory = cat;
    renderCategories();
    renderPOSCatalog();
}

function renderPOSCatalog(searchQuery = "") {
    const grid = document.getElementById("pos-product-grid");
    if (!grid) return;

    let filtered = POS.products;
    if (POS.activeCategory !== "ALL") {
        filtered = filtered.filter(p => p.category === POS.activeCategory);
    }
    if (searchQuery) {
        filtered = filtered.filter(p => 
            p.product_name.toLowerCase().includes(searchQuery) ||
            p.sku.toLowerCase().includes(searchQuery) ||
            (p.barcode && p.barcode.includes(searchQuery))
        );
    }

    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">No products found matching your search.</div>`;
        return;
    }

    grid.innerHTML = filtered.map(p => `
        <div class="product-tile" onclick="addToCart('${p.sku}')">
            <div>
                <span class="tile-category">${p.category}</span>
                <h4 class="tile-title">${p.product_name}</h4>
            </div>
            <div>
                <div class="tile-price">₱${p.retail_price.toFixed(2)}</div>
                <div class="tile-stock">Stock: ${p.current_stock_qty} ${p.unit_measure || 'pcs'}</div>
            </div>
        </div>
    `).join("");
}

async function lookupAndAddToCart(code) {
    try {
        const res = await fetch(`/api/pos/lookup/${encodeURIComponent(code)}`);
        const data = await res.json();
        if (data.success && data.product) {
            addToCart(data.product.sku);
            showToast(`Added: ${data.product.product_name}`, "success");
        } else {
            showToast(`Item not found for code: ${code}`, "danger");
        }
    } catch (e) {
        showToast("Error scanning product", "danger");
    }
}

function addToCart(sku) {
    const prod = POS.products.find(p => p.sku === sku);
    if (!prod) return;

    if (prod.current_stock_qty <= 0) {
        showToast(`'${prod.product_name}' is currently OUT OF STOCK!`, "danger");
        return;
    }

    const existing = POS.cart.find(item => item.sku === sku);
    if (existing) {
        if (existing.quantity + 1 > prod.current_stock_qty) {
            showToast(`Cannot exceed available stock (${prod.current_stock_qty})`, "warning");
            return;
        }
        existing.quantity += 1;
    } else {
        POS.cart.push({
            sku: prod.sku,
            product_name: prod.product_name,
            retail_price: prod.retail_price,
            quantity: 1,
            max_stock: prod.current_stock_qty
        });
    }
    renderCart();
}

function updateCartQty(sku, delta) {
    const item = POS.cart.find(i => i.sku === sku);
    if (!item) return;

    const newQty = item.quantity + delta;
    if (newQty <= 0) {
        POS.cart = POS.cart.filter(i => i.sku !== sku);
    } else if (newQty > item.max_stock) {
        showToast(`Cannot exceed available stock (${item.max_stock})`, "warning");
        return;
    } else {
        item.quantity = newQty;
    }
    renderCart();
}

function renderCart() {
    const list = document.getElementById("pos-cart-items");
    const subtotalEl = document.getElementById("pos-cart-subtotal");
    const totalEl = document.getElementById("pos-cart-total");
    const countBadge = document.getElementById("pos-cart-count");

    if (!list) return;

    if (POS.cart.length === 0) {
        list.innerHTML = `<div style="text-align:center;padding:36px;color:var(--text-muted);font-size:13px;">Cart is empty. Click items or scan barcode.</div>`;
        if (subtotalEl) subtotalEl.textContent = "₱0.00";
        if (totalEl) totalEl.textContent = "₱0.00";
        if (countBadge) countBadge.textContent = "0";
        return;
    }

    let subtotal = 0;
    let itemCount = 0;

    list.innerHTML = POS.cart.map(item => {
        const lineTotal = item.retail_price * item.quantity;
        subtotal += lineTotal;
        itemCount += item.quantity;

        return `
            <div class="cart-item-row">
                <div class="cart-item-info">
                    <div class="cart-item-title">${item.product_name}</div>
                    <div class="cart-item-sub">₱${item.retail_price.toFixed(2)} / unit</div>
                </div>
                <div class="cart-qty-controls">
                    <button class="qty-btn" onclick="updateCartQty('${item.sku}', -1)">-</button>
                    <span style="font-size:13px;font-weight:700;width:20px;text-align:center;">${item.quantity}</span>
                    <button class="qty-btn" onclick="updateCartQty('${item.sku}', 1)">+</button>
                </div>
                <div class="cart-item-total">₱${lineTotal.toFixed(2)}</div>
            </div>
        `;
    }).join("");

    if (subtotalEl) subtotalEl.textContent = `₱${subtotal.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `₱${subtotal.toFixed(2)}`;
    if (countBadge) countBadge.textContent = itemCount;
}

// Payment Modal Controller
function openPaymentModal() {
    const modal = document.getElementById("payment-modal");
    if (!modal) return;

    const total = POS.cart.reduce((sum, item) => sum + (item.retail_price * item.quantity), 0);
    document.getElementById("payment-modal-total").textContent = `₱${total.toFixed(2)}`;

    // Set default tendered
    const tenderedInput = document.getElementById("payment-tendered-input");
    tenderedInput.value = total.toFixed(2);
    updateChangeMath();

    modal.classList.add("active");
    selectPaymentMethod("Cash");
}

function closePaymentModal() {
    const modal = document.getElementById("payment-modal");
    if (modal) modal.classList.remove("active");
}

function selectPaymentMethod(method) {
    POS.paymentMethod = method;

    document.querySelectorAll(".pay-method-tab").forEach(tab => {
        if (tab.getAttribute("data-method") === method) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });

    const cashPanel = document.getElementById("pay-method-cash-panel");
    const gcashPanel = document.getElementById("pay-method-gcash-panel");
    const debitPanel = document.getElementById("pay-method-debit-panel");

    if (cashPanel) cashPanel.style.display = method === "Cash" ? "block" : "none";
    if (gcashPanel) gcashPanel.style.display = method === "GCash" ? "block" : "none";
    if (debitPanel) debitPanel.style.display = method === "Debit" ? "block" : "none";
}

function updateChangeMath() {
    const total = POS.cart.reduce((sum, item) => sum + (item.retail_price * item.quantity), 0);
    const tendered = parseFloat(document.getElementById("payment-tendered-input").value) || 0;
    const change = tendered - total;
    const changeEl = document.getElementById("payment-change-display");

    if (changeEl) {
        if (change < 0) {
            changeEl.textContent = `Short by: ₱${Math.abs(change).toFixed(2)}`;
            changeEl.style.color = "var(--status-danger)";
        } else {
            changeEl.textContent = `₱${change.toFixed(2)}`;
            changeEl.style.color = "var(--brand-primary)";
        }
    }
}

function setQuickCash(amount) {
    const total = POS.cart.reduce((sum, item) => sum + (item.retail_price * item.quantity), 0);
    const tenderedInput = document.getElementById("payment-tendered-input");
    if (amount === "exact") {
        tenderedInput.value = total.toFixed(2);
    } else {
        tenderedInput.value = amount.toFixed(2);
    }
    updateChangeMath();
}

async function submitCheckout() {
    const total = POS.cart.reduce((sum, item) => sum + (item.retail_price * item.quantity), 0);
    let tendered = total;
    let gcashRef = "";

    if (POS.paymentMethod === "Cash") {
        tendered = parseFloat(document.getElementById("payment-tendered-input").value) || 0;
        if (tendered < total) {
            showToast("Amount tendered is less than total amount!", "danger");
            return;
        }
    } else if (POS.paymentMethod === "GCash") {
        gcashRef = document.getElementById("payment-gcash-ref-input").value.trim();
        if (!gcashRef) {
            showToast("Please enter the GCash Reference Number", "warning");
            return;
        }
    }

    const payload = {
        items: POS.cart.map(i => ({ sku: i.sku, quantity: i.quantity })),
        payment_method: POS.paymentMethod,
        amount_tendered: tendered,
        gcash_ref_number: gcashRef,
        customer_name: "Walk-in Customer",
        terminal_id: "TERM-01"
    };

    try {
        const res = await fetch("/api/pos/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            closePaymentModal();
            POS.cart = [];
            renderCart();
            loadPOSCatalog(); // Refresh live stock counts
            showToast(`Transaction completed! Receipt #${data.receipt_number}`, "success");
            showReceiptModal(data.receipt_number);
        } else {
            showToast(data.message || "Checkout failed", "danger");
        }
    } catch (e) {
        showToast("Network error during checkout", "danger");
    }
}

async function showReceiptModal(receiptNo) {
    try {
        const res = await fetch(`/api/pos/receipt/${receiptNo}`);
        const data = await res.json();
        if (!data.success) return;

        const r = data.receipt;
        const container = document.getElementById("printable-receipt-content");
        if (!container) return;

        container.innerHTML = `
            <div class="receipt-container">
                <div class="receipt-header">
                    <div class="receipt-store-title">${r.store_name}</div>
                    <div class="receipt-meta">${r.store_address}</div>
                    <div class="receipt-meta">Tel: ${r.store_contact} | TIN: ${r.tin}</div>
                    <div class="receipt-meta" style="margin-top:6px;font-weight:700;">OFFICIAL SALES INVOICE</div>
                </div>

                <div class="receipt-info-grid">
                    <div class="receipt-info-row">
                        <span>Receipt No:</span>
                        <strong style="color:#000;">${r.receipt_number}</strong>
                    </div>
                    <div class="receipt-info-row">
                        <span>Terminal:</span>
                        <span>${r.terminal_id}</span>
                    </div>
                    <div class="receipt-info-row">
                        <span>Cashier:</span>
                        <span>${r.cashier}</span>
                    </div>
                    <div class="receipt-info-row">
                        <span>Date/Time:</span>
                        <span>${r.timestamp}</span>
                    </div>
                </div>

                <table class="receipt-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th class="col-right">Qty</th>
                            <th class="col-right">Price</th>
                            <th class="col-right">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${r.items.map(i => `
                            <tr>
                                <td>${i.product_name}</td>
                                <td class="col-right">${i.quantity_sold}</td>
                                <td class="col-right">${i.unit_retail_price.toFixed(2)}</td>
                                <td class="col-right">${i.line_total.toFixed(2)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>

                <div class="receipt-totals">
                    <div class="receipt-total-row receipt-grand-total">
                        <span>TOTAL AMOUNT:</span>
                        <span>₱${r.total_amount.toFixed(2)}</span>
                    </div>
                    <div class="receipt-total-row">
                        <span>Payment Method:</span>
                        <span>${r.payment_method}</span>
                    </div>
                    ${r.payment_method === 'Cash' ? `
                        <div class="receipt-total-row">
                            <span>Cash Tendered:</span>
                            <span>₱${r.amount_tendered.toFixed(2)}</span>
                        </div>
                        <div class="receipt-total-row">
                            <span>Change Due:</span>
                            <span style="font-weight:700;">₱${r.change_given.toFixed(2)}</span>
                        </div>
                    ` : ''}
                    ${r.gcash_ref_number ? `
                        <div class="receipt-total-row">
                            <span>GCash Ref No:</span>
                            <span style="font-family:monospace;">${r.gcash_ref_number}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="receipt-footer">
                    <div class="receipt-barcode">*${r.receipt_number}*</div>
                    <div>Thank you for shopping at Sulit Store!</div>
                    <div style="font-size:9px;margin-top:4px;">Software Design Capstone - TIP Quezon City</div>
                </div>
            </div>
        `;

        const modal = document.getElementById("printable-receipt-modal");
        if (modal) modal.classList.add("active");
    } catch (e) {
        console.error("Error generating receipt view:", e);
    }
}

function printReceipt() {
    window.print();
}

function closeReceiptModal() {
    const modal = document.getElementById("printable-receipt-modal");
    if (modal) modal.classList.remove("active");
}

window.loadPOSCatalog = loadPOSCatalog;
window.filterCategory = filterCategory;
window.addToCart = addToCart;
window.updateCartQty = updateCartQty;
window.openPaymentModal = openPaymentModal;
window.closePaymentModal = closePaymentModal;
window.selectPaymentMethod = selectPaymentMethod;
window.updateChangeMath = updateChangeMath;
window.setQuickCash = setQuickCash;
window.submitCheckout = submitCheckout;
window.printReceipt = printReceipt;
window.closeReceiptModal = closeReceiptModal;
window.showReceiptModal = showReceiptModal;
