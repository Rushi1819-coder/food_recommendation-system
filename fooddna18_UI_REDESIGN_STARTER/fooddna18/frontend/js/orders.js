/**
 * FoodDNA - Order History Frontend Logic (Phase 6).
 */

let currentPage = 1;

async function initOrdersPage() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }
    if (user.role !== "customer") {
        const msg = document.getElementById("ordersMessage");
        showMessage(msg, "warning", "Only customers have access to order history.");
        return;
    }

    loadOrders(currentPage);
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

async function loadOrders(page = 1) {
    currentPage = page;
    const container = document.getElementById("ordersContent");
    const pager = document.getElementById("ordersPagination");
    const msg = document.getElementById("ordersMessage");

    clearMessage(msg);
    pager.replaceChildren();
    container.replaceChildren();

    const loading = document.createElement("div");
    loading.className = "text-center py-5 text-secondary";
    loading.textContent = "Loading orders...";
    container.appendChild(loading);

    const res = await fetchOrders({ page, page_size: 10 });
    if (!res.ok) {
        container.replaceChildren();
        showMessage(msg, "danger", res.data.error || "Could not retrieve order history.");
        return;
    }

    const orders = res.data.orders || [];
    const pagination = res.data.pagination;

    if (orders.length === 0) {
        renderEmptyOrders(container);
        return;
    }

    renderOrdersList(container, orders);
    renderPagination(pager, pagination);
}

function renderEmptyOrders(container) {
    container.replaceChildren();
    const card = document.createElement("div");
    card.className = "fd-card p-5 text-center";

    const title = document.createElement("h2");
    title.className = "h4 mb-2";
    title.textContent = "No orders placed yet";

    const desc = document.createElement("p");
    desc.className = "text-secondary mb-4";
    desc.textContent = "When you order meals, their details and status tracking will appear here.";

    const btn = document.createElement("a");
    btn.className = "btn btn-fd px-4 py-2";
    btn.href = "menu.html";
    btn.textContent = "Order Food Now";

    card.append(title, desc, btn);
    container.appendChild(card);
}

function renderOrdersList(container, orders) {
    container.replaceChildren();

    const list = document.createElement("div");
    list.className = "d-flex flex-column gap-3";

    orders.forEach((o) => {
        const card = document.createElement("article");
        card.className = "fd-card p-4";

        const topRow = document.createElement("div");
        topRow.className = "d-flex flex-column flex-sm-row justify-content-between align-items-sm-center mb-3 pb-2 border-bottom gap-2";

        const idDateBox = document.createElement("div");
        const idText = document.createElement("span");
        idText.className = "fw-bold fs-5 text-dark me-2";
        idText.textContent = `Order #${o.id}`;

        const dateText = document.createElement("span");
        dateText.className = "text-secondary small";
        dateText.textContent = formatDate(o.placed_at);

        idDateBox.append(idText, dateText);

        const statusBadge = document.createElement("span");
        statusBadge.className = `badge ${getStatusBadgeClass(o.order_status)} px-3 py-2`;
        statusBadge.textContent = formatStatus(o.order_status);

        topRow.append(idDateBox, statusBadge);

        // Middle: Restaurant & Items
        const midRow = document.createElement("div");
        midRow.className = "row align-items-center mb-3";

        const restCol = document.createElement("div");
        restCol.className = "col-md-7 mb-2 mb-md-0";

        const restName = document.createElement("h3");
        restName.className = "h6 mb-1 text-dark";
        restName.textContent = o.restaurant_name;

        const summaryText = document.createElement("p");
        summaryText.className = "small text-secondary mb-0";
        summaryText.textContent = (o.items_summary && o.items_summary.length > 0)
            ? o.items_summary.join(", ")
            : `${o.item_count} items`;

        restCol.append(restName, summaryText);

        const priceCol = document.createElement("div");
        priceCol.className = "col-md-5 text-md-end";

        const totalLine = document.createElement("div");
        totalLine.className = "fw-bold fs-5 fd-price";
        totalLine.textContent = formatPrice(o.total_amount);

        const payLine = document.createElement("div");
        payLine.className = "small text-muted";
        payLine.textContent = `Cash on Delivery (${formatStatus(o.payment_status)})`;

        priceCol.append(totalLine, payLine);
        midRow.append(restCol, priceCol);

        // Bottom row: Action button
        const bottomRow = document.createElement("div");
        bottomRow.className = "pt-2 border-top d-flex justify-content-end";

        const detailsLink = document.createElement("a");
        detailsLink.className = "btn btn-outline-dark btn-sm";
        detailsLink.href = `order-details.html?id=${encodeURIComponent(o.id)}`;
        detailsLink.textContent = "View Order Details \u2192";

        bottomRow.appendChild(detailsLink);

        card.append(topRow, midRow, bottomRow);
        list.appendChild(card);
    });

    container.appendChild(list);
}

function renderPagination(container, pagination) {
    container.replaceChildren();
    if (!pagination || pagination.total_pages <= 1) {
        return;
    }

    const nav = document.createElement("nav");
    nav.setAttribute("aria-label", "Order history pagination");

    const ul = document.createElement("ul");
    ul.className = "pagination mb-0";

    // Previous
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${pagination.has_prev ? "" : "disabled"}`;
    const prevA = document.createElement("button");
    prevA.type = "button";
    prevA.className = "page-link";
    prevA.textContent = "\u00AB Previous";
    prevA.addEventListener("click", () => {
        if (pagination.has_prev) loadOrders(currentPage - 1);
    });
    prevLi.appendChild(prevA);
    ul.appendChild(prevLi);

    // Page indicator
    const infoLi = document.createElement("li");
    infoLi.className = "page-item disabled";
    const infoA = document.createElement("span");
    infoA.className = "page-link text-secondary";
    infoA.textContent = `Page ${pagination.page} of ${pagination.total_pages}`;
    infoLi.appendChild(infoA);
    ul.appendChild(infoLi);

    // Next
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${pagination.has_next ? "" : "disabled"}`;
    const nextA = document.createElement("button");
    nextA.type = "button";
    nextA.className = "page-link";
    nextA.textContent = "Next \u00BB";
    nextA.addEventListener("click", () => {
        if (pagination.has_next) loadOrders(currentPage + 1);
    });
    nextLi.appendChild(nextA);
    ul.appendChild(nextLi);

    nav.appendChild(ul);
    container.appendChild(nav);
}
