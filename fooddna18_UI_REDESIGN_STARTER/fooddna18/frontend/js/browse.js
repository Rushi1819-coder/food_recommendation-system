/*
 * Food DNA - restaurant and food browsing UI (Phase 4).
 *
 * Needs js/api.js. Every list and detail comes from the Flask API; nothing
 * is hard-coded. All text from the server is inserted with textContent
 * (never innerHTML), so database content cannot inject HTML or scripts.
 */

/* ---------- small safe DOM helpers ---------- */

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text !== undefined && text !== null) {
        node.textContent = text;
    }
    return node;
}

function showLoading(container, label) {
    const box = el("div", "text-center text-secondary py-5");
    box.setAttribute("data-state", "loading");
    box.setAttribute("role", "status");
    box.appendChild(el("div", "spinner-border spinner-border-sm me-2"));
    box.appendChild(el("span", "", label || "Loading..."));
    container.replaceChildren(box);
}

function showEmpty(container, title, text, actionLabel, onAction) {
    const box = el("div", "text-center py-5");
    box.setAttribute("data-state", "empty");
    box.appendChild(el("div", "h5 mb-1", title));
    box.appendChild(el("p", "text-secondary mb-3", text));
    if (actionLabel && onAction) {
        const button = el("button", "btn btn-outline-dark btn-sm", actionLabel);
        button.type = "button";
        button.addEventListener("click", onAction);
        box.appendChild(button);
    }
    container.replaceChildren(box);
}

function showError(container, message, onRetry) {
    const box = el("div", "alert alert-danger text-center my-4");
    box.setAttribute("data-state", "error");
    box.setAttribute("role", "alert");
    box.appendChild(el("div", "mb-2", message || "Something went wrong."));
    if (onRetry) {
        const button = el("button", "btn btn-outline-danger btn-sm", "Try again");
        button.type = "button";
        button.addEventListener("click", onRetry);
        box.appendChild(button);
    }
    container.replaceChildren(box);
}

function renderPagination(container, pagination, onPage) {
    container.replaceChildren();
    if (!pagination || pagination.total_pages <= 1) {
        return;
    }
    const nav = el(
        "nav",
        "d-flex justify-content-center align-items-center gap-3 mt-4"
    );
    nav.setAttribute("aria-label", "Pages");

    const prev = el("button", "btn btn-outline-dark btn-sm", "Previous");
    prev.type = "button";
    prev.disabled = pagination.page <= 1;
    prev.addEventListener("click", () => onPage(pagination.page - 1));

    const label = el(
        "span",
        "text-secondary small",
        `Page ${pagination.page} of ${pagination.total_pages}`
    );

    const next = el("button", "btn btn-outline-dark btn-sm", "Next");
    next.type = "button";
    next.disabled = pagination.page >= pagination.total_pages;
    next.addEventListener("click", () => onPage(pagination.page + 1));

    nav.append(prev, label, next);
    container.appendChild(nav);
}

/* ---------- cards ---------- */

const FOOD_TYPE_STYLES = {
    "veg": "text-bg-success",
    "vegan": "text-bg-success",
    "non-veg": "text-bg-danger"
};

function foodTypeBadge(foodType) {
    const style =
        FOOD_TYPE_STYLES[String(foodType).toLowerCase()] || "text-bg-secondary";
    return el("span", `badge ${style}`, foodType);
}

function isHttpUrl(value) {
    return typeof value === "string" && /^https?:\/\//i.test(value);
}

/** An <img> when the meal has a valid URL (falls back if it fails), else a letter tile. */
function createMealImage(meal, extraClass) {
    const wrapper = el("div", `fd-meal-img ${extraClass || ""}`.trim());

    function placeholder() {
        const tile = el(
            "div",
            "fd-img-placeholder",
            (meal.name || "?").charAt(0).toUpperCase()
        );
        tile.setAttribute("aria-hidden", "true");
        wrapper.replaceChildren(tile);
    }

    if (isHttpUrl(meal.image_url)) {
        const img = document.createElement("img");
        img.alt = meal.name || "Meal";
        img.loading = "lazy";
        img.referrerPolicy = "no-referrer";
        img.addEventListener("error", placeholder);
        img.src = meal.image_url;
        wrapper.appendChild(img);
    } else {
        placeholder();
    }
    return wrapper;
}

function mealTags(meal) {
    const row = el("div", "d-flex flex-wrap gap-1 mb-2");
    row.appendChild(foodTypeBadge(meal.food_type));
    [meal.category && meal.category.name, meal.cuisine, meal.meal_type].forEach(
        (text) => {
            if (text) {
                row.appendChild(el("span", "badge text-bg-light border", text));
            }
        }
    );
    return row;
}

function renderMealCard(meal, options) {
    const showRestaurant = !(options && options.hideRestaurant);
    const col = el("div", "col");
    const card = el("article", "card h-100 fd-card-item");
    card.setAttribute("data-meal-id", meal.id);

    card.appendChild(createMealImage(meal));

    const body = el("div", "card-body d-flex flex-column");
    const title = el("h2", "h5 card-title mb-1");
    const link = el("a", "text-decoration-none", meal.name);
    link.href = `meal.html?id=${encodeURIComponent(meal.id)}`;
    title.appendChild(link);
    body.appendChild(title);

    if (showRestaurant && meal.restaurant) {
        const where = el("div", "small mb-2");
        const restaurantLink = el("a", "", meal.restaurant.name);
        restaurantLink.href =
            `restaurant-menu.html?id=${encodeURIComponent(meal.restaurant.id)}`;
        where.appendChild(restaurantLink);
        body.appendChild(where);
    }

    body.appendChild(mealTags(meal));

    if (meal.description) {
        body.appendChild(
            el("p", "card-text small text-secondary flex-grow-1", meal.description)
        );
    }

    const facts = [];
    if (meal.taste) {
        facts.push(`Taste: ${meal.taste}`);
    }
    if (meal.spice_level) {
        facts.push(`Spice: ${meal.spice_level}`);
    }
    if (meal.dietary_preference) {
        facts.push(meal.dietary_preference);
    }
    if (facts.length) {
        body.appendChild(el("div", "small text-secondary mb-2", facts.join(" \u00B7 ")));
    }

    const priceRow = el("div", "d-flex justify-content-between align-items-center mt-auto pt-2");
    priceRow.appendChild(el("div", "fw-bold fs-5 fd-price", formatPrice(meal.price)));

    const addBtn = el("button", "btn btn-fd btn-sm", "Add to Cart");
    addBtn.type = "button";
    addBtn.setAttribute("aria-label", `Add ${meal.name} to cart`);
    addBtn.addEventListener("click", (e) => {
        e.preventDefault();
        handleAddToCart(addBtn, meal.id, 1, meal.name);
    });
    priceRow.appendChild(addBtn);

    body.appendChild(priceRow);
    card.appendChild(body);
    col.appendChild(card);
    return col;
}

function renderRestaurantCard(restaurant) {
    const col = el("div", "col");
    const card = el("article", "card h-100 fd-card-item");
    card.setAttribute("data-restaurant-id", restaurant.id);
    const body = el("div", "card-body d-flex flex-column");

    body.appendChild(el("h2", "h5 card-title", restaurant.name));
    if (restaurant.description) {
        body.appendChild(el("p", "card-text text-secondary", restaurant.description));
    }
    if (restaurant.address) {
        body.appendChild(el("p", "small mb-2", restaurant.address));
    }
    const count = restaurant.meal_count || 0;
    body.appendChild(
        el(
            "p",
            "small text-secondary mb-3",
            count === 1 ? "1 dish available" : `${count} dishes available`
        )
    );

    const button = el("a", "btn btn-fd mt-auto", "View menu");
    button.href = `restaurant-menu.html?id=${encodeURIComponent(restaurant.id)}`;
    body.appendChild(button);

    card.appendChild(body);
    col.appendChild(card);
    return col;
}

/* ---------- restaurant list page ---------- */

async function initRestaurantList() {
    const form = document.getElementById("restaurantSearchForm");
    const input = document.getElementById("restaurantSearch");
    const results = document.getElementById("restaurantResults");
    const summary = document.getElementById("restaurantSummary");
    const pager = document.getElementById("restaurantPager");

    const initial = new URLSearchParams(window.location.search);
    input.value = (initial.get("q") || "").slice(0, 100);
    let page = parseIdParam(initial.get("page")) ? Number(initial.get("page")) : 1;
    let requestCounter = 0;

    async function load() {
        const mine = ++requestCounter;
        const search = input.value.trim();
        history.replaceState(
            null,
            "",
            `${window.location.pathname}${buildQuery({ q: search, page: page > 1 ? page : "" })}`
        );
        showLoading(results, "Loading restaurants...");
        summary.textContent = "";
        pager.replaceChildren();

        const response = await fetchRestaurants({ q: search, page, page_size: 9 });
        if (mine !== requestCounter) {
            return;
        }
        if (!response.ok) {
            showError(
                results,
                response.data.error || "Could not load restaurants.",
                load
            );
            return;
        }
        const { restaurants, pagination } = response.data;
        if (!restaurants.length) {
            if (pagination.total > 0 && page > 1) {
                page = 1;
                return load();
            }
            showEmpty(
                results,
                search ? "No restaurants match your search" : "No restaurants are available yet",
                search ? "Try a different name." : "Please check back soon.",
                search ? "Clear search" : null,
                () => {
                    input.value = "";
                    page = 1;
                    load();
                }
            );
            return;
        }
        const grid = el("div", "row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4");
        restaurants.forEach((restaurant) =>
            grid.appendChild(renderRestaurantCard(restaurant))
        );
        results.replaceChildren(grid);
        summary.textContent =
            pagination.total === 1 ? "1 restaurant" : `${pagination.total} restaurants`;
        renderPagination(pager, pagination, (next) => {
            page = next;
            load();
            window.scrollTo(0, 0);
        });
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        page = 1;
        load();
    });
    return load();
}

/* ---------- meal browser (food menu page and restaurant menu page) ---------- */

const SPICE_ORDER = ["none", "mild", "medium", "hot", "extra hot"];

function fillSelect(select, values, labelOf) {
    if (!select) {
        return;
    }
    const keep = select.value;
    while (select.options.length > 1) {
        select.remove(1);
    }
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = String(value.value !== undefined ? value.value : value);
        option.textContent = labelOf ? labelOf(value) : String(value);
        select.appendChild(option);
    });
    if (keep) {
        select.value = keep;
    }
}

const FILTER_FIELDS = [
    "q", "restaurant_id", "category_id", "cuisine", "meal_type",
    "food_type", "dietary_preference", "spice_level", "min_price",
    "max_price", "sort"
];

/*
 * options.restaurantId: fixes the restaurant (restaurant menu page).
 * Expects the elements used by menu.html / restaurant-menu.html.
 */
async function initMealBrowser(options) {
    const fixedRestaurant = (options && options.restaurantId) || null;
    const form = document.getElementById("filterForm");
    const results = document.getElementById("mealResults");
    const summary = document.getElementById("mealSummary");
    const pager = document.getElementById("mealPager");
    const formMessage = document.getElementById("filterMessage");
    const reset = document.getElementById("resetFilters");

    function field(name) {
        return form.elements[name] || null;
    }

    // Show feedback straight away; the filter lists load first.
    showLoading(results, "Loading dishes...");

    // Filter choices come from the database, so they always match real data.
    const [filters, categories, restaurants] = await Promise.all([
        fetchMealFilters(),
        fetchCategories(),
        fixedRestaurant ? Promise.resolve(null) : fetchRestaurants({ page_size: 50 })
    ]);

    if (filters.ok) {
        const f = filters.data.filters;
        fillSelect(field("cuisine"), f.cuisines);
        fillSelect(field("meal_type"), f.meal_types);
        fillSelect(field("food_type"), f.food_types);
        fillSelect(field("dietary_preference"), f.dietary_preferences);
        fillSelect(
            field("spice_level"),
            [...f.spice_levels].sort((a, b) => {
                const ia = SPICE_ORDER.indexOf(String(a).toLowerCase());
                const ib = SPICE_ORDER.indexOf(String(b).toLowerCase());
                return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
            })
        );
    }
    if (categories.ok) {
        fillSelect(
            field("category_id"),
            categories.data.categories.map((c) => ({ value: c.id, name: c.name })),
            (c) => c.name
        );
    }
    if (restaurants && restaurants.ok) {
        fillSelect(
            field("restaurant_id"),
            restaurants.data.restaurants.map((r) => ({ value: r.id, name: r.name })),
            (r) => r.name
        );
    }

    // Start from the address-bar values so links and the Back button work.
    const initial = new URLSearchParams(window.location.search);
    FILTER_FIELDS.forEach((name) => {
        const input = field(name);
        if (input && initial.has(name)) {
            input.value = initial.get(name).slice(0, 100);
        }
    });
    let page = parseIdParam(initial.get("page")) ? Number(initial.get("page")) : 1;
    let requestCounter = 0;

    function currentParams() {
        const params = {};
        FILTER_FIELDS.forEach((name) => {
            const input = field(name);
            if (input && input.value.trim() !== "") {
                params[name] = input.value.trim();
            }
        });
        if (fixedRestaurant) {
            params.restaurant_id = fixedRestaurant;
        }
        return params;
    }

    // Same rules as the backend (the backend is still the real authority).
    function validateForm() {
        const min = field("min_price").value.trim();
        const max = field("max_price").value.trim();
        const bad = [min, max].some(
            (v) => v !== "" && !/^\d{1,7}(\.\d{1,2})?$/.test(v)
        );
        if (bad) {
            return "Prices must be positive numbers with at most 2 decimals.";
        }
        if (min !== "" && max !== "" && Number(min) > Number(max)) {
            return "Minimum price cannot be greater than maximum price.";
        }
        return "";
    }

    function updateAddressBar(params) {
        const urlParams = Object.assign({}, params);
        const keep = {};
        if (fixedRestaurant) {
            keep.id = fixedRestaurant;
            delete urlParams.restaurant_id;
        }
        history.replaceState(
            null,
            "",
            `${window.location.pathname}${buildQuery(
                Object.assign(keep, urlParams, { page: page > 1 ? page : "" })
            )}`
        );
    }

    async function load() {
        const problem = validateForm();
        if (problem) {
            showMessage(formMessage, "warning", problem);
            return;
        }
        clearMessage(formMessage);

        const mine = ++requestCounter;
        const params = currentParams();
        updateAddressBar(params);

        showLoading(results, "Loading dishes...");
        summary.textContent = "";
        pager.replaceChildren();

        const response = await fetchMeals(
            Object.assign({}, params, { page, page_size: 12 })
        );
        if (mine !== requestCounter) {
            return;
        }
        if (!response.ok) {
            showError(results, response.data.error || "Could not load dishes.", load);
            return;
        }
        const { meals, pagination } = response.data;
        if (!meals.length) {
            if (pagination.total > 0 && page > 1) {
                page = 1;
                return load();
            }
            const filtered = Object.keys(params).some(
                (key) => key !== "restaurant_id" && key !== "sort"
            );
            showEmpty(
                results,
                filtered ? "No dishes match your search" : "No dishes are available yet",
                filtered
                    ? "Try removing a filter or searching for something else."
                    : "Please check back soon.",
                filtered ? "Clear all filters" : null,
                resetAll
            );
            return;
        }
        const grid = el(
            "div",
            "row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xl-4 g-4"
        );
        meals.forEach((meal) =>
            grid.appendChild(
                renderMealCard(meal, { hideRestaurant: Boolean(fixedRestaurant) })
            )
        );
        results.replaceChildren(grid);
        summary.textContent =
            pagination.total === 1 ? "1 dish found" : `${pagination.total} dishes found`;
        renderPagination(pager, pagination, (next) => {
            page = next;
            load();
            window.scrollTo(0, 0);
        });
    }

    function resetAll() {
        form.reset();
        FILTER_FIELDS.forEach((name) => {
            const input = field(name);
            if (input) {
                input.value = "";
            }
        });
        page = 1;
        load();
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        page = 1;
        load();
    });
    reset.addEventListener("click", resetAll);
    [
        "category_id", "restaurant_id", "cuisine", "meal_type", "food_type",
        "dietary_preference", "spice_level", "sort"
    ].forEach((name) => {
        const input = field(name);
        if (input) {
            input.addEventListener("change", () => {
                page = 1;
                load();
            });
        }
    });

    return load();
}

/* ---------- restaurant menu page header ---------- */

async function initRestaurantMenuPage() {
    const header = document.getElementById("restaurantHeader");
    const content = document.getElementById("menuContent");
    const id = parseIdParam(new URLSearchParams(window.location.search).get("id"));

    if (!id) {
        content.hidden = true;
        showEmpty(header, "Restaurant not found", "The link is missing a valid restaurant.", null, null);
        return;
    }
    showLoading(header, "Loading restaurant...");
    const response = await fetchRestaurant(id);

    if (response.status === 404) {
        content.hidden = true;
        showEmpty(header, "Restaurant not found", "It may no longer be available.", null, null);
        return;
    }
    if (!response.ok) {
        content.hidden = true;
        showError(
            header,
            response.data.error || "Could not load the restaurant.",
            initRestaurantMenuPage
        );
        return;
    }

    const r = response.data.restaurant;
    document.title = `${r.name} - Food DNA`;
    const box = el("div", "fd-card p-4");
    box.appendChild(el("h1", "h3 mb-1", r.name));
    if (r.description) {
        box.appendChild(el("p", "text-secondary mb-2", r.description));
    }
    if (r.address) {
        box.appendChild(el("div", "small", r.address));
    }
    if (r.phone) {
        box.appendChild(el("div", "small text-secondary", `Phone: ${r.phone}`));
    }
    header.replaceChildren(box);

    content.hidden = false;
    return initMealBrowser({ restaurantId: id });
}

/* ---------- meal details page ---------- */

async function initMealDetailPage() {
    const holder = document.getElementById("mealDetail");
    const id = parseIdParam(new URLSearchParams(window.location.search).get("id"));

    if (!id) {
        showEmpty(holder, "Dish not found", "The link is missing a valid dish.", null, null);
        return;
    }
    showLoading(holder, "Loading dish...");
    const response = await fetchMeal(id);

    if (response.status === 404) {
        showEmpty(holder, "Dish not found", "It may be sold out or no longer on the menu.", null, null);
        return;
    }
    if (!response.ok) {
        showError(
            holder,
            response.data.error || "Could not load the dish.",
            initMealDetailPage
        );
        return;
    }

    const meal = response.data.meal;
    document.title = `${meal.name} - Food DNA`;
    const card = el("div", "fd-card overflow-hidden");
    const row = el("div", "row g-0");

    const imageCol = el("div", "col-md-5");
    imageCol.appendChild(createMealImage(meal, "fd-meal-img-large"));

    const info = el("div", "col-md-7 p-4");
    info.appendChild(el("h1", "h3 mb-2", meal.name));
    info.appendChild(mealTags(meal));
    info.appendChild(el("div", "fs-3 fw-bold fd-price mb-3", formatPrice(meal.price)));
    if (meal.description) {
        info.appendChild(el("p", "", meal.description));
    }

    const list = el("dl", "row small mb-3");
    [
        ["Taste", meal.taste],
        ["Spice level", meal.spice_level],
        ["Portion size", meal.portion_size],
        ["Dietary preference", meal.dietary_preference],
        ["Cuisine", meal.cuisine],
        ["Meal type", meal.meal_type]
    ].forEach(([label, value]) => {
        if (value) {
            list.appendChild(el("dt", "col-5 col-sm-4", label));
            list.appendChild(el("dd", "col-7 col-sm-8", value));
        }
    });
    info.appendChild(list);

    if (meal.restaurant) {
        const from = el("p", "mb-3");
        from.appendChild(document.createTextNode("From "));
        const link = el("a", "fw-semibold", meal.restaurant.name);
        link.href = `restaurant-menu.html?id=${encodeURIComponent(meal.restaurant.id)}`;
        from.appendChild(link);
        if (meal.restaurant.address) {
            from.appendChild(el("div", "small text-secondary", meal.restaurant.address));
        }
        info.appendChild(from);
    }

    const cartBox = el("div", "d-flex align-items-center gap-2 mb-3");
    const qtySelect = el("select", "form-select w-auto");
    for (let i = 1; i <= 10; i++) {
        const opt = el("option", "", String(i));
        opt.value = String(i);
        qtySelect.appendChild(opt);
    }
    const addDetailBtn = el("button", "btn btn-fd", "Add to Cart");
    addDetailBtn.type = "button";
    addDetailBtn.addEventListener("click", () => {
        handleAddToCart(addDetailBtn, meal.id, Number(qtySelect.value), meal.name);
    });
    cartBox.append(el("label", "form-label me-1 mb-0 small fw-semibold", "Qty:"), qtySelect, addDetailBtn);
    info.appendChild(cartBox);

    const actions = el("div", "d-flex flex-wrap gap-2");
    if (meal.restaurant) {
        const menu = el("a", "btn btn-outline-secondary", "View restaurant menu");
        menu.href = `restaurant-menu.html?id=${encodeURIComponent(meal.restaurant.id)}`;
        actions.appendChild(menu);
    }
    const all = el("a", "btn btn-outline-dark", "Back to food menu");
    all.href = "menu.html";
    actions.appendChild(all);
    info.appendChild(actions);

    row.append(imageCol, info);
    card.appendChild(row);
    holder.replaceChildren(card);

    // Phase 5 Food Memory: customers only, best effort, never blocks the page.
    recordMealViewIfCustomer(meal.id);
}
