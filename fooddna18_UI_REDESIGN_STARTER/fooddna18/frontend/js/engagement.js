/* Phase 10: Offers, Notifications and Feedback. All untrusted content uses textContent. */
(async function () {
    const pageMessage = document.getElementById("pageMessage");
    const offerList = document.getElementById("offerList");
    const notificationList = document.getElementById("notificationList");
    const feedbackForm = document.getElementById("feedbackForm");
    const offerForm = document.getElementById("offerForm");
    const user = await getCurrentUser();

    function message(text, kind = "info") {
        if (!pageMessage) return;
        showMessage(pageMessage, kind, text);
    }

    if (offerList) {
        if (user && user.role === "restaurant_admin") {
            document.getElementById("adminOfferForm").hidden = false;
        }
        const endpoint = user && user.role === "restaurant_admin" ? "/api/restaurant-admin/offers" : "/api/offers";
        const res = await apiRequest(endpoint);
        if (!res.ok) { message(res.data.error || "Offers could not be loaded.", "warning"); return; }
        offerList.replaceChildren();
        (res.data.offers || []).forEach(offer => {
            const col = document.createElement("div"); col.className = "col-md-6 col-xl-4";
            const card = document.createElement("article"); card.className = "fd-card p-3 h-100";
            const title = document.createElement("h2"); title.className = "h5"; title.textContent = offer.title;
            const badge = document.createElement("span"); badge.className = "badge text-bg-success"; badge.textContent = `${offer.discount_percent}% off`;
            const restaurant = document.createElement("div"); restaurant.className = "small text-secondary mt-2"; restaurant.textContent = offer.restaurant_name || "Restaurant";
            const description = document.createElement("p"); description.className = "mt-2"; description.textContent = offer.description || "Enjoy this restaurant offer.";
            const dates = document.createElement("div"); dates.className = "small text-secondary"; dates.textContent = `${offer.start_date} to ${offer.end_date}`;
            card.append(title, badge, restaurant, description, dates);
            if (user && user.role === "restaurant_admin" && !offer.is_active) {
                const b = document.createElement("button"); b.className = "btn btn-outline-primary btn-sm mt-2"; b.textContent = "Activate";
                b.addEventListener("click", async () => { const r = await apiRequest(`/api/restaurant-admin/offers/${offer.id}`, { method: "PATCH", body: { is_active: true }, csrf: true }); if (!r.ok) message(r.data.error || "Could not activate offer.", "danger"); else location.reload(); }); card.appendChild(b);
            }
            col.appendChild(card); offerList.appendChild(col);
        });
        if (!(res.data.offers || []).length) message("No current offers are available.");
        if (offerForm) offerForm.addEventListener("submit", async event => {
            event.preventDefault();
            const body = { title: document.getElementById("offerTitle").value.trim(),
                discount_percent: Number(document.getElementById("offerDiscount").value),
                description: document.getElementById("offerDescription").value,
                start_date: document.getElementById("offerStart").value,
                end_date: document.getElementById("offerEnd").value };
            const r = await apiRequest("/api/restaurant-admin/offers", { method: "POST", body, csrf: true });
            if (!r.ok) message(r.data.error || "Could not create offer.", "danger"); else { message("Offer created successfully.", "success"); location.reload(); }
        });
    }

    if (notificationList) {
        if (!user) { window.location.href = "login.html"; return; }
        const res = await apiRequest("/api/notifications");
        if (!res.ok) { message(res.data.error || "Notifications could not be loaded.", "warning"); return; }
        notificationList.replaceChildren();
        (res.data.notifications || []).forEach(n => {
            const item = document.createElement("div"); item.className = "list-group-item d-flex justify-content-between gap-3";
            const body = document.createElement("div");
            const title = document.createElement("div"); title.className = "fw-semibold"; title.textContent = n.title + (n.is_read ? "" : " • New");
            const text = document.createElement("div"); text.className = "mt-1"; text.textContent = n.message;
            const date = document.createElement("div"); date.className = "small text-secondary mt-1"; date.textContent = n.created_at ? new Date(n.created_at).toLocaleString() : "";
            body.append(title, text, date); item.appendChild(body);
            if (!n.is_read) { const button = document.createElement("button"); button.className = "btn btn-outline-secondary btn-sm align-self-start"; button.textContent = "Mark read";
                button.addEventListener("click", async () => { const r = await apiRequest(`/api/notifications/${n.id}/read`, { method: "PATCH", csrf: true }); if (!r.ok) message(r.data.error || "Unable to mark as read.", "danger"); else location.reload(); }); item.appendChild(button); }
            notificationList.appendChild(item);
        });
        if (!(res.data.notifications || []).length) message("You're all caught up. No notifications yet.");
        const readAll = document.getElementById("readAll");
        if (readAll) readAll.addEventListener("click", async () => { const r = await apiRequest("/api/notifications/read-all", { method: "POST", csrf: true }); if (!r.ok) message(r.data.error || "Unable to update notifications.", "danger"); else location.reload(); });
    }

    if (feedbackForm) {
        if (!user) { window.location.href = "login.html"; return; }
        const list = document.getElementById("feedbackList");
        const res = await apiRequest("/api/feedback");
        if (res.ok) {
            (res.data.feedback || []).forEach(f => {
                const p = document.createElement("p"); p.className = "border-bottom py-2";
                p.textContent = `Meal #${f.food_id} · ${f.rating}/5 · ${f.comment || "No comment"}`; list.appendChild(p);
            });
            if (!(res.data.feedback || []).length) { const p = document.createElement("p"); p.className = "text-secondary small"; p.textContent = "You have not submitted feedback yet."; list.appendChild(p); }
        }
        feedbackForm.addEventListener("submit", async event => {
            event.preventDefault();
            const body = { order_id: Number(document.getElementById("feedbackOrderId").value),
                meal_id: Number(document.getElementById("feedbackMealId").value),
                rating: Number(document.getElementById("feedbackRating").value),
                comment: document.getElementById("feedbackComment").value.trim() };
            const r = await apiRequest("/api/feedback", { method: "POST", body, csrf: true });
            if (!r.ok) message(r.data.error || "Feedback could not be submitted.", "danger");
            else { message("Thank you for your feedback!", "success"); feedbackForm.reset(); }
        });
    }
})();
