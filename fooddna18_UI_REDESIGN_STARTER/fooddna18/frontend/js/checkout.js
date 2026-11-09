/**
 * FoodDNA - Checkout Frontend Logic (Phase 6).
 */

async function initCheckoutPage() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }
    if (user.role !== "customer") {
        const msg = document.getElementById("checkoutMessage");
        showMessage(msg, "warning", "Only customers can place food orders.");
        return;
    }

    const container = document.getElementById("checkoutContent");
    const msg = document.getElementById("checkoutMessage");

    container.replaceChildren();
    const loading = document.createElement("div");
    loading.className = "text-center py-5 text-secondary";
    loading.textContent = "Loading checkout details...";
    container.appendChild(loading);

    const res = await fetchCart();
    if (!res.ok) {
        container.replaceChildren();
        showMessage(msg, "danger", res.data.error || "Could not retrieve cart.");
        return;
    }

    const cart = res.data.cart;
    if (cart.is_empty || !cart.items || cart.items.length === 0) {
        container.replaceChildren();
        showMessage(
            msg,
            "info",
            "Your cart is empty. Please add items from the menu before checking out."
        );
        const backBtn = document.createElement("a");
        backBtn.className = "btn btn-fd mt-3";
        backBtn.href = "menu.html";
        backBtn.textContent = "Browse Menu";
        container.appendChild(backBtn);
        return;
    }

    const offersResult = await apiRequest("/api/offers");
    const offers = offersResult.ok ? (offersResult.data.offers || []).filter(o => Number(o.restaurant_id) === Number(cart.restaurant?.id)) : [];
    renderCheckoutForm(container, msg, cart, offers);
}

function renderCheckoutForm(container, msg, cart, offers = []) {
    let selectedOffer = null;
    let offerSelect = null;
    let discountDisplay = null;
    let totalDisplay = null;
    let totalToPay = Number(cart.total_amount);
    container.replaceChildren();

    const row = document.createElement("div");
    row.className = "row g-4";

    // Left column: Delivery Address & Payment Method
    const leftCol = document.createElement("div");
    leftCol.className = "col-lg-7";

    const formCard = document.createElement("div");
    formCard.className = "fd-card p-4 mb-4";

    const formTitle = document.createElement("h2");
    formTitle.className = "h5 mb-3";
    formTitle.textContent = "1. Delivery Information";

    const addressGroup = document.createElement("div");
    addressGroup.className = "mb-4";

    const addressLabel = document.createElement("label");
    addressLabel.className = "form-label fw-semibold";
    addressLabel.htmlFor = "deliveryAddressInput";
    addressLabel.textContent = "Delivery Address *";

    const addressInput = document.createElement("textarea");
    addressInput.id = "deliveryAddressInput";
    addressInput.className = "form-control";
    addressInput.rows = 4;
    addressInput.placeholder = "Enter your complete street address, house/flat number, landmark and city...";
    addressInput.required = true;
    addressInput.maxLength = 500;

    const charCounter = document.createElement("div");
    charCounter.className = "form-text text-end";
    charCounter.textContent = "Minimum 10 characters (0 / 500)";

    addressInput.addEventListener("input", () => {
        const len = addressInput.value.trim().length;
        charCounter.textContent = `Minimum 10 characters (${len} / 500)`;
        if (len >= 10) {
            addressInput.classList.remove("is-invalid");
        }
    });

    addressGroup.append(addressLabel, addressInput, charCounter);
    formCard.append(formTitle, addressGroup);

    // Payment Section
    const paymentTitle = document.createElement("h2");
    paymentTitle.className = "h5 mb-3";
    paymentTitle.textContent = "2. Payment Method";

    const paymentBox = document.createElement("div");
    paymentBox.className = "p-3 border rounded-3 bg-light mb-3";

    const codOption = document.createElement("div");
    codOption.className = "form-check";

    const codRadio = document.createElement("input");
    codRadio.className = "form-check-input";
    codRadio.type = "radio";
    codRadio.name = "paymentMethod";
    codRadio.id = "paymentCod";
    codRadio.value = "cash_on_delivery";
    codRadio.checked = true;

    const codLabel = document.createElement("label");
    codLabel.className = "form-check-label fw-semibold";
    codLabel.htmlFor = "paymentCod";
    codLabel.textContent = "Cash on Delivery (COD)";

    const codDesc = document.createElement("p");
    codDesc.className = "small text-secondary mb-0 mt-1";
    codDesc.textContent = "Pay with cash or UPI when your food arrives. Payment status will remain pending until received.";

    codOption.append(codRadio, codLabel, codDesc);
    paymentBox.appendChild(codOption);

    const onlineNote = document.createElement("div");
    onlineNote.className = "small text-muted mb-4";
    onlineNote.textContent = "\u2139 Online credit/debit card and net-banking integration is coming in a future release.";

    // Order Confirmation Submit Button
    const submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.id = "placeOrderBtn";
    submitBtn.className = "btn btn-fd w-100 py-3 fs-5 fw-semibold shadow-sm";
    submitBtn.textContent = `Place Order (${formatPrice(cart.total_amount)})`;

    submitBtn.addEventListener("click", async () => {
        clearMessage(msg);
        const address = addressInput.value.trim();

        if (address.length < 10) {
            addressInput.classList.add("is-invalid");
            showMessage(msg, "danger", "Please enter a valid delivery address with at least 10 characters.");
            addressInput.focus();
            return;
        }

        const confirmed = confirm(
            `Please confirm your order:\n\n` +
            `Restaurant: ${cart.restaurant ? cart.restaurant.name : "Restaurant"}\n` +
            `Total: ${formatPrice(totalToPay.toFixed(2))}\n` +
            `Payment: Cash on Delivery\n` +
            `Deliver to: ${address}\n\n` +
            `Proceed to place this order?`
        );
        if (!confirmed) {
            return;
        }

        setBusy(submitBtn, true, "Placing your order...");
        const res = await placeOrder(address, "cash_on_delivery", selectedOffer ? selectedOffer.id : null);
        setBusy(submitBtn, false);

        if (res.ok && res.data.order) {
            window.location.href = `order-details.html?id=${encodeURIComponent(res.data.order.id)}&placed=1`;
        } else {
            showMessage(
                msg,
                "danger",
                res.data.error || "Failed to place order. Please verify your cart and try again."
            );
        }
    });

    formCard.append(paymentTitle, paymentBox, onlineNote, submitBtn);
    leftCol.appendChild(formCard);

    // Right column: Order Summary Card
    const rightCol = document.createElement("div");
    rightCol.className = "col-lg-5";

    const summaryCard = document.createElement("div");
    summaryCard.className = "fd-card p-4";

    const summaryTitle = document.createElement("h2");
    summaryTitle.className = "h5 mb-3";
    summaryTitle.textContent = "Order Summary";

    if (cart.restaurant) {
        const restBox = document.createElement("div");
        restBox.className = "mb-3 pb-3 border-bottom";
        const rName = document.createElement("div");
        rName.className = "fw-semibold";
        rName.textContent = cart.restaurant.name;
        const rAddr = document.createElement("div");
        rAddr.className = "small text-secondary";
        rAddr.textContent = cart.restaurant.address || "";
        restBox.append(rName, rAddr);
        summaryCard.appendChild(restBox);
    }

    if (offers.length) {
        const offerGroup = document.createElement("div"); offerGroup.className = "mb-3";
        const offerLabel = document.createElement("label"); offerLabel.className = "form-label fw-semibold";
        offerLabel.htmlFor = "checkoutOfferSelect"; offerLabel.textContent = "Apply restaurant offer (optional)";
        offerSelect = document.createElement("select"); offerSelect.id = "checkoutOfferSelect"; offerSelect.className = "form-select";
        const noOffer = document.createElement("option"); noOffer.value = ""; noOffer.textContent = "No offer"; offerSelect.appendChild(noOffer);
        offers.forEach(offer => { const option = document.createElement("option"); option.value = String(offer.id);
            option.textContent = `${offer.title} (${offer.discount_percent}% off)`; offerSelect.appendChild(option); });
        offerGroup.append(offerLabel, offerSelect); summaryCard.appendChild(offerGroup);
    }

    const itemsList = document.createElement("div");
    itemsList.className = "mb-3 pb-3 border-bottom";

    cart.items.forEach((item) => {
        const itemLine = document.createElement("div");
        itemLine.className = "d-flex justify-content-between align-items-center mb-2 small";
        const namePart = document.createElement("span");
        namePart.textContent = `${item.name} \u00D7 ${item.quantity}`;
        const pricePart = document.createElement("span");
        pricePart.className = "fw-semibold";
        pricePart.textContent = formatPrice(item.line_total);
        itemLine.append(namePart, pricePart);
        itemsList.appendChild(itemLine);
    });

    const dl = document.createElement("dl");
    dl.className = "row mb-3";

    function addRow(label, value, isTotal = false) {
        const dt = document.createElement("dt");
        dt.className = `col-7 ${isTotal ? "fw-bold fs-5" : "text-secondary fw-normal small"}`;
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.className = `col-5 text-end ${isTotal ? "fw-bold fs-5 fd-price" : "small"}`;
        dd.textContent = formatPrice(value);
        dl.append(dt, dd);
        return dd;
    }

    addRow("Subtotal", cart.subtotal);
    discountDisplay = addRow("Offer discount", 0);
    addRow("Delivery Fee", cart.delivery_fee);
    totalDisplay = addRow("Total Amount", cart.total_amount, true);

    function updateEstimatedTotal() {
        const percent = selectedOffer ? Number(selectedOffer.discount_percent) : 0;
        const discount = Math.round(Number(cart.subtotal) * percent) / 100;
        totalToPay = Math.max(0, Number(cart.subtotal) - discount + Number(cart.delivery_fee));
        discountDisplay.textContent = formatPrice(discount.toFixed(2));
        totalDisplay.textContent = formatPrice(totalToPay.toFixed(2));
        submitBtn.textContent = `Place Order (${formatPrice(totalToPay.toFixed(2))})`;
    }
    if (offerSelect) {
        offerSelect.addEventListener("change", () => {
            selectedOffer = offers.find(o => String(o.id) === offerSelect.value) || null;
            updateEstimatedTotal();
        });
    }

    summaryCard.append(itemsList, dl);
    rightCol.appendChild(summaryCard);

    row.append(leftCol, rightCol);
    container.appendChild(row);
}
