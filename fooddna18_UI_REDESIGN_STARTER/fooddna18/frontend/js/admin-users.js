/**
 * Food DNA - Super Admin User Management (Screen 21)
 * Handles:
 *  - Filtering users by role
 *  - Suspending or activating user accounts
 *  - Creating operator accounts (Staff or Delivery Partner)
 */

(async function () {
    const messageBox = document.getElementById("pageMessage");
    const userTableBody = document.getElementById("userTableBody");
    const roleFilter = document.getElementById("roleFilter");
    const createOperatorForm = document.getElementById("createOperatorForm");
    const operatorRoleSelect = document.getElementById("operatorRole");
    const staffFields = document.getElementById("staffFields");
    const deliveryFields = document.getElementById("deliveryFields");
    const restaurantSelect = document.getElementById("operatorRestaurant");

    const user = await getCurrentUser();
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    if (user.role !== "super_admin") {
        if (messageBox) showMessage(messageBox, "warning", "Only Super Administrators have access to user management.");
        return;
    }

    // Role-dependent fields toggle
    if (operatorRoleSelect) {
        operatorRoleSelect.addEventListener("change", () => {
            const role = operatorRoleSelect.value;
            if (staffFields) staffFields.hidden = role !== "staff";
            if (deliveryFields) deliveryFields.hidden = role !== "delivery_partner";
        });
    }

    // Load Approved Restaurants into operator form
    async function loadRestaurants() {
        if (!restaurantSelect) return;
        try {
            const res = await apiRequest("/api/admin/restaurants?status=approved");
            if (res.ok && res.data.restaurants) {
                restaurantSelect.replaceChildren();
                const defaultOpt = document.createElement("option");
                defaultOpt.value = "";
                defaultOpt.textContent = "Select Approved Restaurant";
                defaultOpt.disabled = true;
                defaultOpt.selected = true;
                restaurantSelect.appendChild(defaultOpt);

                res.data.restaurants.forEach(r => {
                    const opt = document.createElement("option");
                    opt.value = r.id;
                    opt.textContent = `${r.name} (#${r.id})`;
                    restaurantSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Error loading restaurants:", e);
        }
    }

    async function loadUsers() {
        if (!userTableBody) return;
        const role = roleFilter ? roleFilter.value : "";
        const url = role ? `/api/admin/users?role=${encodeURIComponent(role)}` : "/api/admin/users";

        try {
            const res = await apiRequest(url);
            if (!res.ok) {
                if (messageBox) showMessage(messageBox, "danger", res.data.error || "Could not load users.");
                return;
            }

            const users = res.data.users || [];
            userTableBody.replaceChildren();

            if (users.length === 0) {
                userTableBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-secondary">No users found for this role filter.</td></tr>`;
                return;
            }

            users.forEach(u => {
                const tr = document.createElement("tr");
                const isSelf = u.id === user.id;

                tr.innerHTML = `
                    <td>
                        <div class="fw-bold">${escapeHtml(u.full_name || 'User')} ${isSelf ? '<span class="badge bg-secondary ms-1">You</span>' : ''}</div>
                        <div class="small text-secondary">${escapeHtml(u.email || '')}</div>
                    </td>
                    <td><span class="fd-badge fd-badge-${getRoleBadgeClass(u.role)}">${formatRole(u.role)}</span></td>
                    <td><span class="fd-badge ${u.account_status === 'active' ? 'fd-badge-success' : 'fd-badge-danger'}">${(u.account_status || 'active').toUpperCase()}</span></td>
                    <td class="small text-secondary">${u.approval_status || 'N/A'}</td>
                    <td class="text-end action-cell"></td>
                `;

                const actionCell = tr.querySelector(".action-cell");

                if (!isSelf) {
                    const toggleBtn = document.createElement("button");
                    toggleBtn.type = "button";
                    const isSuspended = u.account_status === "suspended";
                    toggleBtn.className = `btn btn-sm ${isSuspended ? 'btn-fd' : 'btn-outline-danger'}`;
                    toggleBtn.textContent = isSuspended ? "Reactivate" : "Suspend";
                    toggleBtn.addEventListener("click", async () => {
                        toggleBtn.disabled = true;
                        const newStatus = isSuspended ? "active" : "suspended";
                        const patchRes = await apiRequest(`/api/admin/users/${u.id}/status`, {
                            method: "PATCH",
                            body: { account_status: newStatus },
                            csrf: true
                        });
                        if (!patchRes.ok) {
                            if (messageBox) showMessage(messageBox, "danger", patchRes.data.error || "Failed to update status.");
                            toggleBtn.disabled = false;
                        } else {
                            if (messageBox) showMessage(messageBox, "success", `User ${u.full_name} is now ${newStatus}.`);
                            loadUsers();
                        }
                    });
                    actionCell.appendChild(toggleBtn);
                } else {
                    actionCell.innerHTML = `<span class="small text-secondary">—</span>`;
                }

                userTableBody.appendChild(tr);
            });
        } catch (e) {
            console.error("Error loading users:", e);
        }
    }

    if (roleFilter) {
        roleFilter.addEventListener("change", loadUsers);
    }

    if (createOperatorForm) {
        createOperatorForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = createOperatorForm.querySelector("button[type='submit']");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Creating Account...";
            }

            const role = operatorRoleSelect.value;
            const body = {
                role,
                full_name: document.getElementById("operatorName").value.trim(),
                email: document.getElementById("operatorEmail").value.trim().toLowerCase(),
                password: document.getElementById("operatorPassword").value
            };

            if (role === "staff") {
                body.restaurant_id = Number(document.getElementById("operatorRestaurant").value);
                body.designation = document.getElementById("operatorDesignation").value.trim() || "Kitchen Staff";
            } else if (role === "delivery_partner") {
                body.phone = document.getElementById("operatorPhone").value.trim();
            }

            const res = await apiRequest("/api/admin/users", {
                method: "POST",
                body,
                csrf: true
            });

            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Create Account";
            }

            if (!res.ok) {
                if (messageBox) showMessage(messageBox, "danger", res.data.error || "Could not create operator account.");
            } else {
                if (messageBox) showMessage(messageBox, "success", `Operator account for ${body.full_name} created successfully!`);
                createOperatorForm.reset();
                if (staffFields) staffFields.hidden = false;
                if (deliveryFields) deliveryFields.hidden = true;
                loadUsers();
            }
        });
    }

    function getRoleBadgeClass(role) {
        switch (role) {
            case "super_admin": return "danger";
            case "restaurant_admin": return "primary";
            case "staff": return "warning";
            case "delivery_partner": return "info";
            default: return "neutral";
        }
    }

    function formatRole(role) {
        if (!role) return "User";
        return role.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    await Promise.all([loadRestaurants(), loadUsers()]);
})();
