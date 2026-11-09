/**
 * FoodDNA - Order Details & Status Tracking Logic (Phase 6).
 */

async function initOrderDetailsPage() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }
    if (user.role !== "customer") {
        const msg = document.getElementById("orderDetailMessage");
        showMessage(msg, "warning", "Only customers have access to order details.");
        return;
    }

    const container = document.getElementById("orderDetailContent");
    const msg = document.getElementById("orderDetailMessage");

    const params = new URLSearchParams(window.location.search);
    const orderId = parseIdParam(params.get("id"));
    const justPlaced = params.get("placed") === "1";

    if (!orderId) {
        showMessage(msg, "danger", "Order ID is missing or invalid.");
        return;
    }

    if (justPlaced) {
        const successBox = document.createElement("div");
        successBox.className = "alert alert-success d-flex align-items-center mb-4 rounded-4 shadow-sm p-3";
        successBox.setAttribute("role", "alert");
        successBox.innerHTML = `
            <div class="fs-4 me-3">&#10004;</div>
            <div>
                <h4 class="alert-heading h5 mb-1">Order Placed Successfully!</h4>
                <p class="mb-0 small">Your order has been recorded and received by the restaurant. Thank you for choosing FoodDNA.</p>
            </div>
        `;
        msg.appendChild(successBox);
    }

    container.replaceChildren();
    const loading = document.createElement("div");
    loading.className = "text-center py-5 text-secondary";
    loading.textContent = "Loading order details...";
    container.appendChild(loading);

    const res = await fetchOrderDetails(orderId);
    if (res.status === 404) {
        container.replaceChildren();
        showMessage(msg, "danger", "Order not found or does not belong to your account.");
        return;
    }
    if (!res.ok) {
        container.replaceChildren();
        showMessage(msg, "danger", res.data.error || "Could not retrieve order details.");
        return;
    }

    const order = res.data.order;
    document.title = `Order #${order.id} - Food DNA`;
    renderOrderDetails(container, order);
}

function getStatusBadgeClass(status) {
    switch ((status || "").toLowerCase()) {
        case "pending":
            return "text-bg-warning";
        case "confirmed":
        case "accepted":
            return "text-bg-info";
        case "preparing":
            return "text-bg-primary";
        case "ready_for_pickup":
        case "out_for_delivery":
            return "text-bg-secondary";
        case "delivered":
        case "completed":
            return "text-bg-success";
        case "cancelled":
        case "rejected":
            return "text-bg-danger";
        default:
            return "text-bg-light border";
    }
}

function formatStatus(status) {
    if (!status) return "Pending";
    return status
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(isoString) {
    if (!isoString) return "";
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return isoString;
    }
}

function renderOrderDetails(container, order) {
    container.replaceChildren();

    const row = document.createElement("div");
    row.className = "row g-4";

    // Left Column: Items and Status Timeline
    const leftCol = document.createElement("div");
    leftCol.className = "col-lg-8";

    // Header Card
    const headerCard = document.createElement("div");
    headerCard.className = "fd-card p-4 mb-4";

    const topBar = document.createElement("div");
    topBar.className = "d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom";

    const titleBox = document.createElement("div");
    const mainTitle = document.createElement("h1");
    mainTitle.className = "h3 mb-1 text-dark";
    mainTitle.textContent = `Order #${order.id}`;

    const dateText = document.createElement("div");
    dateText.className = "small text-secondary";
    dateText.textContent = `Placed on ${formatDate(order.placed_at)}`;
    titleBox.append(mainTitle, dateText);

    const badge = document.createElement("span");
    badge.className = `badge ${getStatusBadgeClass(order.order_status)} fs-6 px-3 py-2`;
    badge.textContent = formatStatus(order.order_status);

    topBar.append(titleBox, badge);
    headerCard.appendChild(topBar);

    // Restaurant details
    if (order.restaurant) {
        const restDiv = document.createElement("div");
        restDiv.className = "mb-3";
        const rName = document.createElement("h2");
        rName.className = "h5 mb-1 text-dark";
        rName.textContent = order.restaurant.name;
        const rAddr = document.createElement("div");
        rAddr.className = "small text-secondary";
        rAddr.textContent = order.restaurant.address || "";
        if (order.restaurant.phone) {
            const rPhone = document.createElement("div");
            rPhone.className = "small text-secondary";
            rPhone.textContent = `Phone: ${order.restaurant.phone}`;
            restDiv.append(rName, rAddr, rPhone);
        } else {
            restDiv.append(rName, rAddr);
        }
        headerCard.appendChild(restDiv);
    }

    leftCol.appendChild(headerCard);

    // Items Card
    const itemsCard = document.createElement("div");
    itemsCard.className = "fd-card p-4 mb-4";

    const itemsTitle = document.createElement("h2");
    itemsTitle.className = "h5 mb-3";
    itemsTitle.textContent = "Dishes Ordered";

    const listGroup = document.createElement("div");
    listGroup.className = "list-group list-group-flush";

    (order.items || []).forEach((item) => {
        const itemRow = document.createElement("div");
        itemRow.className = "list-group-item px-0 py-3 d-flex justify-content-between align-items-center";

        const infoBox = document.createElement("div");
        const nameText = document.createElement("div");
        nameText.className = "fw-semibold";
        nameText.textContent = item.name;

        const subText = document.createElement("div");
        subText.className = "small text-secondary";
        subText.textContent = `${formatPrice(item.unit_price)} \u00D7 ${item.quantity}`;
        infoBox.append(nameText, subText);

        const totalText = document.createElement("div");
        totalText.className = "fw-bold fd-price";
        totalText.textContent = formatPrice(item.line_total);

        itemRow.append(infoBox, totalText);
        listGroup.appendChild(itemRow);
    });

    itemsCard.append(itemsTitle, listGroup);
    leftCol.appendChild(itemsCard);

    // Status Timeline Card
    if (order.status_history && order.status_history.length > 0) {
        const timelineCard = document.createElement("div");
        timelineCard.className = "fd-card p-4 mb-4";

        const tlTitle = document.createElement("h2");
        tlTitle.className = "h5 mb-3";
        tlTitle.textContent = "Status Timeline";

        const tlList = document.createElement("ul");
        tlList.className = "list-unstyled mb-0 position-relative ps-3 border-start border-2 border-secondary-subtle";

        order.status_history.forEach((sh) => {
            const li = document.createElement("li");
            li.className = "mb-3 position-relative";

            const dot = document.createElement("span");
            dot.className = "position-absolute top-0 start-0 translate-middle bg-primary rounded-circle";
            dot.style.width = "10px";
            dot.style.height = "10px";
            dot.style.left = "-17px";

            const timeDiv = document.createElement("div");
            timeDiv.className = "small text-muted";
            timeDiv.textContent = formatDate(sh.created_at);

            const statusText = document.createElement("div");
            statusText.className = "fw-semibold";
            statusText.textContent = formatStatus(sh.status);

            li.append(dot, timeDiv, statusText);
            if (sh.note) {
                const noteDiv = document.createElement("div");
                noteDiv.className = "small text-secondary";
                noteDiv.textContent = sh.note;
                li.appendChild(noteDiv);
            }
            tlList.appendChild(li);
        });

        timelineCard.append(tlTitle, tlList);
        leftCol.appendChild(timelineCard);
    }

    // Right Column: Delivery Details & Payment Breakdown
    const rightCol = document.createElement("div");
    rightCol.className = "col-lg-4";

    // Delivery Address Card
    const addressCard = document.createElement("div");
    addressCard.className = "fd-card p-4 mb-4";

    const addrTitle = document.createElement("h2");
    addrTitle.className = "h5 mb-2";
    addrTitle.textContent = "Delivery Address";

    const addrText = document.createElement("p");
    addrText.className = "small text-secondary mb-0";
    addrText.textContent = order.delivery_address;

    addressCard.append(addrTitle, addrText);
    rightCol.appendChild(addressCard);

    // Payment & Charges Card
    const payCard = document.createElement("div");
    payCard.className = "fd-card p-4 mb-4";

    const payTitle = document.createElement("h2");
    payTitle.className = "h5 mb-3";
    payTitle.textContent = "Payment & Charges";

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
    }

    addRow("Subtotal", order.subtotal);
    if (Number(order.discount_amount || 0) > 0) addRow("Offer discount", `-${formatPrice(order.discount_amount)}`);
    addRow("Delivery Fee", order.delivery_fee);
    addRow("Total Amount", order.total_amount, true);

    const hr = document.createElement("hr");
    hr.className = "my-3";

    const payMethodBox = document.createElement("div");
    payMethodBox.className = "small";

    const mLabel = document.createElement("div");
    mLabel.className = "fw-semibold";
    mLabel.textContent = "Payment Method:";
    const mVal = document.createElement("div");
    mVal.className = "text-secondary mb-2";
    mVal.textContent = "Cash on Delivery (COD)";

    const sLabel = document.createElement("div");
    sLabel.className = "fw-semibold";
    sLabel.textContent = "Payment Status:";
    const sVal = document.createElement("div");
    sVal.className = "badge text-bg-warning";
    sVal.textContent = order.payment ? formatStatus(order.payment.payment_status) : "Pending";

    const pNote = document.createElement("div");
    pNote.className = "small text-muted mt-2";
    pNote.textContent = "Payment is due upon food arrival at your delivery address.";

    payMethodBox.append(mLabel, mVal, sLabel, sVal, pNote);

    payCard.append(payTitle, dl, hr, payMethodBox);
    rightCol.appendChild(payCard);

    // Action buttons
    const actionsBox = document.createElement("div");
    actionsBox.className = "d-flex flex-column gap-2";

    if (order.restaurant) {
        const againBtn = document.createElement("a");
        againBtn.className = "btn btn-fd py-2";
        againBtn.href = `restaurant-menu.html?id=${encodeURIComponent(order.restaurant.id)}`;
        againBtn.textContent = `Order More from ${order.restaurant.name}`;
        actionsBox.appendChild(againBtn);
    }

    const backBtn = document.createElement("a");
    backBtn.className = "btn btn-outline-dark py-2";
    backBtn.href = "orders.html";
    backBtn.textContent = "Back to All Orders";
    actionsBox.appendChild(backBtn);

    rightCol.appendChild(actionsBox);

    row.append(leftCol, rightCol);
    container.appendChild(row);
}
