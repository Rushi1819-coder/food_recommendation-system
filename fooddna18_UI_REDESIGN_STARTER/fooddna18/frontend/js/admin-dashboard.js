/**
 * Food DNA - Platform Super Admin Dashboard (Screen 20)
 * Handles:
 *  - Platform KPIs (Total Approvals, Pending Approvals, Total Restaurants, System Users)
 *  - Restaurant Admin Application Approvals Queue (Approve / Reject with remarks)
 *  - Restaurants Directory overview
 */

(async function () {
    const messageBox = document.getElementById("pageMessage");
    const approvalsList = document.getElementById("approvalsList");
    const restaurantsList = document.getElementById("restaurantsList");

    // KPI elements
    const kpiPendingApprovals = document.getElementById("kpiPendingApprovals");
    const kpiTotalRestaurants = document.getElementById("kpiTotalRestaurants");
    const kpiTotalUsers = document.getElementById("kpiTotalUsers");

    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    if (user.role !== "super_admin") {
        if (messageBox) showMessage(messageBox, "warning", "Only Super Administrators have access to this control panel.");
        return;
    }

    // Tabs
    const tabBtns = document.querySelectorAll("[data-admin-tab]");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const target = btn.getAttribute("data-admin-tab");
            document.getElementById("tabContentApprovals").hidden = target !== "approvals";
            document.getElementById("tabContentRestaurants").hidden = target !== "restaurants";
        });
    });

    async function loadAdminOverview() {
        try {
            // Load Approvals
            const appRes = await apiRequest("/api/admin/approvals?status=all");
            let approvals = [];
            if (appRes.ok) {
                approvals = appRes.data.approvals || [];
                const pendingCount = approvals.filter(a => a.status === "pending").length;
                if (kpiPendingApprovals) kpiPendingApprovals.textContent = pendingCount;
                renderApprovals(approvals);
            }

            // Load Restaurants
            const restRes = await apiRequest("/api/admin/restaurants?status=all");
            if (restRes.ok) {
                const rests = restRes.data.restaurants || [];
                if (kpiTotalRestaurants) kpiTotalRestaurants.textContent = rests.length;
                renderRestaurants(rests);
            }

            // Load Users Count
            const usersRes = await apiRequest("/api/admin/users");
            if (usersRes.ok) {
                const users = usersRes.data.users || [];
                if (kpiTotalUsers) kpiTotalUsers.textContent = users.length;
            }
        } catch (e) {
            console.error("Error loading admin dashboard:", e);
        }
    }

    function renderApprovals(approvals) {
        if (!approvalsList) return;
        approvalsList.replaceChildren();

        if (approvals.length === 0) {
            approvalsList.innerHTML = `<div class="p-4 text-center text-secondary">No restaurant admin applications found.</div>`;
            return;
        }

        const table = document.createElement("table");
        table.className = "table table-hover align-middle fd-table mb-0";
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Applicant</th>
                    <th>Restaurant</th>
                    <th>Type</th>
                    <th>Submitted</th>
                    <th>Status</th>
                    <th class="text-end">Action</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector("tbody");

        approvals.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div class="fw-bold">${escapeHtml(item.full_name || 'Applicant')}</div>
                    <div class="small text-secondary">${escapeHtml(item.email || '')}</div>
                </td>
                <td class="fw-semibold">${escapeHtml(item.restaurant_name || `Restaurant #${item.restaurant_id || ''}`)}</td>
                <td><span class="fd-badge fd-badge-neutral">${escapeHtml(item.approval_type)}</span></td>
                <td class="small text-secondary">${item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</td>
                <td><span class="fd-badge fd-badge-${getStatusBadgeClass(item.status)}">${item.status.toUpperCase()}</span></td>
                <td class="text-end actions-cell"></td>
            `;

            const actionsCell = tr.querySelector(".actions-cell");
            if (item.status === "pending") {
                const approveBtn = document.createElement("button");
                approveBtn.className = "btn btn-sm btn-fd me-2";
                approveBtn.textContent = "Approve";
                approveBtn.addEventListener("click", () => handleReview(item.id, "approved"));

                const rejectBtn = document.createElement("button");
                rejectBtn.className = "btn btn-sm btn-outline-danger";
                rejectBtn.textContent = "Reject";
                rejectBtn.addEventListener("click", () => handleReview(item.id, "rejected"));

                actionsCell.append(approveBtn, rejectBtn);
            } else {
                actionsCell.innerHTML = `<span class="small text-secondary">Reviewed</span>`;
            }

            tbody.appendChild(tr);
        });

        approvalsList.appendChild(table);
    }

    async function handleReview(approvalId, status) {
        const remarks = prompt(`Enter optional remarks for ${status.toUpperCase()}:`, "");
        if (remarks === null) return; // User cancelled prompt

        const res = await apiRequest(`/api/admin/approvals/${approvalId}`, {
            method: "PATCH",
            body: { status, remarks: remarks || "" },
            csrf: true
        });

        if (!res.ok) {
            if (messageBox) showMessage(messageBox, "danger", res.data.error || "Review failed.");
        } else {
            if (messageBox) showMessage(messageBox, "success", `Application #${approvalId} has been ${status}.`);
            loadAdminOverview();
        }
    }

    function renderRestaurants(restaurants) {
        if (!restaurantsList) return;
        restaurantsList.replaceChildren();

        if (restaurants.length === 0) {
            restaurantsList.innerHTML = `<div class="p-4 text-center text-secondary">No restaurants registered on the platform.</div>`;
            return;
        }

        const table = document.createElement("table");
        table.className = "table table-hover align-middle fd-table mb-0";
        table.innerHTML = `
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Restaurant Name</th>
                    <th>Address</th>
                    <th>Contact Email</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector("tbody");

        restaurants.forEach(rest => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>#${rest.id}</td>
                <td class="fw-bold">${escapeHtml(rest.name)}</td>
                <td class="small text-secondary">${escapeHtml(rest.address || 'N/A')}</td>
                <td class="small text-secondary">${escapeHtml(rest.email || 'N/A')}</td>
                <td><span class="fd-badge fd-badge-${getStatusBadgeClass(rest.status)}">${(rest.status || 'unknown').toUpperCase()}</span></td>
            `;
            tbody.appendChild(tr);
        });

        restaurantsList.appendChild(table);
    }

    function getStatusBadgeClass(status) {
        switch (status) {
            case "approved": return "success";
            case "pending": return "warning";
            case "rejected": return "danger";
            default: return "neutral";
        }
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    await loadAdminOverview();
})();
