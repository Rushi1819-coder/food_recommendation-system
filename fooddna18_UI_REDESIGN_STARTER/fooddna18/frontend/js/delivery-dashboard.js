/**
 * Food DNA - Delivery Partner Dashboard (Screen 19)
 * Handles:
 *  - Rider availability status
 *  - Claiming available orders marked "ready_for_pickup"
 *  - Advancing active deliveries: Picked Up -> Out for Delivery -> Delivered (with COD collection)
 */

(async function () {
    const messageBox = document.getElementById("pageMessage");
    const activeDeliveriesList = document.getElementById("activeDeliveriesList");
    const availableOrdersList = document.getElementById("availableOrdersList");
    const riderStatusBadge = document.getElementById("riderStatusBadge");
    const availableCountBadge = document.getElementById("availableCountBadge");

    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    if (user.role !== "delivery_partner") {
        if (messageBox) showMessage(messageBox, "warning", "Only registered delivery partners have access to this portal.");
        return;
    }

    // Tab switching
    const tabButtons = document.querySelectorAll("[data-delivery-tab]");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const targetTab = btn.getAttribute("data-delivery-tab");
            document.getElementById("tabContentActive").hidden = targetTab !== "active";
            document.getElementById("tabContentAvailable").hidden = targetTab !== "available";
        });
    });

    async function loadDeliveryData() {
        try {
            // Load dashboard overview & active deliveries
            const dashRes = await apiRequest("/api/delivery/dashboard");
            if (!dashRes.ok) {
                if (messageBox) showMessage(messageBox, "danger", dashRes.data.error || "Could not load delivery dashboard.");
                return;
            }

            const data = dashRes.data;
            if (riderStatusBadge) {
                const isBusy = data.availability_status === "busy";
                riderStatusBadge.textContent = isBusy ? "On Delivery Trip (Busy)" : "Available for Orders";
                riderStatusBadge.className = `fd-badge ${isBusy ? 'fd-badge-warning' : 'fd-badge-success'}`;
            }

            if (availableCountBadge) {
                availableCountBadge.textContent = `${data.available_orders || 0} Available`;
            }

            renderAssignedDeliveries(data.assigned_orders || []);

            // Load available orders queue
            const availRes = await apiRequest("/api/delivery/orders/available");
            if (availRes.ok) {
                renderAvailableOrders(availRes.data.orders || []);
            }
        } catch (e) {
            console.error("Error loading delivery portal data:", e);
        }
    }

    function renderAssignedDeliveries(orders) {
        if (!activeDeliveriesList) return;
        activeDeliveriesList.replaceChildren();

        if (orders.length === 0) {
            activeDeliveriesList.innerHTML = `
                <div class="p-5 text-center text-secondary">
                    <div class="fs-4 mb-2">🛵</div>
                    <div class="fw-bold">No active deliveries right now.</div>
                    <div class="small mt-1">Switch to the "Available for Claim" tab to accept ready kitchen orders.</div>
                </div>
            `;
            return;
        }

        orders.forEach(order => {
            const card = document.createElement("div");
            card.className = "fd-card p-4 mb-3";

            const nextAction = getNextDeliveryAction(order.status);

            card.innerHTML = `
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fs-5 fw-bold" style="color: var(--fd-primary);">Order #${order.id}</span>
                        <span class="fd-badge fd-badge-${getStatusClass(order.status)}">${formatStatus(order.status)}</span>
                    </div>
                    <div class="fw-bold" style="color: var(--fd-primary);">
                        Collect COD: ₹${parseFloat(order.total_amount).toFixed(2)}
                    </div>
                </div>
                <div class="row g-2 mb-3 text-secondary small">
                    <div class="col-md-6">
                        <strong>Pickup From:</strong> ${escapeHtml(order.restaurant_name || 'Restaurant')}
                    </div>
                    <div class="col-md-6">
                        <strong>Dropoff Address:</strong> ${escapeHtml(order.delivery_address || 'Customer Address')}
                    </div>
                    <div class="col-md-6">
                        <strong>Items:</strong> ${order.item_count} items
                    </div>
                    <div class="col-md-6">
                        <strong>Payment Method:</strong> Cash on Delivery (Authoritative)
                    </div>
                </div>
                <div class="d-flex justify-content-end action-container"></div>
            `;

            if (nextAction) {
                const actionBtn = document.createElement("button");
                actionBtn.type = "button";
                actionBtn.className = "btn btn-fd px-4";
                actionBtn.textContent = nextAction.label;
                actionBtn.addEventListener("click", async () => {
                    actionBtn.disabled = true;
                    actionBtn.textContent = "Updating...";
                    const res = await apiRequest(`/api/delivery/orders/${order.id}/status`, {
                        method: "PATCH",
                        body: { status: nextAction.targetStatus, note: nextAction.note },
                        csrf: true
                    });
                    if (!res.ok) {
                        if (messageBox) showMessage(messageBox, "danger", res.data.error || "Update failed.");
                        actionBtn.disabled = false;
                        actionBtn.textContent = nextAction.label;
                    } else {
                        if (messageBox) showMessage(messageBox, "success", `Order #${order.id} status updated to ${nextAction.label}!`);
                        loadDeliveryData();
                    }
                });
                card.querySelector(".action-container").appendChild(actionBtn);
            }

            activeDeliveriesList.appendChild(card);
        });
    }

    function renderAvailableOrders(orders) {
        if (!availableOrdersList) return;
        availableOrdersList.replaceChildren();

        if (orders.length === 0) {
            availableOrdersList.innerHTML = `
                <div class="p-5 text-center text-secondary">
                    <div class="fs-4 mb-2">📦</div>
                    <div class="fw-bold">No orders currently waiting for pickup.</div>
                    <div class="small mt-1">Check back in a few moments as kitchens finish food preparation.</div>
                </div>
            `;
            return;
        }

        orders.forEach(order => {
            const card = document.createElement("div");
            card.className = "fd-card p-4 mb-3";

            card.innerHTML = `
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                    <div>
                        <span class="fw-bold fs-5">Order #${order.id}</span>
                        <span class="fd-badge fd-badge-info ms-2">Ready for Pickup</span>
                    </div>
                    <div class="fw-bold fs-5" style="color: var(--fd-primary);">
                        ₹${parseFloat(order.total_amount).toFixed(2)}
                    </div>
                </div>
                <div class="row g-2 mb-3 text-secondary small">
                    <div class="col-md-6"><strong>Restaurant:</strong> ${escapeHtml(order.restaurant_name || 'Restaurant')}</div>
                    <div class="col-md-6"><strong>Destination:</strong> ${escapeHtml(order.delivery_address || 'Customer Address')}</div>
                    <div class="col-md-6"><strong>Items:</strong> ${order.item_count} items</div>
                    <div class="col-md-6"><strong>Delivery Fee:</strong> ₹${parseFloat(order.delivery_fee || 40).toFixed(2)}</div>
                </div>
                <div class="d-flex justify-content-end">
                    <button type="button" class="btn btn-fd px-4 claim-order-btn">Claim Delivery</button>
                </div>
            `;

            const claimBtn = card.querySelector(".claim-order-btn");
            claimBtn.addEventListener("click", async () => {
                claimBtn.disabled = true;
                claimBtn.textContent = "Claiming...";
                const res = await apiRequest(`/api/delivery/orders/${order.id}/claim`, {
                    method: "POST",
                    csrf: true
                });
                if (!res.ok) {
                    if (messageBox) showMessage(messageBox, "danger", res.data.error || "Order could not be claimed.");
                    claimBtn.disabled = false;
                    claimBtn.textContent = "Claim Delivery";
                } else {
                    if (messageBox) showMessage(messageBox, "success", `Order #${order.id} claimed! View in your active deliveries.`);
                    // Switch to active deliveries tab
                    document.querySelector("[data-delivery-tab='active']").click();
                    loadDeliveryData();
                }
            });

            availableOrdersList.appendChild(card);
        });
    }

    function getNextDeliveryAction(status) {
        if (status === "ready_for_pickup") {
            return { label: "Confirm Pickup from Restaurant", targetStatus: "picked_up", note: "Picked up from kitchen" };
        } else if (status === "picked_up") {
            return { label: "Start Delivery (Out for Delivery)", targetStatus: "out_for_delivery", note: "Rider on the way" };
        } else if (status === "out_for_delivery") {
            return { label: "Confirm Delivered & Collect Cash", targetStatus: "delivered", note: "Delivered to customer" };
        }
        return null;
    }

    function getStatusClass(status) {
        switch (status) {
            case "ready_for_pickup": return "info";
            case "picked_up": return "primary";
            case "out_for_delivery": return "warning";
            case "delivered": return "success";
            default: return "neutral";
        }
    }

    function formatStatus(status) {
        if (!status) return "Unknown";
        return status.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    await loadDeliveryData();
    setInterval(loadDeliveryData, 15000);
})();
