/* FoodDNA role-aware dashboards for Phases 7-9. Text is always rendered with textContent. */
(async function () {
    const panel = document.getElementById("roleDashboard");
    if (!panel) return;
    const user = await getCurrentUser();
    if (!user) return;

    function heading(title, subtitle = "") {
        const h = document.createElement("h2"); h.className = "h4 mb-1"; h.textContent = title; panel.appendChild(h);
        if (subtitle) { const p = document.createElement("p"); p.className = "text-secondary small"; p.textContent = subtitle; panel.appendChild(p); }
    }
    function message(text, kind = "info") {
        const p = document.createElement("div"); p.className = `alert alert-${kind}`; p.textContent = text; panel.appendChild(p);
    }
    function link(text, href, cls = "btn btn-outline-primary btn-sm") {
        const a = document.createElement("a"); a.className = cls; a.href = href; a.textContent = text; return a;
    }
    function table(headers, rows) {
        const wrap = document.createElement("div"); wrap.className = "table-responsive mt-3";
        const t = document.createElement("table"); t.className = "table table-sm align-middle";
        const thead = document.createElement("thead"), tr = document.createElement("tr");
        headers.forEach(x => { const th = document.createElement("th"); th.textContent = x; tr.appendChild(th); });
        thead.appendChild(tr); t.appendChild(thead);
        const tbody = document.createElement("tbody");
        rows.forEach(values => { const r = document.createElement("tr"); values.forEach(v => { const td = document.createElement("td"); if (v instanceof Node) td.appendChild(v); else td.textContent = String(v ?? "—"); r.appendChild(td); }); tbody.appendChild(r); });
        if (!rows.length) { const r = document.createElement("tr"), td = document.createElement("td"); td.colSpan = headers.length; td.className = "text-secondary"; td.textContent = "No records to show yet."; r.appendChild(td); tbody.appendChild(r); }
        t.appendChild(tbody); wrap.appendChild(t); panel.appendChild(wrap);
    }
    async function updateStatus(path, status, reload = true) {
        const result = await apiRequest(path, { method: "PATCH", body: { status }, csrf: true });
        if (!result.ok) { alert(result.data.error || "Could not update this record."); return; }
        if (reload) location.reload();
    }

    if (user.role === "customer") {
        heading("Your FoodDNA dashboard", "Quick view of your food orders and recommendations.");
        const res = await apiRequest("/api/dashboard/customer");
        if (!res.ok) { message(res.data.error || "Dashboard data is unavailable.", "warning"); return; }
        const s = res.data.summary;
        const cards = document.createElement("div"); cards.className = "row g-3 mb-3";
        [["Orders", s.orders_total], ["Active orders", s.orders_active], ["Items in cart", s.cart_item_count], ["Recommendations saved", s.recommendations_count]].forEach(([label, value]) => {
            const col = document.createElement("div"); col.className = "col-6 col-lg-3";
            const card = document.createElement("div"); card.className = "fd-card p-3 h-100";
            const strong = document.createElement("div"); strong.className = "fs-3 fw-bold"; strong.textContent = value;
            const small = document.createElement("div"); small.className = "small text-secondary"; small.textContent = label;
            card.append(strong, small); col.appendChild(card); cards.appendChild(col);
        }); panel.appendChild(cards);
        panel.append(link("Browse food", "menu.html"), document.createTextNode(" "), link("My orders", "orders.html"), document.createTextNode(" "), link("Food Memory", "notifications.html"));
        heading("Recent orders");
        table(["Order", "Restaurant", "Status", "Total", "Placed"], (s.recent_orders || []).map(o => [
            `#${o.id}`, o.restaurant_name, o.status, `₹${o.total_amount}`, o.placed_at ? new Date(o.placed_at).toLocaleString() : "—"
        ]));
        return;
    }

    if (user.role === "super_admin") {
        heading("Super Admin dashboard", "Review restaurant applications and manage platform accounts.");
        panel.append(link("View all users", "#users"), document.createTextNode(" "), link("Offers", "offers.html"), document.createTextNode(" "), link("Notifications", "notifications.html"));
        const res = await apiRequest("/api/admin/approvals?status=pending");
        if (!res.ok) { message(res.data.error || "Could not load applications.", "danger"); return; }
        heading("Pending restaurant applications");
        const rows = (res.data.approvals || []).map(a => {
            const actions = document.createElement("div"); actions.className = "d-flex gap-1";
            const approve = document.createElement("button"); approve.className = "btn btn-success btn-sm"; approve.textContent = "Approve";
            approve.addEventListener("click", () => updateStatus(`/api/admin/approvals/${a.id}`, "approved"));
            const reject = document.createElement("button"); reject.className = "btn btn-outline-danger btn-sm"; reject.textContent = "Reject";
            reject.addEventListener("click", () => updateStatus(`/api/admin/approvals/${a.id}`, "rejected"));
            actions.append(approve, reject);
            return [a.restaurant_name, a.full_name, a.email, a.created_at ? new Date(a.created_at).toLocaleDateString() : "—", actions];
        });
        table(["Restaurant", "Applicant", "Email", "Applied", "Action"], rows);
        const users = document.createElement("div"); users.id = "users"; users.className = "mt-4"; panel.appendChild(users);
        const btn = link("Load user list", "#users", "btn btn-outline-secondary btn-sm");
        btn.addEventListener("click", async (e) => {
            e.preventDefault(); const r = await apiRequest("/api/admin/users");
            if (!r.ok) { message(r.data.error || "Could not load users.", "danger"); return; }
            const old = document.getElementById("userTable"); if (old) old.remove();
            const container = document.createElement("div"); container.id = "userTable";
            users.appendChild(container);
            const rows = (r.data.users || []).map(u => [`${u.full_name} (#${u.id})`, u.email, u.role, u.account_status, u.is_active ? "Active" : "Inactive"]);
            // Render a table in the dedicated container.
            const t = document.createElement("table"); t.className = "table table-sm"; const tb = document.createElement("tbody");
            const hd = document.createElement("tr"); ["User", "Email", "Role", "Status", "Active"].forEach(v => { const th = document.createElement("th"); th.textContent = v; hd.appendChild(th); }); t.appendChild(hd);
            rows.forEach(arr => { const tr = document.createElement("tr"); arr.forEach(v => { const td = document.createElement("td"); td.textContent = v; tr.appendChild(td); }); tb.appendChild(tr); }); t.appendChild(tb); container.appendChild(t);
        });
        users.appendChild(btn);

        const createTitle = document.createElement("h3"); createTitle.className = "h5 mt-4"; createTitle.textContent = "Create staff or delivery partner account"; users.appendChild(createTitle);
        const createForm = document.createElement("form"); createForm.className = "row g-2";
        const nameInput = document.createElement("input"); nameInput.className = "form-control"; nameInput.placeholder = "Full name"; nameInput.required = true; nameInput.maxLength = 120;
        const emailInput = document.createElement("input"); emailInput.type = "email"; emailInput.className = "form-control"; emailInput.placeholder = "Gmail address (@gmail.com)"; emailInput.required = true;
        const passwordInput = document.createElement("input"); passwordInput.type = "password"; passwordInput.className = "form-control"; passwordInput.placeholder = "Temporary password (10+ characters)"; passwordInput.minLength = 10; passwordInput.required = true;
        const roleSelect = document.createElement("select"); roleSelect.className = "form-select";
        [["staff", "Restaurant Staff"], ["delivery_partner", "Delivery Partner"]].forEach(([value,label]) => { const o=document.createElement("option"); o.value=value; o.textContent=label; roleSelect.appendChild(o); });
        const restaurantSelect = document.createElement("select"); restaurantSelect.className = "form-select";
        const restResult = await apiRequest("/api/admin/restaurants?status=approved");
        if (restResult.ok) (restResult.data.restaurants || []).forEach(r => { const o=document.createElement("option"); o.value=r.id; o.textContent=`${r.name} (#${r.id})`; restaurantSelect.appendChild(o); });
        const submit = document.createElement("button"); submit.type="submit"; submit.className="btn btn-fd"; submit.textContent="Create account";
        function syncRestaurant() { restaurantSelect.hidden = roleSelect.value !== "staff"; restaurantSelect.required = roleSelect.value === "staff"; }
        roleSelect.addEventListener("change", syncRestaurant); syncRestaurant();
        nameInput.addEventListener("input", () => { nameInput.value = nameInput.value.replace(/[^\p{L}\p{M} ]/gu, ""); });
        [[nameInput,"col-md-4"],[emailInput,"col-md-4"],[passwordInput,"col-md-4"],[roleSelect,"col-md-4"],[restaurantSelect,"col-md-5"],[submit,"col-md-3"]].forEach(([el,cls]) => { const col=document.createElement("div"); col.className=cls; col.appendChild(el); createForm.appendChild(col); });
        createForm.addEventListener("submit", async event => { event.preventDefault(); const body={full_name:nameInput.value.trim(),email:emailInput.value.trim(),password:passwordInput.value,role:roleSelect.value}; if (!NAME_RULE.test(body.full_name)) { message("Full name may contain only letters and spaces.","danger"); return; } if (!EMAIL_RULE.test(body.email)) { message("Please enter a valid Gmail address ending in @gmail.com.","danger"); return; } if (!PASSWORD_RULE.test(body.password) || body.password.length < 10) { message("Use at least 10 characters, including uppercase, lowercase, a number and a special character, with no spaces.","danger"); return; } if (roleSelect.value === "staff") body.restaurant_id=Number(restaurantSelect.value);
            const r=await apiRequest("/api/admin/users", {method:"POST",body,csrf:true}); if(!r.ok) message(r.data.error || "Could not create account.","danger"); else { message(`Created ${r.data.user.role} account for ${r.data.user.email}.`,"success"); createForm.reset(); syncRestaurant(); } });
        users.appendChild(createForm);
        return;
    }

    if (user.role === "restaurant_admin" || user.role === "staff") {
        const endpoint = user.role === "staff" ? "/api/staff/dashboard" : "/api/restaurant-admin/dashboard";
        heading(user.role === "staff" ? "Restaurant staff dashboard" : "Restaurant Admin dashboard", "Manage preparation workflow and track incoming orders.");
        panel.append(link("Manage offers", "offers.html"), document.createTextNode(" "), link("Notifications", "notifications.html"));
        const res = await apiRequest(endpoint);
        if (!res.ok) { message(res.data.error || "Could not load restaurant operations.", "warning"); return; }
        const orders = user.role === "staff" ? res.data.orders : (res.data.summary?.recent_orders || []);
        if (user.role === "restaurant_admin") {
            const summary = res.data.summary || {};
            const p = document.createElement("p"); p.className = "mt-3 text-secondary"; p.textContent = `${res.data.restaurant?.name || "Restaurant"}: ${summary.orders_total || 0} orders, ${summary.orders_active || 0} active, ${summary.meals_total || 0} meals.`; panel.appendChild(p);
            panel.append(link("Manage restaurant menu", "restaurant-management.html"));
        }
        heading("Recent orders");
        const rows = (orders || []).map(o => {
            const action = document.createElement("div"); action.className = "d-flex gap-1 flex-wrap";
            const next = { pending: "confirmed", confirmed: "preparing", preparing: "ready_for_pickup" }[o.status];
            if (next) { const b = document.createElement("button"); b.className = "btn btn-primary btn-sm"; b.textContent = next.replaceAll("_", " ");
                const path = user.role === "staff" ? `/api/staff/orders/${o.id}/status` : `/api/restaurant-admin/orders/${o.id}/status`;
                b.addEventListener("click", () => updateStatus(path, next)); action.appendChild(b); }
            return [`#${o.id}`, o.status, `₹${o.total_amount}`, o.item_count, action];
        });
        table(["Order", "Status", "Total", "Items", "Action"], rows);
        return;
    }

    if (user.role === "delivery_partner") {
        heading("Delivery Partner dashboard", "Claim ready orders and update delivery progress.");
        panel.append(link("Notifications", "notifications.html"));
        const res = await apiRequest("/api/delivery/dashboard");
        if (!res.ok) { message(res.data.error || "Could not load delivery tasks.", "warning"); return; }
        const active = res.data.assigned_orders || [];
        heading(`Available orders: ${res.data.available_orders || 0}`);
        const av = await apiRequest("/api/delivery/orders/available");
        const rows = (av.data.orders || []).map(o => {
            const b = document.createElement("button"); b.className = "btn btn-success btn-sm"; b.textContent = "Claim order";
            b.addEventListener("click", async () => { const r = await apiRequest(`/api/delivery/orders/${o.id}/claim`, { method: "POST", csrf: true }); if (!r.ok) alert(r.data.error || "Unable to claim order."); else location.reload(); });
            return [`#${o.id}`, o.restaurant_name, o.status, `₹${o.total_amount}`, b];
        });
        table(["Order", "Restaurant", "Status", "Total", "Action"], rows);
        heading("My active deliveries");
        const activeRows = active.map(o => {
            const action = document.createElement("div");
            const next = { ready_for_pickup: "picked_up", picked_up: "out_for_delivery", out_for_delivery: "delivered" }[o.status];
            if (next) { const b = document.createElement("button"); b.className = "btn btn-primary btn-sm"; b.textContent = next.replaceAll("_", " ");
                b.addEventListener("click", () => updateStatus(`/api/delivery/orders/${o.id}/status`, next)); action.appendChild(b); }
            return [`#${o.id}`, o.restaurant_name, o.status, o.delivery_address, action];
        });
        table(["Order", "Restaurant", "Status", "Address", "Update"], activeRows);
    }
})();
