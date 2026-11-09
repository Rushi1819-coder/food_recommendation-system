/**
 * Food DNA - Restaurant Management Dashboard (Screens 16 & 17)
 * Handles:
 *  1. Restaurant Overview & KPIs (Total Orders, Active Orders, Dishes, Approval Status)
 *  2. Orders Queue with state transitions (Confirm, Start Preparing, Ready for Pickup, Cancel)
 *  3. Menu Management (Dish table, Availability toggle, Add new dish)
 */

(async function () {
    const messageBox = document.getElementById("pageMessage");
    const form = document.getElementById("mealForm");
    const categorySelect = document.getElementById("mealCategory");
    const mealList = document.getElementById("mealList");
    const ordersList = document.getElementById("ordersList");
    const restaurantNameEl = document.getElementById("restaurantName");
    const restaurantStatusEl = document.getElementById("restaurantStatus");

    // KPI elements
    const kpiTotalOrders = document.getElementById("kpiTotalOrders");
    const kpiActiveOrders = document.getElementById("kpiActiveOrders");
    const kpiTotalMeals = document.getElementById("kpiTotalMeals");

    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    if (user.role !== "restaurant_admin") {
        if (messageBox) {
            showMessage(messageBox, "warning", "Only restaurant administrators have access to this portal.");
        }
        if (form) form.hidden = true;
        return;
    }

    // Load Categories for Meal Form
    if (categorySelect) {
        try {
            const categoriesRes = await apiRequest("/api/categories");
            if (categoriesRes.ok && categoriesRes.data.categories) {
                categorySelect.replaceChildren();
                const defaultOpt = document.createElement("option");
                defaultOpt.value = "";
                defaultOpt.textContent = "Select Category";
                defaultOpt.disabled = true;
                defaultOpt.selected = true;
                categorySelect.appendChild(defaultOpt);

                categoriesRes.data.categories.forEach(category => {
                    const option = document.createElement("option");
                    option.value = category.id;
                    option.textContent = category.name;
                    categorySelect.appendChild(option);
                });
            }
        } catch (e) {
            console.error("Error loading categories:", e);
        }
    }

    // Load Dashboard Overview & Orders
    async function loadDashboard() {
        try {
            const res = await apiRequest("/api/restaurant-admin/dashboard");
            if (!res.ok) {
                if (messageBox) showMessage(messageBox, "danger", res.data.error || "Could not load restaurant dashboard.");
                return;
            }

            const data = res.data;
            if (restaurantNameEl && data.restaurant) {
                restaurantNameEl.textContent = data.restaurant.name;
            }
            if (restaurantStatusEl && data.restaurant) {
                restaurantStatusEl.textContent = data.restaurant.status.toUpperCase();
                restaurantStatusEl.className = `fd-badge ${data.restaurant.status === 'approved' ? 'fd-badge-success' : 'fd-badge-warning'}`;
            }

            if (data.summary) {
                if (kpiTotalOrders) kpiTotalOrders.textContent = data.summary.orders_total || 0;
                if (kpiActiveOrders) kpiActiveOrders.textContent = data.summary.orders_active || 0;
                if (kpiTotalMeals) kpiTotalMeals.textContent = data.summary.meals_total || 0;
            }

            renderOrders(data.summary ? data.summary.recent_orders || [] : []);
        } catch (e) {
            console.error("Error loading dashboard data:", e);
        }
    }

    function renderOrders(orders) {
        if (!ordersList) return;
        ordersList.replaceChildren();

        if (orders.length === 0) {
            ordersList.innerHTML = `<div class="p-4 text-center text-secondary">No active or recent orders for your restaurant yet.</div>`;
            return;
        }

        orders.forEach(order => {
            const card = document.createElement("div");
            card.className = "fd-card p-3 mb-3";

            const nextActions = getOrderTransitions(order.status);

            card.innerHTML = `
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                    <div>
                        <span class="fw-bold">Order #${order.id}</span>
                        <span class="text-secondary small ms-2">${order.placed_at ? new Date(order.placed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}</span>
                    </div>
                    <div>
                        <span class="fd-badge fd-badge-${getStatusClass(order.status)}">${formatStatus(order.status)}</span>
                    </div>
                </div>
                <div class="row g-2 small text-secondary mb-3">
                    <div class="col-6 col-md-3"><strong>Items:</strong> ${order.item_count} items</div>
                    <div class="col-6 col-md-3"><strong>Total:</strong> ₹${parseFloat(order.total_amount).toFixed(2)}</div>
                    <div class="col-12 col-md-6 text-truncate"><strong>Delivery:</strong> ${escapeHtml(order.delivery_address || 'Customer Address')}</div>
                </div>
                <div class="d-flex flex-wrap gap-2 justify-content-end order-actions-container"></div>
            `;

            const actionsContainer = card.querySelector(".order-actions-container");

            nextActions.forEach(action => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = `btn btn-sm ${action.isDanger ? 'btn-outline-danger' : 'btn-fd'}`;
                btn.textContent = action.label;
                btn.addEventListener("click", async () => {
                    btn.disabled = true;
                    btn.textContent = "Updating...";
                    const updateRes = await apiRequest(`/api/restaurant-admin/orders/${order.id}/status`, {
                        method: "PATCH",
                        body: { status: action.targetStatus },
                        csrf: true
                    });
                    if (!updateRes.ok) {
                        if (messageBox) showMessage(messageBox, "danger", updateRes.data.error || "Update failed.");
                        btn.disabled = false;
                        btn.textContent = action.label;
                    } else {
                        if (messageBox) showMessage(messageBox, "success", `Order #${order.id} status updated to ${action.label}.`);
                        loadDashboard();
                    }
                });
                actionsContainer.appendChild(btn);
            });

            ordersList.appendChild(card);
        });
    }

    function getOrderTransitions(status) {
        if (status === "pending") {
            return [
                { label: "Confirm Order", targetStatus: "confirmed", isDanger: false },
                { label: "Cancel", targetStatus: "cancelled", isDanger: true }
            ];
        } else if (status === "confirmed") {
            return [
                { label: "Start Preparing", targetStatus: "preparing", isDanger: false },
                { label: "Cancel", targetStatus: "cancelled", isDanger: true }
            ];
        } else if (status === "preparing") {
            return [
                { label: "Ready for Pickup", targetStatus: "ready_for_pickup", isDanger: false }
            ];
        }
        return [];
    }

    function getStatusClass(status) {
        switch (status) {
            case "delivered": return "success";
            case "cancelled": return "danger";
            case "ready_for_pickup":
            case "out_for_delivery": return "info";
            case "confirmed":
            case "preparing": return "warning";
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

    // Load Meals Menu
    async function loadMeals() {
        if (!mealList) return;
        const result = await apiRequest("/api/restaurant-admin/meals");
        if (!result.ok) {
            if (messageBox) showMessage(messageBox, "danger", result.data.error || "Could not load menu dishes.");
            return;
        }

        mealList.replaceChildren();
        const meals = result.data.meals || [];

        if (meals.length === 0) {
            mealList.innerHTML = `<div class="p-4 text-center text-secondary">No dishes yet. Use the form below to add your first dish.</div>`;
            return;
        }

        const table = document.createElement("table");
        table.className = "table table-hover align-middle fd-table mb-0";
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Dish Details</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Diet / Type</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector("tbody");

        meals.forEach(meal => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div class="fw-bold">${escapeHtml(meal.name)}</div>
                    <div class="small text-secondary">${escapeHtml(meal.cuisine || 'Cuisine')} • ${escapeHtml(meal.taste || 'Savory')}</div>
                </td>
                <td><span class="fd-badge fd-badge-neutral">${meal.category_id}</span></td>
                <td class="fw-bold" style="color: var(--fd-primary);">₹${parseFloat(meal.price).toFixed(2)}</td>
                <td>
                    <span class="fd-diet-badge fd-diet-${(meal.food_type || 'veg').toLowerCase().replace('-', '')}">
                        <span class="dot"></span> ${escapeHtml(meal.food_type || 'Veg')}
                    </span>
                </td>
                <td>
                    <span class="fd-badge ${meal.is_available ? 'fd-badge-success' : 'fd-badge-neutral'}">
                        ${meal.is_available ? 'Available' : 'Sold Out'}
                    </span>
                </td>
                <td class="text-end">
                    <button type="button" class="btn btn-sm ${meal.is_available ? 'btn-outline-secondary' : 'btn-fd-outline'} toggle-avail-btn">
                        ${meal.is_available ? 'Mark Unavailable' : 'Mark Available'}
                    </button>
                </td>
            `;

            const toggleBtn = tr.querySelector(".toggle-avail-btn");
            toggleBtn.addEventListener("click", async () => {
                toggleBtn.disabled = true;
                const r = await apiRequest(`/api/restaurant-admin/meals/${meal.id}`, {
                    method: "PATCH",
                    body: { is_available: !meal.is_available },
                    csrf: true
                });
                if (!r.ok) {
                    if (messageBox) showMessage(messageBox, "danger", r.data.error || "Update failed.");
                    toggleBtn.disabled = false;
                } else {
                    loadMeals();
                    loadDashboard();
                }
            });

            tbody.appendChild(tr);
        });

        mealList.appendChild(table);
    }

    // Add Dish Form Handler
    if (form) {
        form.addEventListener("submit", async event => {
            event.preventDefault();
            const submitBtn = form.querySelector("button[type='submit']");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Adding Dish...";
            }

            const body = {
                category_id: Number(categorySelect.value),
                name: document.getElementById("mealName").value.trim(),
                price: document.getElementById("mealPrice").value,
                description: document.getElementById("mealDescription").value.trim(),
                cuisine: document.getElementById("mealCuisine").value.trim(),
                meal_type: document.getElementById("mealType").value.trim(),
                taste: document.getElementById("mealTaste").value.trim(),
                spice_level: document.getElementById("mealSpice").value,
                portion_size: document.getElementById("mealPortion").value,
                food_type: document.getElementById("mealFoodType").value,
                dietary_preference: document.getElementById("mealDietary").value.trim(),
                image_url: document.getElementById("mealImage").value.trim()
            };

            const result = await apiRequest("/api/restaurant-admin/meals", {
                method: "POST",
                body,
                csrf: true
            });

            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Add Dish to Menu";
            }

            if (!result.ok) {
                if (messageBox) showMessage(messageBox, "danger", result.data.error || "Could not add dish.");
            } else {
                if (messageBox) showMessage(messageBox, "success", `"${body.name}" has been added to your menu!`);
                form.reset();
                // Set default cuisine back
                const cuisineInput = document.getElementById("mealCuisine");
                if (cuisineInput) cuisineInput.value = "Indian";
                loadMeals();
                loadDashboard();
            }
        });
    }

    // Initial loads
    await Promise.all([loadDashboard(), loadMeals()]);
})();
