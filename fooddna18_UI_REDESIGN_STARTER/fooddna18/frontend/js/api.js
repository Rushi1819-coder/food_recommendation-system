/*
 * Food DNA - shared frontend helpers.
 *
 * Every request goes to the real Flask backend. The API address uses the
 * same host name as the page, so the session cookie is sent (a page on
 * 127.0.0.1 talks to 127.0.0.1:5000, a page on localhost talks to
 * localhost:5000). Do not open the pages by double-clicking the files:
 * serve them with `python -m http.server 5500` (see README).
 */

const API_HOST = window.location.hostname || "127.0.0.1";
const API_BASE = `http://${API_HOST}:5000`;

let csrfTokenCache = null;

/**
 * Calls the backend and ALWAYS returns { ok, status, data }.
 * It never throws, so pages can show a friendly message.
 */
async function apiRequest(path, options = {}) {
    const method = options.method || "GET";
    const headers = {};
    let body;

    if (options.body !== undefined) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(options.body);
    }

    if (options.csrf) {
        const token = await getCsrfToken();
        if (token) {
            headers["X-CSRF-Token"] = token;
        }
    }

    let response;
    try {
        response = await fetch(API_BASE + path, {
            method,
            headers,
            body,
            credentials: "include"
        });
    } catch (error) {
        return {
            ok: false,
            status: 0,
            data: {
                success: false,
                error: "Cannot reach the server. Make sure the Flask " +
                       "backend is running on port 5000."
            }
        };
    }

    let data = {};
    try {
        data = await response.json();
    } catch (error) {
        data = { success: false, error: "Unexpected server response." };
    }

    return {
        ok: response.ok && data.success !== false,
        status: response.status,
        data
    };
}

async function getCsrfToken(forceRefresh = false) {
    if (csrfTokenCache && !forceRefresh) {
        return csrfTokenCache;
    }
    const result = await apiRequest("/api/auth/csrf");
    csrfTokenCache = result.ok ? result.data.csrf_token : null;
    return csrfTokenCache;
}

/** Returns the logged-in user object, or null. */
async function getCurrentUser() {
    const result = await apiRequest("/api/auth/me");
    return result.ok ? result.data.user : null;
}

/** Sends the user to the login page if they are not logged in. */
async function requireLogin() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return null;
    }
    return user;
}

async function logout() {
    await apiRequest("/api/auth/logout", { method: "POST", csrf: true });
    csrfTokenCache = null;
    window.location.href = "login.html";
}

/* ---------- small UI helpers (use textContent: no HTML injection) ---------- */

function showMessage(container, type, text) {
    container.replaceChildren();
    const box = document.createElement("div");
    box.className = `alert alert-${type} mb-3`;
    box.setAttribute("role", "alert");
    box.textContent = text;
    container.appendChild(box);
}

function clearMessage(container) {
    container.replaceChildren();
}

function setBusy(button, busy, busyText) {
    if (busy) {
        button.dataset.originalText = button.textContent;
        button.textContent = busyText || "Please wait...";
        button.disabled = true;
    } else {
        button.textContent = button.dataset.originalText || button.textContent;
        button.disabled = false;
    }
}

/* Same rules as the backend. The backend is still the real authority. */
const PASSWORD_RULE =
    /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9])\S{8,}$/;
const EMAIL_RULE = /^(?!.*\.\.)[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?@gmail\.com$/i;
const NAME_RULE = /^(?=.*\p{L})[\p{L}\p{M} ]+$/u;

const PASSWORD_HINT =
    "At least 8 characters with an uppercase letter, a lowercase letter, " +
    "a number, a special character and no spaces.";

const ROLE_LABELS = {
    customer: "Customer",
    restaurant_admin: "Restaurant Admin",
    staff: "Staff",
    delivery_partner: "Delivery Partner",
    super_admin: "Super Admin"
};

/* ---------- Phase 4: food and restaurant browsing (public GET APIs) ---------- */

/* Display currency. The database stores plain prices; change this one
   constant if you want another symbol. */
const CURRENCY_SYMBOL = "\u20B9";

/** Builds "?a=1&b=2", skipping empty values. Values are URL-encoded. */
function buildQuery(params) {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
        if (value === undefined || value === null) {
            return;
        }
        const text = String(value).trim();
        if (text !== "") {
            query.set(key, text);
        }
    });
    const text = query.toString();
    return text ? `?${text}` : "";
}

function fetchRestaurants(params) {
    return apiRequest(`/api/restaurants${buildQuery(params)}`);
}

function fetchRestaurant(id) {
    return apiRequest(`/api/restaurants/${encodeURIComponent(id)}`);
}

function fetchCategories() {
    return apiRequest("/api/categories");
}

function fetchMeals(params) {
    return apiRequest(`/api/meals${buildQuery(params)}`);
}

function fetchMeal(id) {
    return apiRequest(`/api/meals/${encodeURIComponent(id)}`);
}

function fetchMealFilters() {
    return apiRequest("/api/meals/filters");
}

/** "240.00" -> "\u20B9240.00"; returns "" for anything that is not a number. */
function formatPrice(value) {
    const number = Number(value);
    return Number.isFinite(number)
        ? `${CURRENCY_SYMBOL}${number.toFixed(2)}`
        : "";
}

/** Returns the id string if it is a positive whole number, otherwise null. */
function parseIdParam(raw) {
    return /^[1-9]\d{0,17}$/.test(raw || "") ? raw : null;
}

/* ---------- Phase 5: preferences, recommendations, Food Memory ---------- */

/* Same rules as the backend (the backend is still the real authority). */
const BUDGET_RULE = /^\d{1,7}(\.\d{1,2})?$/;
const PREFERENCE_TEXT_RULE = /^[\p{L}\p{N}_ '&().,/+\-]+$/u;

function fetchPreferences() {
    return apiRequest("/api/preferences");
}

/** `values` is the COMPLETE set of preferences; null/blank clears a field. */
function savePreferences(values) {
    return apiRequest("/api/preferences", {
        method: "PUT",
        body: values,
        csrf: true
    });
}

/** Computes recommendations AND records them in the customer's history. */
function generateRecommendations(limit) {
    return apiRequest("/api/recommendations", {
        method: "POST",
        body: { limit },
        csrf: true
    });
}

function fetchRecommendationHistory(params) {
    return apiRequest(`/api/recommendations/history${buildQuery(params)}`);
}

function recordRecommendationSelection(mealId) {
    return apiRequest(
        `/api/recommendations/${encodeURIComponent(mealId)}/select`,
        { method: "POST", csrf: true }
    );
}

/** Fire-and-forget Food Memory event; only customers have one. */
async function recordMealViewIfCustomer(mealId) {
    const user = await getCurrentUser();
    if (user && user.role === "customer") {
        await apiRequest("/api/food-memory/meal-views", {
            method: "POST",
            body: { meal_id: Number(mealId) },
            csrf: true
        });
    }
}

/* ---------- Phase 6: Shopping Cart and Ordering APIs ---------- */

function fetchCart() {
    return apiRequest("/api/cart");
}

function addToCart(mealId, quantity = 1) {
    return apiRequest("/api/cart/items", {
        method: "POST",
        body: { meal_id: Number(mealId), quantity: Number(quantity) },
        csrf: true
    });
}

function updateCartItem(itemId, quantity) {
    return apiRequest(`/api/cart/items/${encodeURIComponent(itemId)}`, {
        method: "PATCH",
        body: { quantity: Number(quantity) },
        csrf: true
    });
}

function removeCartItem(itemId) {
    return apiRequest(`/api/cart/items/${encodeURIComponent(itemId)}`, {
        method: "DELETE",
        csrf: true
    });
}

function clearCart() {
    return apiRequest("/api/cart", {
        method: "DELETE",
        csrf: true
    });
}

function placeOrder(deliveryAddress, paymentMethod = "cash_on_delivery", offerId = null) {
    return apiRequest("/api/orders", {
        method: "POST",
        body: {
            delivery_address: deliveryAddress,
            payment_method: paymentMethod,
            ...(offerId ? { offer_id: Number(offerId) } : {})
        },
        csrf: true
    });
}

function fetchOrders(params) {
    return apiRequest(`/api/orders${buildQuery(params)}`);
}

function fetchOrderDetails(orderId) {
    return apiRequest(`/api/orders/${encodeURIComponent(orderId)}`);
}

function fetchOrderStatus(orderId) {
    return apiRequest(`/api/orders/${encodeURIComponent(orderId)}/status`);
}

/** Shows a transient notification toast without breaking layout. */
function showToast(message, type = "success") {
    let container = document.getElementById("fdToastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "fdToastContainer";
        container.className = "toast-container position-fixed bottom-0 end-0 p-3";
        container.style.zIndex = "1100";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-bg-${type} border-0 show shadow`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");

    const flex = document.createElement("div");
    flex.className = "d-flex";

    const body = document.createElement("div");
    body.className = "toast-body";
    body.textContent = message;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-close btn-close-white me-2 m-auto";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.addEventListener("click", () => toast.remove());

    flex.append(body, closeBtn);
    toast.appendChild(flex);
    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

/**
 * Shared Add-to-Cart handler with authentication, single-restaurant conflict
 * resolution and instant feedback.
 */
async function handleAddToCart(button, mealId, quantity = 1, mealName = "dish") {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }
    if (user.role !== "customer") {
        alert("Only customers can add meals to the shopping cart.");
        return;
    }

    setBusy(button, true, "Adding...");
    const res = await addToCart(mealId, quantity);
    setBusy(button, false);

    if (res.ok) {
        showToast(`Added "${mealName}" to your cart!`);
    } else if (res.status === 409 && res.data.code === "RESTAURANT_CONFLICT") {
        const existingName = (res.data.existing_restaurant && res.data.existing_restaurant.name) || "another restaurant";
        const newName = (res.data.new_restaurant && res.data.new_restaurant.name) || "this restaurant";
        const proceed = confirm(
            `Your cart already contains dishes from "${existingName}".\n\n` +
            `An order can only contain dishes from one restaurant at a time.\n\n` +
            `Would you like to clear your current cart and start a new order from "${newName}"?`
        );
        if (proceed) {
            setBusy(button, true, "Switching restaurant...");
            await clearCart();
            const retryRes = await addToCart(mealId, quantity);
            setBusy(button, false);
            if (retryRes.ok) {
                showToast(`Cart cleared and added "${mealName}" from "${newName}"!`);
            } else {
                alert(retryRes.data.error || "Could not add item to cart.");
            }
        }
    } else {
        alert(res.data.error || "Could not add item to cart.");
    }
}

/* ---------- User Profile & Saved Addresses ---------- */

async function fetchUserProfile() {
    return await apiRequest("/api/user/profile");
}

async function updateUserProfile(data) {
    return await apiRequest("/api/user/profile", {
        method: "PATCH",
        body: data,
        csrf: true
    });
}

async function changeUserPassword(data) {
    return await apiRequest("/api/user/change-password", {
        method: "POST",
        body: data,
        csrf: true
    });
}

async function fetchUserAddresses() {
    return await apiRequest("/api/user/addresses");
}

async function addUserAddress(data) {
    return await apiRequest("/api/user/addresses", {
        method: "POST",
        body: data,
        csrf: true
    });
}

async function setDefaultAddress(id) {
    return await apiRequest(`/api/user/addresses/${id}/default`, {
        method: "PATCH",
        csrf: true
    });
}

async function deleteUserAddress(id) {
    return await apiRequest(`/api/user/addresses/${id}`, {
        method: "DELETE",
        csrf: true
    });
}

/* ---------- Reverse Food Ordering Search ---------- */

async function reverseFoodSearch(query) {
    return await apiRequest(`/api/meals/reverse-search?q=${encodeURIComponent(query)}`);
}

/* ---------- Operations Helpers (Super Admin, Staff, Delivery) ---------- */

async function fetchAdminApprovals(status = "all") {
    return await apiRequest(`/api/admin/approvals?status=${encodeURIComponent(status)}`);
}

async function reviewAdminApproval(id, status, remarks = "") {
    return await apiRequest(`/api/admin/approvals/${id}`, {
        method: "PATCH",
        body: { status, remarks },
        csrf: true
    });
}

async function fetchAdminUsers(role = "") {
    const q = role ? `?role=${encodeURIComponent(role)}` : "";
    return await apiRequest(`/api/admin/users${q}`);
}

async function createAdminOperator(data) {
    return await apiRequest("/api/admin/users", {
        method: "POST",
        body: data,
        csrf: true
    });
}

async function updateAdminUserStatus(id, account_status) {
    return await apiRequest(`/api/admin/users/${id}/status`, {
        method: "PATCH",
        body: { account_status },
        csrf: true
    });
}

async function fetchAdminRestaurants(status = "all") {
    return await apiRequest(`/api/admin/restaurants?status=${encodeURIComponent(status)}`);
}

async function fetchStaffDashboard() {
    return await apiRequest("/api/staff/dashboard");
}

async function updateStaffOrderStatus(orderId, status, note = "") {
    return await apiRequest(`/api/staff/orders/${orderId}/status`, {
        method: "PATCH",
        body: { status, note },
        csrf: true
    });
}

async function fetchDeliveryDashboard() {
    return await apiRequest("/api/delivery/dashboard");
}

async function fetchDeliveryAvailableOrders() {
    return await apiRequest("/api/delivery/orders/available");
}

async function claimDeliveryOrder(orderId) {
    return await apiRequest(`/api/delivery/orders/${orderId}/claim`, {
        method: "POST",
        csrf: true
    });
}

async function updateDeliveryOrderStatus(orderId, status, note = "") {
    return await apiRequest(`/api/delivery/orders/${orderId}/status`, {
        method: "PATCH",
        body: { status, note },
        csrf: true
    });
}



