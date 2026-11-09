/**
 * FoodDNA - Shopping Cart Frontend Logic (Phase 6).
 */

async function initCartPage() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }
    if (user.role !== "customer") {
        const msg = document.getElementById("cartMessage");
        showMessage(msg, "warning", "Only customers can access the shopping cart.");
        return;
    }

    loadCart();
}

async function loadCart() {
    const container = document.getElementById("cartContent");
    const msg = document.getElementById("cartMessage");
    const headerActions = document.getElementById("cartHeaderActions");
    clearMessage(msg);
    headerActions.replaceChildren();

    container.replaceChildren();
    const loading = document.createElement("div");
    loading.className = "text-center py-5 text-secondary";
    loading.textContent = "Loading cart contents...";
    container.appendChild(loading);

    const res = await fetchCart();
    if (!res.ok) {
        container.replaceChildren();
        showMessage(msg, "danger", res.data.error || "Could not retrieve cart.");
        return;
    }

    const cart = res.data.cart;
    if (cart.is_empty || !cart.items || cart.items.length === 0) {
        renderEmptyCart(container);
        return;
    }

    renderActiveCart(container, headerActions, cart);
}

function renderEmptyCart(container) {
    container.replaceChildren();
    const card = document.createElement("div");
    card.className = "fd-card p-5 text-center";

    const title = document.createElement("h2");
    title.className = "h4 mb-2";
    title.textContent = "Your cart is empty";

    const desc = document.createElement("p");
    desc.className = "text-secondary mb-4";
    desc.textContent = "Explore our restaurants and discover delicious dishes crafted for your taste.";

    const btn = document.createElement("a");
    btn.className = "btn btn-fd px-4 py-2";
    btn.href = "menu.html";
    btn.textContent = "Browse Food Menu";

    card.append(title, desc, btn);
    container.appendChild(card);
}

function renderActiveCart(container, headerActions, cart) {
    container.replaceChildren();

    // Clear cart button in header
    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "btn btn-outline-danger btn-sm";
    clearBtn.textContent = "Clear Cart";
    clearBtn.addEventListener("click", async () => {
        if (confirm("Are you sure you want to remove all items from your cart?")) {
            setBusy(clearBtn, true, "Clearing...");
            const res = await clearCart();
            setBusy(clearBtn, false);
            if (res.ok) {
                showToast("Cart cleared.");
                loadCart();
            } else {
                alert(res.data.error || "Could not clear cart.");
            }
        }
    });
    headerActions.appendChild(clearBtn);

    const row = document.createElement("div");
    row.className = "row g-4";

    // Left column: Restaurant banner & Cart items table
    const leftCol = document.createElement("div");
    leftCol.className = "col-lg-8";

    if (cart.restaurant) {
        const restBanner = document.createElement("div");
        restBanner.className = "card mb-3 border-0 bg-white shadow-sm p-3 rounded-4";
        const restTitle = document.createElement("div");
        restTitle.className = "fw-semibold text-dark";
        restTitle.textContent = `Ordering from: ${cart.restaurant.name}`;
        const restAddress = document.createElement("div");
        restAddress.className = "small text-secondary";
        restAddress.textContent = cart.restaurant.address || "";
        restBanner.append(restTitle, restAddress);
        leftCol.appendChild(restBanner);
    }

    const itemsCard = document.createElement("div");
    itemsCard.className = "fd-card p-3 p-md-4";

    const listGroup = document.createElement("div");
    listGroup.className = "list-group list-group-flush";

    cart.items.forEach((item) => {
        const itemRow = document.createElement("div");
        itemRow.className = "list-group-item px-0 py-3 d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3";

        // Dish details
        const infoCol = document.createElement("div");
        infoCol.className = "flex-grow-1";

        const nameLine = document.createElement("div");
        nameLine.className = "fw-semibold";
        nameLine.textContent = item.name;

        const metaLine = document.createElement("div");
        metaLine.className = "small text-secondary";
        metaLine.textContent = `${formatPrice(item.price)} each \u00B7 ${item.cuisine || "Special"} (${item.food_type || ""})`;

        infoCol.append(nameLine, metaLine);

        // Quantity controls
        const qtyCol = document.createElement("div");
        qtyCol.className = "d-flex align-items-center gap-2";

        const decBtn = document.createElement("button");
        decBtn.type = "button";
        decBtn.className = "btn btn-outline-secondary btn-sm px-2";
        decBtn.textContent = "-";
        decBtn.setAttribute("aria-label", "Decrease quantity");
        decBtn.addEventListener("click", async () => {
            if (item.quantity <= 1) {
                if (confirm(`Remove "${item.name}" from cart?`)) {
                    setBusy(decBtn, true);
                    await removeCartItem(item.id);
                    loadCart();
                }
            } else {
                setBusy(decBtn, true);
                await updateCartItem(item.id, item.quantity - 1);
                loadCart();
            }
        });

        const qtyBadge = document.createElement("span");
        qtyBadge.className = "badge text-bg-light border px-3 py-2 fs-6";
        qtyBadge.textContent = String(item.quantity);

        const incBtn = document.createElement("button");
        incBtn.type = "button";
        incBtn.className = "btn btn-outline-secondary btn-sm px-2";
        incBtn.textContent = "+";
        incBtn.setAttribute("aria-label", "Increase quantity");
        incBtn.addEventListener("click", async () => {
            if (item.quantity >= 50) {
                alert("Maximum 50 items allowed per dish.");
                return;
            }
            setBusy(incBtn, true);
            await updateCartItem(item.id, item.quantity + 1);
            loadCart();
        });

        qtyCol.append(decBtn, qtyBadge, incBtn);

        // Line total and remove button
        const rightPart = document.createElement("div");
        rightPart.className = "d-flex align-items-center gap-3 text-end";

        const lineTotal = document.createElement("div");
        lineTotal.className = "fw-bold fs-6 fd-price";
        lineTotal.textContent = formatPrice(item.line_total);

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn-link text-danger p-0 text-decoration-none";
        removeBtn.textContent = "\u00D7 Remove";
        removeBtn.setAttribute("aria-label", `Remove ${item.name}`);
        removeBtn.addEventListener("click", async () => {
            if (confirm(`Remove "${item.name}" from your cart?`)) {
                setBusy(removeBtn, true, "Removing...");
                await removeCartItem(item.id);
                loadCart();
            }
        });

        rightPart.append(lineTotal, removeBtn);

        itemRow.append(infoCol, qtyCol, rightPart);
        listGroup.appendChild(itemRow);
    });

    itemsCard.appendChild(listGroup);
    leftCol.appendChild(itemsCard);

    // Right column: Charges breakdown & Checkout button
    const rightCol = document.createElement("div");
    rightCol.className = "col-lg-4";

    const summaryCard = document.createElement("div");
    summaryCard.className = "fd-card p-4";

    const summaryTitle = document.createElement("h2");
    summaryTitle.className = "h5 mb-3";
    summaryTitle.textContent = "Bill Details";

    const dl = document.createElement("dl");
    dl.className = "row mb-3";

    function addRow(label, value, bold = false) {
        const dt = document.createElement("dt");
        dt.className = `col-7 ${bold ? "fw-bold" : "text-secondary fw-normal"}`;
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.className = `col-5 text-end ${bold ? "fw-bold fs-5 fd-price" : ""}`;
        dd.textContent = formatPrice(value);
        dl.append(dt, dd);
    }

    addRow("Item Subtotal", cart.subtotal);
    addRow("Delivery Fee", cart.delivery_fee);

    const hr = document.createElement("hr");
    hr.className = "my-2";

    summaryCard.append(summaryTitle, dl, hr);

    const totalRow = document.createElement("div");
    totalRow.className = "d-flex justify-content-between align-items-center mb-4";
    const totalLabel = document.createElement("span");
    totalLabel.className = "fw-bold fs-5";
    totalLabel.textContent = "To Pay";
    const totalVal = document.createElement("span");
    totalVal.className = "fw-bold fs-4 fd-price";
    totalVal.textContent = formatPrice(cart.total_amount);
    totalRow.append(totalLabel, totalVal);
    summaryCard.appendChild(totalRow);

    const checkoutBtn = document.createElement("a");
    checkoutBtn.className = "btn btn-fd w-100 py-2 mb-2 fw-semibold";
    checkoutBtn.href = "checkout.html";
    checkoutBtn.textContent = "Proceed to Checkout";

    const continueBtn = document.createElement("a");
    continueBtn.className = "btn btn-outline-dark w-100 py-2 btn-sm";
    continueBtn.href = cart.restaurant
        ? `restaurant-menu.html?id=${encodeURIComponent(cart.restaurant.id)}`
        : "menu.html";
    continueBtn.textContent = "Continue Shopping";

    summaryCard.append(checkoutBtn, continueBtn);
    rightCol.appendChild(summaryCard);

    row.append(leftCol, rightCol);
    container.appendChild(row);
}
