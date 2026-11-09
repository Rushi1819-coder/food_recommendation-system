/**
 * Food DNA - Kitchen Staff Dashboard (Screen 18)
 * Handles kitchen queue:
 *  - Live polling / refresh of incoming orders for staff's linked restaurant
 *  - Order transitions: Confirm -> Start Preparing -> Ready for Pickup
 */

(async function () {
    const messageBox = document.getElementById("pageMessage");
    const kitchenQueue = document.getElementById("kitchenQueue");
    const restaurantNameEl = document.getElementById("restaurantName");
    const activeCountEl = document.getElementById("activeKitchenCount");
    const refreshBtn = document.getElementById("refreshQueueBtn");

    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    if (user.role !== "staff") {
        if (messageBox) showMessage(messageBox, "warning", "Only restaurant kitchen staff have access to this screen.");
        return;
    }

    let filter = "all";
    const filterPills = document.querySelectorAll("[data-staff-filter]");
    filterPills.forEach(pill => {
        pill.addEventListener("click", () => {
            filterPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            filter = pill.getAttribute("data-staff-filter");
            loadQueue();
        });
    });

    async function loadQueue() {
        if (!kitchenQueue) return;
        try {
            const res = await apiRequest("/api/staff/dashboard");
            if (!res.ok) {
                if (messageBox) showMessage(messageBox, "danger", res.data.error || "Could not load kitchen orders.");
                return;
            }

            if (restaurantNameEl && res.data.restaurant) {
                restaurantNameEl.textContent = res.data.restaurant;
            }

            const orders = res.data.orders || [];
            const activeOrders = orders.filter(o => ["pending", "confirmed", "preparing"].includes(o.status));
            if (activeCountEl) activeCountEl.textContent = activeOrders.length;

            let filtered = orders;
            if (filter === "prep") {
                filtered = orders.filter(o => ["confirmed", "preparing"].includes(o.status));
            } else if (filter === "ready") {
                filtered = orders.filter(o => o.status === "ready_for_pickup");
            } else if (filter === "pending") {
                filtered = orders.filter(o => o.status === "pending");
            }

            kitchenQueue.replaceChildren();

            if (filtered.length === 0) {
                kitchenQueue.innerHTML = `<div class="p-5 text-center text-secondary">No orders match this filter in the kitchen queue.</div>`;
                return;
            }

            filtered.forEach(order => {
                const card = document.createElement("div");
                card.className = "fd-card p-4 mb-3";

                const nextActions = getStaffTransitions(order.status);

                card.innerHTML = `
                    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                        <div class="d-flex align-items-center gap-2">
                            <span class="fs-5 fw-bold" style="color: var(--fd-primary);">Order #${order.id}</span>
                            <span class="fd-badge fd-badge-${getStatusClass(order.status)}">${formatStatus(order.status)}</span>
                        </div>
                        <div class="text-secondary small">
                            Placed at ${order.placed_at ? new Date(order.placed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Recently'}
                        </div>
                    </div>
                    <div class="row g-2 mb-3 text-secondary small">
                        <div class="col-sm-4"><strong>Total Items:</strong> ${order.item_count} items</div>
                        <div class="col-sm-4"><strong>Bill:</strong> ₹${parseFloat(order.total_amount).toFixed(2)}</div>
                        <div class="col-sm-4"><strong>Delivery:</strong> ${escapeHtml(order.delivery_address || 'Customer Address')}</div>
                    </div>
                    <div class="d-flex flex-wrap gap-2 justify-content-end staff-actions-container"></div>
                `;

                const actionsContainer = card.querySelector(".staff-actions-container");

                nextActions.forEach(action => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = `btn btn-sm ${action.isDanger ? 'btn-outline-danger' : 'btn-fd'}`;
                    btn.textContent = action.label;
                    btn.addEventListener("click", async () => {
                        btn.disabled = true;
                        btn.textContent = "Updating...";
                        const updateRes = await apiRequest(`/api/staff/orders/${order.id}/status`, {
                            method: "PATCH",
                            body: { status: action.targetStatus },
                            csrf: true
                        });
                        if (!updateRes.ok) {
                            if (messageBox) showMessage(messageBox, "danger", updateRes.data.error || "Update failed.");
                            btn.disabled = false;
                            btn.textContent = action.label;
                        } else {
                            if (messageBox) showMessage(messageBox, "success", `Order #${order.id} is now ${action.label}.`);
                            loadQueue();
                        }
                    });
                    actionsContainer.appendChild(btn);
                });

                kitchenQueue.appendChild(card);
            });
        } catch (e) {
            console.error("Error loading kitchen queue:", e);
        }
    }

    function getStaffTransitions(status) {
        if (status === "pending") {
            return [
                { label: "Accept Order", targetStatus: "confirmed", isDanger: false },
                { label: "Decline", targetStatus: "cancelled", isDanger: true }
            ];
        } else if (status === "confirmed") {
            return [
                { label: "Start Cooking", targetStatus: "preparing", isDanger: false },
                { label: "Cancel", targetStatus: "cancelled", isDanger: true }
            ];
        } else if (status === "preparing") {
            return [
                { label: "Food Ready for Pickup", targetStatus: "ready_for_pickup", isDanger: false }
            ];
        }
        return [];
    }

    function getStatusClass(status) {
        switch (status) {
            case "ready_for_pickup": return "info";
            case "preparing": return "warning";
            case "confirmed": return "primary";
            case "delivered": return "success";
            case "cancelled": return "danger";
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

    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            loadQueue();
        });
    }

    await loadQueue();
    // Auto-poll queue every 15 seconds
    setInterval(loadQueue, 15000);
})();
