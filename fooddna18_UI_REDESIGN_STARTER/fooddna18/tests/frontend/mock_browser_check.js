/*
 * Optional developer tool: runs the REAL Food DNA pages in a REAL headless
 * Chromium (via Playwright) against a small STAND-IN API server.
 *
 * IMPORTANT: this is NOT the Flask backend and NOT MySQL. The stand-in
 * server (below) imitates the shape of the Phase 4 API using the demo data
 * in mock_data.json, so it checks the frontend JavaScript and DOM behaviour
 * only. It proves nothing about Flask, SQLAlchemy or MySQL; the pytest suite
 * and manual testing cover those.
 *
 * Usage (from this folder, with Playwright and a Chromium browser installed):
 *     node mock_browser_check.js
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const FRONTEND = path.resolve(__dirname, "..", "..", "frontend");
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, "mock_data.json"), "utf8"));
const FRONT_PORT = 5500;
const API_PORT = 5000;
const ORIGIN = `http://127.0.0.1:${FRONT_PORT}`;

/* ---------------- stand-in API ---------------- */

const apiCalls = [];
const extraMeals = [];   // added by individual checks (e.g. an XSS name)

function visibleMeals() {
    const approved = new Set(DATA.restaurants.filter((r) => r.status === "approved").map((r) => r.id));
    const active = new Set(DATA.categories.filter((c) => c.is_active).map((c) => c.id));
    return DATA.meals.concat(extraMeals).filter(
        (m) => m.is_available && approved.has(m.restaurant_id) && active.has(m.category_id)
    );
}

function pageOf(list, query) {
    const page = Number(query.get("page") || 1);
    const size = Number(query.get("page_size") || 12);
    const total = list.length;
    return {
        items: list.slice((page - 1) * size, page * size),
        pagination: { page, page_size: size, total, total_pages: total ? Math.ceil(total / size) : 0 }
    };
}

function serializeMeal(m, detail) {
    const r = DATA.restaurants.find((x) => x.id === m.restaurant_id);
    const c = DATA.categories.find((x) => x.id === m.category_id);
    const restaurant = { id: r.id, name: r.name };
    if (detail) { restaurant.address = r.address; }
    return {
        id: m.id, name: m.name, description: m.description,
        price: Number(m.price).toFixed(2), cuisine: m.cuisine, meal_type: m.meal_type,
        taste: m.taste, spice_level: m.spice_level, portion_size: m.portion_size,
        dietary_preference: m.dietary_preference, food_type: m.food_type,
        image_url: m.image_url, restaurant, category: { id: c.id, name: c.name }
    };
}

function distinct(list, key) {
    return [...new Set(list.map((m) => m[key]).filter(Boolean))].sort();
}

function handleApi(req, res) {
    const url = new URL(req.url, `http://127.0.0.1:${API_PORT}`);
    apiCalls.push(url.pathname + url.search);
    const send = (status, body) => {
        res.writeHead(status, {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ORIGIN,
            "Access-Control-Allow-Credentials": "true"
        });
        res.end(JSON.stringify(body));
    };
    const q = url.searchParams;
    const p = url.pathname;

    if (p === "/api/auth/me") { return send(401, { success: false, error: "Authentication required." }); }
    if (p === "/api/health") { return send(200, { success: true, status: "healthy" }); }
    if (p === "/api/health/db") { return send(200, { success: true, status: "database_ok" }); }

    if (p === "/api/restaurants") {
        const text = (q.get("q") || "").toLowerCase();
        const meals = visibleMeals();
        const list = DATA.restaurants
            .filter((r) => r.status === "approved" && r.name.toLowerCase().includes(text))
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((r) => ({
                id: r.id, name: r.name, description: r.description, address: r.address,
                meal_count: meals.filter((m) => m.restaurant_id === r.id).length
            }));
        const { items, pagination } = pageOf(list, q);
        return send(200, { success: true, restaurants: items, pagination });
    }
    let match = p.match(/^\/api\/restaurants\/(.+)$/);
    if (match) {
        if (!/^[1-9]\d*$/.test(match[1])) { return send(400, { success: false, error: "restaurant id must be a positive whole number." }); }
        const r = DATA.restaurants.find((x) => String(x.id) === match[1] && x.status === "approved");
        if (!r) { return send(404, { success: false, error: "Restaurant not found." }); }
        const count = visibleMeals().filter((m) => m.restaurant_id === r.id).length;
        return send(200, { success: true, restaurant: {
            id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone, meal_count: count } });
    }
    if (p === "/api/categories") {
        const meals = visibleMeals();
        return send(200, { success: true, categories: DATA.categories.filter((c) => c.is_active).map((c) => ({
            id: c.id, name: c.name, description: c.description,
            meal_count: meals.filter((m) => m.category_id === c.id).length })) });
    }
    if (p === "/api/meals/filters") {
        const meals = visibleMeals();
        const prices = meals.map((m) => Number(m.price));
        return send(200, { success: true, filters: {
            cuisines: distinct(meals, "cuisine"), meal_types: distinct(meals, "meal_type"),
            food_types: distinct(meals, "food_type"), dietary_preferences: distinct(meals, "dietary_preference"),
            spice_levels: distinct(meals, "spice_level"),
            price_range: { min: Math.min(...prices).toFixed(2), max: Math.max(...prices).toFixed(2) } } });
    }
    if (p === "/api/meals") {
        const plain = /^\d{1,7}(\.\d{1,2})?$/;
        for (const key of ["min_price", "max_price"]) {
            if (q.get(key) && !plain.test(q.get(key))) {
                return send(400, { success: false, error: `${key} must be a plain number with at most 2 decimal places.` });
            }
        }
        if (q.get("min_price") && q.get("max_price") && Number(q.get("min_price")) > Number(q.get("max_price"))) {
            return send(400, { success: false, error: "min_price cannot be greater than max_price." });
        }
        let list = visibleMeals();
        const text = (q.get("q") || "").toLowerCase();
        if (text) { list = list.filter((m) => m.name.toLowerCase().includes(text) || (m.description || "").toLowerCase().includes(text)); }
        for (const key of ["restaurant_id", "category_id"]) {
            if (q.get(key)) { list = list.filter((m) => String(m[key]) === q.get(key)); }
        }
        for (const key of ["cuisine", "meal_type", "food_type", "dietary_preference", "spice_level"]) {
            if (q.get(key)) { list = list.filter((m) => String(m[key] || "").toLowerCase() === q.get(key).toLowerCase()); }
        }
        if (q.get("min_price")) { list = list.filter((m) => Number(m.price) >= Number(q.get("min_price"))); }
        if (q.get("max_price")) { list = list.filter((m) => Number(m.price) <= Number(q.get("max_price"))); }
        const sort = q.get("sort") || "name";
        list.sort((a, b) =>
            sort === "price_asc" ? Number(a.price) - Number(b.price) || a.name.localeCompare(b.name)
            : sort === "price_desc" ? Number(b.price) - Number(a.price) || a.name.localeCompare(b.name)
            : a.name.localeCompare(b.name));
        const { items, pagination } = pageOf(list, q);
        return send(200, { success: true, meals: items.map((m) => serializeMeal(m, false)), pagination });
    }
    match = p.match(/^\/api\/meals\/(.+)$/);
    if (match) {
        if (!/^[1-9]\d*$/.test(match[1])) { return send(400, { success: false, error: "meal id must be a positive whole number." }); }
        const m = visibleMeals().find((x) => String(x.id) === match[1]);
        if (!m) { return send(404, { success: false, error: "Meal not found." }); }
        return send(200, { success: true, meal: serializeMeal(m, true) });
    }
    send(404, { success: false, error: "Resource not found." });
}

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };

function handleStatic(req, res) {
    const url = new URL(req.url, ORIGIN);
    const file = path.join(FRONTEND, url.pathname === "/" ? "index.html" : url.pathname);
    if (!file.startsWith(FRONTEND) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); res.end("not found"); return;
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
}

/* ---------------- tiny test harness ---------------- */

const results = [];
async function check(name, fn) {
    try {
        await fn();
        results.push({ name, ok: true });
        console.log(`PASS  ${name}`);
    } catch (error) {
        results.push({ name, ok: false, error: error.message });
        console.log(`FAIL  ${name}\n      ${error.message.split("\n")[0]}`);
    }
}
function expect(condition, message) {
    if (!condition) { throw new Error(message); }
}

(async () => {
    const apiServer = http.createServer(handleApi).listen(API_PORT, "127.0.0.1");
    const staticServer = http.createServer(handleStatic).listen(FRONT_PORT, "127.0.0.1");
    const browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1200, height: 900 } });
    // The Bootstrap stylesheet comes from a CDN; layout/CSS is not part of this check.
    await context.route(/cdn\.jsdelivr\.net/, (route) => route.abort());
    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const open = (file) => page.goto(`${ORIGIN}/${file}`);
    const count = (selector) => page.locator(selector).count();
    const settle = () => page.waitForFunction(() => !document.querySelector('[data-state="loading"]'));

    await check("home page has browse links and the Food DNA branding", async () => {
        await open("index.html");
        expect((await page.textContent("body")).includes("Food DNA"), "branding missing");
        expect(await count('a[href="restaurants.html"].btn') === 1, "restaurants button missing");
        expect(await count('a[href="menu.html"].btn') === 1, "menu button missing");
        expect(await count("nav a.nav-link") >= 5, "navbar links missing");
    });

    await check("restaurant list shows only approved restaurants from the API", async () => {
        await open("restaurants.html"); await settle();
        expect(await count("[data-restaurant-id]") === 6, "expected 6 approved restaurants");
        expect(!(await page.textContent("body")).includes("Pending Kitchen"), "pending restaurant visible");
        expect(apiCalls.some((c) => c.startsWith("/api/restaurants")), "API not called");
    });

    await check("restaurant search narrows results and shows an empty state", async () => {
        await open("restaurants.html"); await settle();
        await page.fill("#restaurantSearch", "dragon");
        await page.click("#restaurantSearchForm button[type=submit]"); await settle();
        expect(await count("[data-restaurant-id]") === 1, "expected 1 result");
        await page.fill("#restaurantSearch", "zzzz");
        await page.click("#restaurantSearchForm button[type=submit]"); await settle();
        expect(await count('[data-state="empty"]') === 1, "empty state missing");
    });

    await check("restaurant card opens its own menu", async () => {
        await open("restaurants.html"); await settle();
        await page.click("[data-restaurant-id] a.btn >> nth=0"); await settle();
        await page.waitForSelector("[data-meal-id]");
        expect(page.url().includes("restaurant-menu.html?id="), "wrong URL: " + page.url());
        expect(await count("#restaurantHeader h1") === 1, "restaurant header missing");
        expect(await count("[data-meal-id]") > 0, "no dishes");
    });

    await check("food menu: 12 per page, 32 dishes, pagination Next/Previous", async () => {
        await open("menu.html"); await settle();
        expect(await count("[data-meal-id]") === 12, "expected 12 cards on page 1");
        expect((await page.textContent("#mealSummary")).includes("32"), "summary should say 32");
        await page.click("#mealPager >> text=Next"); await settle();
        expect(page.url().includes("page=2"), "page=2 missing from URL");
        expect((await page.textContent("#mealPager")).includes("Page 2 of 3"), "pager label wrong");
        await page.click("#mealPager >> text=Previous"); await settle();
        expect((await page.textContent("#mealPager")).includes("Page 1 of 3"), "did not go back");
    });

    await check("filters (cuisine, category, price, sort) call the API and change results", async () => {
        await open("menu.html"); await settle();
        await page.selectOption("#fCuisine", "Chinese"); await settle();
        expect(await count("[data-meal-id]") === 5, "Chinese should have 5 dishes");
        expect(apiCalls.some((c) => c.includes("cuisine=Chinese")), "cuisine param not sent");
        await page.fill("#fMin", "150"); await page.fill("#fMax", "170");
        await page.click("#filterForm button[type=submit]"); await settle();
        const prices = await page.$$eval(".fd-price", (n) => n.map((x) => Number(x.textContent.replace(/[^0-9.]/g, ""))));
        expect(prices.length > 0 && prices.every((x) => x >= 150 && x <= 170), "price filter not applied: " + prices);
        await page.selectOption("#fSort", "price_desc"); await settle();
        const sorted = await page.$$eval(".fd-price", (n) => n.map((x) => Number(x.textContent.replace(/[^0-9.]/g, ""))));
        expect(sorted.every((x, i) => i === 0 || sorted[i - 1] >= x), "not sorted high to low");
    });

    await check("invalid price range is rejected in the form without calling the API", async () => {
        await open("menu.html"); await settle();
        const before = apiCalls.length;
        await page.fill("#fMin", "500"); await page.fill("#fMax", "100");
        await page.click("#filterForm button[type=submit]");
        await page.waitForSelector("#filterMessage .alert");
        expect((await page.textContent("#filterMessage")).includes("Minimum price"), "message missing");
        expect(apiCalls.slice(before).every((c) => !c.includes("min_price=500")), "invalid range reached API");
        await page.fill("#fMin", "abc"); await page.fill("#fMax", "");
        await page.click("#filterForm button[type=submit]");
        expect((await page.textContent("#filterMessage")).includes("Prices must"), "non-numeric message missing");
    });

    await check("no matches: empty state, and Clear all filters restores the list", async () => {
        await open("menu.html"); await settle();
        await page.fill("#fSearch", "zzzznothing");
        await page.click("#filterForm button[type=submit]"); await settle();
        expect(await count('[data-state="empty"]') === 1, "empty state missing");
        await page.click('[data-state="empty"] button'); await settle();
        expect(await count("[data-meal-id]") === 12, "list not restored");
    });

    await check("meal details page shows the dish; bad and missing ids are handled", async () => {
        await open("meal.html?id=1"); await settle();
        await page.waitForSelector("#mealDetail h1");
        expect((await page.textContent("#mealDetail h1")).length > 0, "name missing");
        expect(await count('#mealDetail a[href^="restaurant-menu.html?id="]') >= 1, "restaurant link missing");
        await open("meal.html?id=abc"); await settle();
        expect((await page.textContent("#mealDetail")).includes("Dish not found"), "bad id message missing");
        await open("meal.html?id=9999"); await settle();
        expect((await page.textContent("#mealDetail")).includes("Dish not found"), "404 message missing");
    });

    await check("database text is shown as text, never run as HTML (XSS)", async () => {
        extraMeals.push({ id: 900, restaurant_id: 1, category_id: 1, name: "<img src=x onerror=window.__xss=1>",
            description: "<script>window.__xss=1</script>", price: "10.00", cuisine: "Test", meal_type: "Snack",
            taste: "Sweet", spice_level: "None", portion_size: "Small", dietary_preference: null,
            food_type: "Veg", image_url: "javascript:alert(1)", is_available: true });
        await open("menu.html?q=img"); await settle();
        expect(await count("[data-meal-id]") === 1, "injected dish not listed");
        expect(await page.evaluate(() => window.__xss === undefined), "script executed");
        expect(await count("[data-meal-id] img") === 0, "unsafe image created");
        extraMeals.length = 0;
    });

    await check("Phase 3 pages still load without JavaScript errors", async () => {
        for (const file of ["login.html", "register.html", "forgot-password.html", "restaurant-admin-application.html"]) {
            await open(file);
            await page.waitForSelector("#navbar nav");
        }
        expect(pageErrors.length === 0, "page errors: " + pageErrors.join("; "));
    });

    await check("registration accepts letters/spaces only and Gmail-only account emails", async () => {
        await open("register.html");
        const ok = await page.evaluate(() => NAME_RULE.test("José García")
            && !NAME_RULE.test("José García-O'Brien")
            && !NAME_RULE.test("Asha 123")
            && EMAIL_RULE.test("jose@gmail.com")
            && EMAIL_RULE.test("first.last+tag@gmail.com")
            && !EMAIL_RULE.test("jose@example.in")
            && !EMAIL_RULE.test("a@college.edu")
            && !EMAIL_RULE.test("rushi@gmail.co")
            && !EMAIL_RULE.test("rushi@gmail.com.evil"));
        expect(ok, "client-side registration rules disagree with the requested validation policy");
    });

    await check("backend unavailable: friendly error with a Try again button", async () => {
        apiServer.close();
        apiServer.closeAllConnections();
        await open("restaurants.html"); await settle();
        const text = await page.textContent('[data-state="error"]');
        expect(text.includes("Cannot reach the server"), "friendly error missing: " + text);
        expect(await count('[data-state="error"] button') === 1, "Try again button missing");
        await open("menu.html"); await settle();
        expect(await count('[data-state="error"]') === 1, "menu page error state missing");
    });

    await browser.close();
    staticServer.close();

    const failed = results.filter((r) => !r.ok).length;
    console.log(`\nSTAND-IN API BROWSER CHECK: ${results.length - failed} passed, ${failed} failed (of ${results.length})`);
    process.exit(failed ? 1 : 0);
})();
