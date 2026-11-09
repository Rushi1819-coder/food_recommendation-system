/*
 * Food DNA - personalised recommendations page (Phase 5).
 *
 * Needs js/api.js and js/browse.js. Every recommendation, score and
 * explanation comes from the Flask API (computed from the customer's saved
 * preferences); nothing is hard-coded. Server text is inserted with
 * textContent only.
 */

const PREFERENCE_LABELS = {
    cuisine: "Cuisine",
    meal_type: "Meal type",
    taste: "Taste",
    spice_level: "Spice",
    portion_size: "Portion",
    food_type: "Food type",
    dietary_preference: "Diet",
    budget: "Budget"
};

const EXCLUSION_LABELS = {
    budget: "over your budget",
    food_type: "not your food type",
    dietary_preference: "not matching your dietary preference"
};

/** Record the click, then open the dish (never waits more than ~1 second). */
function openRecommendedMeal(event, mealId, href) {
    // Let new-tab / new-window clicks behave normally.
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
    }
    event.preventDefault();
    const timeout = new Promise((resolve) => setTimeout(resolve, 900));
    Promise.race([recordRecommendationSelection(mealId), timeout]).then(() => {
        window.location.href = href;
    });
}

function renderRecommendationCard(item) {
    const meal = item.meal;
    const href = `meal.html?id=${encodeURIComponent(meal.id)}`;
    const col = el("div", "col");
    const card = el("article", "card h-100 fd-card-item position-relative");
    card.setAttribute("data-meal-id", meal.id);

    card.appendChild(createMealImage(meal));
    card.appendChild(el("span", "fd-rank", `#${item.rank}`));

    const body = el("div", "card-body d-flex flex-column");

    const titleRow = el("div", "d-flex justify-content-between align-items-start gap-2 mb-1");
    const title = el("h2", "h5 card-title mb-0");
    const link = el("a", "text-decoration-none", meal.name);
    link.href = href;
    link.addEventListener("click", (event) => openRecommendedMeal(event, meal.id, href));
    title.appendChild(link);
    const percent = Math.round(Number(item.score));
    titleRow.append(
        title,
        el("span", "badge fd-score flex-shrink-0", `${Number.isFinite(percent) ? percent : 0}% match`)
    );
    body.appendChild(titleRow);

    if (meal.restaurant) {
        const where = el("div", "small mb-2");
        const restaurantLink = el("a", "", meal.restaurant.name);
        restaurantLink.href = `restaurant-menu.html?id=${encodeURIComponent(meal.restaurant.id)}`;
        where.appendChild(restaurantLink);
        body.appendChild(where);
    }
    body.appendChild(mealTags(meal));

    // Why this dish was chosen (text written by the server).
    body.appendChild(el("div", "small fw-semibold mb-1", "Why it matches"));
    const reasons = el("ul", "small text-secondary fd-reasons");
    (item.reasons || []).forEach((reason) => reasons.appendChild(el("li", "", reason)));
    body.appendChild(reasons);

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

    const open = el("a", "btn btn-outline-dark btn-sm mt-2", "View dish");
    open.href = href;
    open.addEventListener("click", (event) => openRecommendedMeal(event, meal.id, href));
    body.appendChild(open);

    card.appendChild(body);
    col.appendChild(card);
    return col;
}

function renderPreferenceChips(holder, preferences) {
    holder.replaceChildren();
    Object.entries(preferences || {}).forEach(([name, value]) => {
        const text = name === "budget" ? `up to ${formatPrice(value)}` : value;
        holder.appendChild(
            el("span", "fd-pref-chip", `${PREFERENCE_LABELS[name] || name}: ${text}`)
        );
    });
}

function describeExclusions(summary) {
    const parts = Object.entries(summary.excluded || {})
        .filter(([, count]) => count > 0)
        .map(([rule, count]) => `${count} ${EXCLUSION_LABELS[rule] || rule}`);
    return parts.length ? `Hidden because: ${parts.join(", ")}.` : "";
}

async function initRecommendationsPage() {
    const pageMessage = document.getElementById("recPageMessage");
    const content = document.getElementById("recContent");
    const summary = document.getElementById("recSummary");
    const prefsHolder = document.getElementById("recPrefs");
    const notes = document.getElementById("recNotes");
    const results = document.getElementById("recResults");
    const limitSelect = document.getElementById("recLimit");
    const refresh = document.getElementById("recRefresh");
    const historyResults = document.getElementById("historyResults");
    const historyPager = document.getElementById("historyPager");

    const user = await requireLogin();
    if (!user) {
        return;
    }
    if (user.role !== "customer") {
        showMessage(
            pageMessage,
            "info",
            "Personalised recommendations are available to customer accounts only."
        );
        return;
    }
    content.hidden = false;

    let requestCounter = 0;
    let historyPage = 1;

    async function loadHistory() {
        showLoading(historyResults, "Loading history...");
        historyPager.replaceChildren();
        const response = await fetchRecommendationHistory({ page: historyPage, page_size: 8 });
        if (!response.ok) {
            showError(
                historyResults,
                response.data.error || "Could not load your history.",
                loadHistory
            );
            return;
        }
        const { history, pagination } = response.data;
        if (!history.length) {
            if (pagination.total > 0 && historyPage > 1) {
                historyPage = 1;
                return loadHistory();
            }
            showEmpty(
                historyResults,
                "No history yet",
                "Recommendations you receive will be listed here."
            );
            return;
        }

        const wrap = el("div", "table-responsive");
        const table = el("table", "table table-sm align-middle");
        const head = el("thead");
        const headRow = el("tr");
        ["When", "Dish", "Restaurant", "Match"].forEach((label) =>
            headRow.appendChild(el("th", "", label))
        );
        head.appendChild(headRow);
        const bodyEl = el("tbody");
        history.forEach((entry) => {
            const row = el("tr");
            const when = new Date(entry.generated_at);
            row.appendChild(
                el("td", "text-nowrap small", Number.isNaN(when.getTime()) ? "" : when.toLocaleString())
            );
            const dish = el("td");
            if (entry.currently_available) {
                const link = el("a", "", entry.meal.name);
                link.href = `meal.html?id=${encodeURIComponent(entry.meal.id)}`;
                dish.appendChild(link);
            } else {
                dish.appendChild(el("span", "", entry.meal.name));
                dish.appendChild(el("div", "small text-secondary", "No longer available"));
            }
            row.appendChild(dish);
            row.appendChild(el("td", "small", entry.meal.restaurant_name));
            row.appendChild(el("td", "small", `${Math.round(Number(entry.score))}%`));
            bodyEl.appendChild(row);
        });
        table.append(head, bodyEl);
        wrap.appendChild(table);
        historyResults.replaceChildren(wrap);
        renderPagination(historyPager, pagination, (next) => {
            historyPage = next;
            loadHistory();
        });
    }

    async function load() {
        const mine = ++requestCounter;
        showLoading(results, "Finding dishes you will like...");
        summary.textContent = "";
        notes.textContent = "";
        prefsHolder.replaceChildren();

        const response = await generateRecommendations(Number(limitSelect.value));
        if (mine !== requestCounter) {
            return;
        }
        if (!response.ok) {
            showError(
                results,
                response.data.error || "Could not load your recommendations.",
                load
            );
            return;
        }

        const data = response.data;
        renderPreferenceChips(prefsHolder, data.preferences);

        if (!data.has_preferences) {
            showEmpty(
                results,
                "Tell us what you like",
                data.message || "Set your food preferences to get recommendations.",
                "Set my preferences",
                () => { window.location.href = "preferences.html"; }
            );
            summary.textContent = "";
        } else if (!data.recommendations.length) {
            showEmpty(
                results,
                "No matching dishes right now",
                data.message || "No dishes matched your preferences.",
                "Change my preferences",
                () => { window.location.href = "preferences.html"; }
            );
            notes.textContent = describeExclusions(data.summary);
        } else {
            const grid = el(
                "div",
                "row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-4"
            );
            data.recommendations.forEach((item) =>
                grid.appendChild(renderRecommendationCard(item))
            );
            results.replaceChildren(grid);
            summary.textContent =
                data.recommendations.length === 1
                    ? "1 dish picked from your preferences"
                    : `${data.recommendations.length} dishes picked from your preferences`;
            notes.textContent = describeExclusions(data.summary);
        }

        historyPage = 1;
        loadHistory();
    }

    refresh.addEventListener("click", load);
    limitSelect.addEventListener("change", load);
    return load();
}
