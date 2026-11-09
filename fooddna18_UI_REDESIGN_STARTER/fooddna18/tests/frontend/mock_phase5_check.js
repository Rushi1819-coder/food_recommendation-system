/*
 * Optional developer tool (Phase 5): runs the REAL preferences and
 * recommendations pages in headless Chromium against a STAND-IN API.
 *
 * IMPORTANT: the stand-in is NOT Flask and NOT MySQL, and its "recommender"
 * is a trivial imitation. This only checks page behaviour (forms, requests
 * sent, states, safe text handling). It says nothing about the real scoring,
 * validation or database code; the pytest files cover those.
 *
 * Usage (from this folder, with Playwright and Chromium installed):
 *     node mock_phase5_check.js
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
const CSRF = "stand-in-csrf-token";

/* ---------------- stand-in state and API ---------------- */

let state;
function resetState(overrides) {
    state = Object.assign({
        user: { id: 1, full_name: "Test Customer", email: "t@example.com", role: "customer",
                account_status: "active", approval_status: "not_required", is_active: true },
        prefs: null,
        calls: [],
        history: [],
        xssName: false
    }, overrides || {});
}

const approved = () => new Set(DATA.restaurants.filter((r) => r.status === "approved").map((r) => r.id));
const active = () => new Set(DATA.categories.filter((c) => c.is_active).map((c) => c.id));
function visible() {
    return DATA.meals.filter((m) => m.is_available && approved().has(m.restaurant_id) && active().has(m.category_id));
}
function distinct(list, key) {
    return [...new Set(list.map((m) => m[key]).filter(Boolean))].sort();
}
function serializeMeal(m) {
    const r = DATA.restaurants.find((x) => x.id === m.restaurant_id);
    const c = DATA.categories.find((x) => x.id === m.category_id);
    return {
        id: m.id, name: state.xssName && m.id === 1 ? "<img src=x onerror=window.__xss=1>" : m.name,
        description: m.description, price: Number(m.price).toFixed(2), cuisine: m.cuisine,
        meal_type: m.meal_type, taste: m.taste, spice_level: m.spice_level, portion_size: m.portion_size,
        dietary_preference: m.dietary_preference, food_type: m.food_type, image_url: null,
        restaurant: { id: r.id, name: r.name, address: r.address }, category: { id: c.id, name: c.name }
    };
}

function readBody(req) {
    return new Promise((resolve) => {
        let text = "";
        req.on("data", (chunk) => { text += chunk; });
        req.on("end", () => { try { resolve(JSON.parse(text || "null")); } catch (e) { resolve(null); } });
    });
}

async function handleApi(req, res) {
    const url = new URL(req.url, `http://127.0.0.1:${API_PORT}`);
    const send = (status, body) => {
        res.writeHead(status, {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ORIGIN,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
            "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS"
        });
        res.end(JSON.stringify(body));
    };
    if (req.method === "OPTIONS") { return send(204, {}); }
    const p = url.pathname;
    const body = ["POST", "PUT"].includes(req.method) ? await readBody(req) : null;
    state.calls.push({ method: req.method, path: p, csrf: req.headers["x-csrf-token"], body });

    if (p === "/api/auth/me") {
        return state.user ? send(200, { success: true, user: state.user })
                          : send(401, { success: false, error: "Authentication required." });
    }
    if (p === "/api/auth/csrf") { return send(200, { success: true, csrf_token: CSRF }); }
    if (!state.user) { return send(401, { success: false, error: "Authentication required." }); }

    if (p === "/api/meals/filters") {
        const meals = visible();
        return send(200, { success: true, filters: {
            cuisines: distinct(meals, "cuisine"), meal_types: distinct(meals, "meal_type"),
            tastes: distinct(meals, "taste"), portion_sizes: distinct(meals, "portion_size"),
            food_types: distinct(meals, "food_type"), dietary_preferences: distinct(meals, "dietary_preference"),
            spice_levels: distinct(meals, "spice_level"), price_range: { min: "40.00", max: "340.00" } } });
    }
    if (p === "/api/preferences" && req.method === "GET") {
        return send(200, { success: true, preferences: state.prefs,
            has_preferences: Boolean(state.prefs && Object.values(state.prefs).some((v) => v)) });
    }
    if (p === "/api/preferences" && req.method === "PUT") {
        if (req.headers["x-csrf-token"] !== CSRF) { return send(403, { success: false, error: "Invalid CSRF token." }); }
        if (body && body.cuisine === "Rejected Cuisine") {
            return send(400, { success: false, error: "Please correct the highlighted preferences.",
                errors: { cuisine: "Server says no to this cuisine." } });
        }
        const created = state.prefs === null;
        state.prefs = Object.assign({ cuisine: null, meal_type: null, taste: null, spice_level: null,
            portion_size: null, food_type: null, dietary_preference: null, budget: null }, body,
            { updated_at: "2026-10-12T05:30:00Z" });
        return send(created ? 201 : 200, { success: true, message: "Preferences saved.", created, preferences: state.prefs });
    }
    if (p === "/api/recommendations" && req.method === "POST") {
        const prefs = state.prefs && Object.fromEntries(Object.entries(state.prefs).filter(([k, v]) => v && k !== "updated_at"));
        if (!prefs || !Object.keys(prefs).length) {
            return send(200, { success: true, has_preferences: false, preferences: {}, recommendations: [],
                summary: { limit: body.limit, returned: 0, visible_meals: 0, excluded: {}, no_match: 0 },
                message: "You have not saved any food preferences yet. Set your preferences to get personalised recommendations.",
                history: { created: 0, updated: 0 } });
        }
        const picks = visible().filter((m) => !prefs.cuisine || m.cuisine === prefs.cuisine).slice(0, body.limit);
        const recs = picks.map((m, i) => ({ rank: i + 1, score: (100 - i * 10).toFixed(2), matched: ["cuisine"],
            partial: [], reasons: [`Cuisine matches your preference: ${m.cuisine}`, "Price is within your budget"],
            meal: serializeMeal(m) }));
        state.history = recs.map((r, i) => ({ id: i + 1, score: r.score, reason: "x", generated_at: "2026-10-12T05:00:00Z",
            meal: { id: r.meal.id, name: r.meal.name, price: r.meal.price, restaurant_name: r.meal.restaurant.name },
            currently_available: i !== 1 }));
        return send(200, { success: true, has_preferences: true, preferences: prefs, recommendations: recs,
            summary: { limit: body.limit, returned: recs.length, visible_meals: 32, excluded: { budget: 3 }, no_match: 0 },
            message: recs.length ? null : "No available meals matched your preferences.",
            history: { created: recs.length, updated: 0 } });
    }
    if (p === "/api/recommendations/history") {
        return send(200, { success: true, history: state.history,
            pagination: { page: 1, page_size: 8, total: state.history.length, total_pages: 1 } });
    }
    let match = p.match(/^\/api\/recommendations\/(\d+)\/select$/);
    if (match) { return send(200, { success: true, recorded: true }); }
    if (p === "/api/food-memory/meal-views") { return send(200, { success: true, recorded: true }); }
    match = p.match(/^\/api\/meals\/(\d+)$/);
    if (match) {
        const m = visible().find((x) => String(x.id) === match[1]);
        return m ? send(200, { success: true, meal: serializeMeal(m) })
                 : send(404, { success: false, error: "Meal not found." });
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
    try { await fn(); results.push({ name, ok: true }); console.log(`PASS  ${name}`); }
    catch (error) {
        results.push({ name, ok: false, error: error.message });
        console.log(`FAIL  ${name}\n      ${error.message.split("\n")[0]}`);
    }
}
function expect(condition, message) { if (!condition) { throw new Error(message); } }

(async () => {
    resetState();
    http.createServer(handleApi).listen(API_PORT, "127.0.0.1");
    const staticServer = http.createServer(handleStatic).listen(FRONT_PORT, "127.0.0.1");
    const browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1200, height: 900 } });
    await context.route(/cdn\.jsdelivr\.net/, (route) => route.abort());
    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const open = (file) => page.goto(`${ORIGIN}/${file}`);
    const count = (selector) => page.locator(selector).count();
    const settle = () => page.waitForFunction(() => !document.querySelector('[data-state="loading"]'));
    const puts = () => state.calls.filter((c) => c.method === "PUT");

    await check("customer navbar shows Recommendations and My Preferences", async () => {
        resetState(); await open("index.html"); await page.waitForSelector("#navbar nav");
        expect(await count('nav a[href="recommendations.html"]') === 1, "Recommendations link missing");
        expect(await count('nav a[href="preferences.html"]') === 1, "My Preferences link missing");
    });

    await check("preferences form: dropdowns come from the API, empty form for a new customer", async () => {
        resetState(); await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        const cuisines = await page.$$eval("#pCuisine option", (o) => o.map((x) => x.textContent));
        expect(cuisines[0] === "No preference" && cuisines.includes("Chinese") && cuisines.includes("Italian"), "cuisine options: " + cuisines);
        expect((await page.$$eval("#pTaste option", (o) => o.length)) > 1, "taste options missing");
        expect((await page.$$eval("#pPortion option", (o) => o.length)) > 1, "portion options missing");
        const spice = await page.$$eval("#pSpice option", (o) => o.slice(1).map((x) => x.textContent));
        expect(spice.join() === ["None", "Mild", "Medium", "Hot"].filter((s) => spice.includes(s)).join(), "spice order: " + spice);
        expect((await page.textContent("#savedAt")).includes("not saved"), "new-customer note missing");
    });

    await check("saving sends a PUT with the CSRF header and null for blank fields", async () => {
        resetState(); await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        await page.selectOption("#pCuisine", "Chinese");
        await page.selectOption("#pFoodType", "Veg");
        await page.fill("#pBudget", "250.50");
        await page.click("#saveButton");
        await page.waitForSelector("#pageMessage .alert-success");
        expect(puts().length === 1, "expected one PUT");
        const call = puts()[0];
        expect(call.csrf === CSRF, "CSRF header missing");
        expect(call.body.cuisine === "Chinese" && call.body.food_type === "Veg" && call.body.budget === "250.50", "payload: " + JSON.stringify(call.body));
        expect(call.body.taste === null && call.body.spice_level === null, "blank fields should be null");
        expect(!(await page.locator("#afterSave").isHidden()), "link to recommendations not shown");
    });

    await check("saved preferences are loaded back into the form after a reload", async () => {
        await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        expect(await page.inputValue("#pCuisine") === "Chinese", "cuisine not restored");
        expect(await page.inputValue("#pBudget") === "250.50", "budget not restored");
        expect((await page.textContent("#savedAt")).includes("Last saved"), "saved time missing");
    });

    await check("a saved value no dish offers is still shown", async () => {
        resetState({ prefs: { cuisine: "Thai", budget: null, updated_at: "2026-10-12T05:30:00Z" } });
        await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        expect(await page.inputValue("#pCuisine") === "Thai", "Thai not selectable");
    });

    await check("invalid budget is stopped in the browser (no request) with a field message", async () => {
        resetState(); await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        for (const bad of ["abc", "0", "-5", "12.345", "1e3"]) {
            await page.fill("#pBudget", bad);
            await page.click("#saveButton");
            await page.waitForSelector("#err-budget:not(:empty)");
            expect(await page.locator("#pBudget.is-invalid").count() === 1, "field not marked: " + bad);
        }
        expect(puts().length === 0, "invalid input reached the API");
    });

    await check("server-side field errors are shown next to the field", async () => {
        resetState(); await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        // add an option the stand-in server will reject
        await page.evaluate(() => {
            const o = document.createElement("option"); o.value = "Rejected Cuisine"; o.textContent = "Rejected Cuisine";
            document.getElementById("pCuisine").appendChild(o);
        });
        await page.selectOption("#pCuisine", "Rejected Cuisine");
        await page.click("#saveButton");
        await page.waitForSelector("#err-cuisine:not(:empty)");
        expect((await page.textContent("#err-cuisine")).includes("Server says no"), "server message missing");
        expect(await page.locator("#saveButton").isEnabled(), "button stayed disabled");
    });

    await check("Clear all fields only empties the form; Save then sends all nulls", async () => {
        resetState({ prefs: { cuisine: "Chinese", budget: "100.00", updated_at: "2026-10-12T05:30:00Z" } });
        await open("preferences.html"); await page.waitForSelector("#preferencesForm:not([hidden])");
        await page.click("#clearButton");
        expect(await page.inputValue("#pCuisine") === "" && await page.inputValue("#pBudget") === "", "form not cleared");
        expect(puts().length === 0, "clear must not call the API by itself");
        await page.click("#saveButton"); await page.waitForSelector("#pageMessage .alert-success");
        expect(Object.values(puts()[0].body).every((v) => v === null), "expected all null: " + JSON.stringify(puts()[0].body));
    });

    await check("recommendations without preferences: empty state linking to the form", async () => {
        resetState(); await open("recommendations.html"); await page.waitForSelector('[data-state="empty"]');
        expect((await page.textContent("#recResults")).includes("not saved any food preferences"), "message missing");
        expect(await count("#recResults [data-meal-id]") === 0, "no cards expected");
        await page.click("#recResults button");
        await page.waitForURL(/preferences\.html$/);
    });

    await check("recommendations with preferences: cards, match %, reasons, notes, history", async () => {
        resetState({ prefs: { cuisine: "Chinese", updated_at: "x" } });
        await open("recommendations.html"); await page.waitForSelector("#recResults [data-meal-id]");
        expect(await count("#recResults [data-meal-id]") === 5, "expected 5 Chinese dishes");
        expect((await page.textContent("#recResults")).includes("100% match"), "match percent missing");
        expect((await page.textContent("#recResults")).includes("Cuisine matches your preference"), "reasons missing");
        expect((await page.textContent("#recPrefs")).includes("Cuisine: Chinese"), "preference chips missing");
        expect((await page.textContent("#recNotes")).includes("3 over your budget"), "exclusion note missing");
        await page.waitForSelector("#historyResults table");
        expect(await count("#historyResults tbody tr") === 5, "history rows missing");
        expect((await page.textContent("#historyResults")).includes("No longer available"), "availability flag missing");
        const post = state.calls.find((c) => c.method === "POST" && c.path === "/api/recommendations");
        expect(post && post.csrf === CSRF && post.body.limit === 10, "generate call wrong");
    });

    await check("changing 'How many' and Refresh both request recommendations again", async () => {
        const before = state.calls.filter((c) => c.path === "/api/recommendations").length;
        await page.selectOption("#recLimit", "5");
        await page.waitForFunction(() => document.querySelectorAll("#recResults [data-meal-id]").length === 5);
        await page.click("#recRefresh");
        await page.waitForSelector("#recResults [data-meal-id]");
        const posts = state.calls.filter((c) => c.path === "/api/recommendations");
        expect(posts.length === before + 2 && posts[posts.length - 2].body.limit === 5, "limit not sent");
    });

    await check("clicking a recommendation records the selection, then opens the dish (which records a view)", async () => {
        await page.click("#recResults [data-meal-id] h2 a >> nth=0");
        await page.waitForURL(/meal\.html\?id=\d+/);
        await page.waitForSelector("#mealDetail h1");
        await page.waitForFunction(() => true);
        await new Promise((r) => setTimeout(r, 400));
        expect(state.calls.some((c) => /\/api\/recommendations\/\d+\/select$/.test(c.path) && c.csrf === CSRF), "select call missing");
        expect(state.calls.some((c) => c.path === "/api/food-memory/meal-views" && c.body.meal_id > 0), "meal view call missing");
    });

    await check("server text in recommendations is shown as text, never run as HTML", async () => {
        resetState({ prefs: { cuisine: "North Indian", updated_at: "x" }, xssName: true });
        await open("recommendations.html"); await page.waitForSelector("#recResults [data-meal-id]");
        expect(await page.evaluate(() => window.__xss === undefined), "script executed");
        expect((await page.textContent("#recResults")).includes("<img src=x"), "name should appear as text");
    });

    await check("non-customer accounts see a message instead of the forms", async () => {
        resetState({ user: { id: 2, full_name: "Admin", email: "a@x.in", role: "super_admin",
            account_status: "active", approval_status: "approved", is_active: true } });
        await open("preferences.html"); await page.waitForSelector("#pageMessage .alert");
        expect(await page.locator("#preferencesForm").isHidden(), "form should stay hidden");
        await open("recommendations.html"); await page.waitForSelector("#recPageMessage .alert");
        expect(await page.locator("#recContent").isHidden(), "content should stay hidden");
        expect(await count('nav a[href="preferences.html"]') === 0, "customer nav link shown to admin");
    });

    await check("visitors who are not logged in are sent to the login page", async () => {
        resetState({ user: null });
        await open("preferences.html"); await page.waitForURL(/login\.html$/);
        await open("recommendations.html"); await page.waitForURL(/login\.html$/);
    });

    await check("dashboard offers the customer links; no JavaScript errors on any page", async () => {
        resetState(); await open("dashboard.html"); await page.waitForSelector("#customerActions:not([hidden])");
        expect(pageErrors.length === 0, "page errors: " + pageErrors.join("; "));
    });

    await browser.close();
    staticServer.close();
    const failed = results.filter((r) => !r.ok).length;
    console.log(`\nPHASE 5 STAND-IN API BROWSER CHECK: ${results.length - failed} passed, ${failed} failed (of ${results.length})`);
    process.exit(failed ? 1 : 0);
})();
