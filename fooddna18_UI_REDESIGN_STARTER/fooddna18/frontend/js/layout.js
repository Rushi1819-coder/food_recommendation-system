/**
 * Food DNA - Shared Layout & Navigation Engine
 * Automatically renders:
 *  1. Dual-Zone App Shell (Sidebar + Topbar) for logged-in role pages.
 *  2. Public Branded Navigation for public/auth pages.
 */

(async function initLayout() {
    const user = await getCurrentUser();
    const currentPage = window.location.pathname.split("/").pop() || "index.html";

    // SVGs for clean UI icons without heavy external icon libraries
    const ICONS = {
        dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>`,
        profile: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
        dna: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M4 12c0 4.4 3.6 8 8 8s8-3.6 8-8-3.6-8-8-8-8 3.6-8 8z"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg>`,
        recommendations: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        menu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>`,
        cart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>`,
        orders: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
        memory: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
        reverse: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 14.93V17a1 1 0 0 1-2 0v-.07A7 7 0 1 1 19 12a1 1 0 0 1-2 0 5 5 0 1 0-4 4.93z"/></svg>`,
        feedback: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
        offers: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`,
        users: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
        restaurant: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 2h-3a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h3a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/><path d="M6 2v20M6 8a4 4 0 0 0 4-4V2"/></svg>`,
        staff: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>`,
        delivery: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>`,
        logout: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>`,
        bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
        search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
        menuIcon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`
    };

    // 1. Render Dual-Zone App Shell (Sidebar & Topbar)
    const sidebarHolder = document.getElementById("sidebar");
    const topbarHolder = document.getElementById("topbar");

    if (sidebarHolder) {
        renderSidebar(sidebarHolder, user, currentPage, ICONS);
    }

    if (topbarHolder) {
        renderTopbar(topbarHolder, user, ICONS);
    }

    // 2. Render Public Navbar if on a public/auth page with #navbar
    const navbarHolder = document.getElementById("navbar");
    if (navbarHolder && !sidebarHolder) {
        renderPublicNavbar(navbarHolder, user, currentPage);
    }

    // Initialize mobile sidebar toggle
    initMobileDrawer();
})();

function renderSidebar(holder, user, currentPage, ICONS) {
    const role = user ? user.role : "customer";

    let links = [];

    if (role === "customer") {
        links = [
            { label: "Dashboard", href: "dashboard.html", icon: ICONS.dashboard },
            { label: "My Profile", href: "profile.html", icon: ICONS.profile },
            { label: "Food DNA", href: "preferences.html", icon: ICONS.dna },
            { label: "Recommendations", href: "recommendations.html", icon: ICONS.recommendations },
            { label: "Menu", href: "menu.html", icon: ICONS.menu },
            { label: "Cart", href: "cart.html", icon: ICONS.cart },
            { label: "My Orders", href: "orders.html", icon: ICONS.orders },
            { label: "Food Memory", href: "food-memory.html", icon: ICONS.memory },
            { label: "Reverse Ordering", href: "reverse-ordering.html", icon: ICONS.reverse },
            { label: "Feedback", href: "feedback.html", icon: ICONS.feedback },
            { label: "Offers", href: "offers.html", icon: ICONS.offers },
        ];
    } else if (role === "restaurant_admin") {
        links = [
            { label: "Dashboard", href: "restaurant-management.html", icon: ICONS.dashboard },
            { label: "Menu Management", href: "restaurant-management.html?tab=menu", icon: ICONS.menu },
            { label: "Orders Queue", href: "restaurant-management.html?tab=orders", icon: ICONS.orders },
            { label: "Offers", href: "offers.html", icon: ICONS.offers },
            { label: "Notifications", href: "notifications.html", icon: ICONS.bell },
        ];
    } else if (role === "staff") {
        links = [
            { label: "Kitchen Dashboard", href: "staff-dashboard.html", icon: ICONS.dashboard },
            { label: "Live Orders", href: "staff-dashboard.html?tab=orders", icon: ICONS.orders },
            { label: "Notifications", href: "notifications.html", icon: ICONS.bell },
        ];
    } else if (role === "delivery_partner") {
        links = [
            { label: "Delivery Dashboard", href: "delivery-dashboard.html", icon: ICONS.delivery },
            { label: "Available Orders", href: "delivery-dashboard.html?tab=available", icon: ICONS.orders },
            { label: "My Deliveries", href: "delivery-dashboard.html?tab=assigned", icon: ICONS.delivery },
            { label: "Notifications", href: "notifications.html", icon: ICONS.bell },
        ];
    } else if (role === "super_admin") {
        links = [
            { label: "System Overview", href: "admin-dashboard.html", icon: ICONS.dashboard },
            { label: "User Management", href: "admin-users.html", icon: ICONS.users },
            { label: "Approvals", href: "admin-dashboard.html?tab=approvals", icon: ICONS.restaurant },
            { label: "Restaurants", href: "admin-dashboard.html?tab=restaurants", icon: ICONS.restaurant },
            { label: "Notifications", href: "notifications.html", icon: ICONS.bell },
        ];
    }

    const navItemsHtml = links.map(link => {
        const isActive = currentPage === link.href.split("?")[0];
        return `
            <a href="${link.href}" class="fd-sidebar-link ${isActive ? 'active' : ''}">
                ${link.icon}
                <span>${link.label}</span>
            </a>
        `;
    }).join("");

    holder.innerHTML = `
        <aside class="fd-sidebar" id="fdSidebar">
            <div class="fd-sidebar-brand">
                <div class="fd-brand-icon">
                    <span>🥗</span>
                </div>
                <div>
                    <div class="fd-brand-text">Food DNA</div>
                    <div class="fd-brand-tagline">Smart Nutrition</div>
                </div>
            </div>
            <div class="fd-sidebar-nav">
                <div class="fd-nav-label">Main Navigation</div>
                ${navItemsHtml}
            </div>
            <div class="fd-sidebar-footer">
                ${user ? `
                    <button type="button" class="fd-sidebar-link w-100 text-danger border-0 bg-transparent text-start" id="sidebarLogout">
                        ${ICONS.logout}
                        <span>Logout</span>
                    </button>
                ` : `
                    <a href="login.html" class="btn btn-fd w-100 btn-sm">Log In</a>
                `}
            </div>
        </aside>
        <div class="fd-drawer-backdrop" id="fdBackdrop"></div>
    `;

    const logoutBtn = document.getElementById("sidebarLogout");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", logout);
    }
}

async function renderTopbar(holder, user, ICONS) {
    let cartCount = 0;
    let unreadNotifications = 0;

    if (user && user.role === "customer") {
        try {
            const cartRes = await apiRequest("/api/cart");
            if (cartRes.ok && cartRes.data.cart && cartRes.data.cart.items) {
                cartCount = cartRes.data.cart.items.reduce((sum, item) => sum + item.quantity, 0);
            }
        } catch (e) {}
    }

    if (user) {
        try {
            const notifRes = await apiRequest("/api/notifications");
            if (notifRes.ok && notifRes.data.unread_count) {
                unreadNotifications = notifRes.data.unread_count;
            }
        } catch (e) {}
    }

    const userName = user ? user.full_name : "Guest";
    const userInitials = user ? user.full_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) : "G";
    const userRole = user ? user.role.replace("_", " ") : "Visitor";

    holder.innerHTML = `
        <header class="fd-topbar">
            <div class="d-flex align-items-center gap-2">
                <button type="button" class="fd-menu-toggle" id="menuToggle" aria-label="Toggle menu">
                    ${ICONS.menuIcon}
                </button>
                <div class="fd-search-bar">
                    <span class="fd-search-icon">${ICONS.search}</span>
                    <input type="text" id="topbarSearch" placeholder="Search for meals, restaurants, cuisines..." autocomplete="off">
                </div>
            </div>
            <div class="fd-topbar-actions">
                ${user && user.role === "customer" ? `
                    <a href="cart.html" class="fd-icon-btn" title="View Shopping Cart">
                        ${ICONS.cart}
                        ${cartCount > 0 ? `<span class="fd-badge-count" id="cartBadgeCount">${cartCount}</span>` : ''}
                    </a>
                ` : ''}
                ${user ? `
                    <a href="notifications.html" class="fd-icon-btn" title="Notifications">
                        ${ICONS.bell}
                        ${unreadNotifications > 0 ? `<span class="fd-badge-count">${unreadNotifications}</span>` : ''}
                    </a>
                    <a href="${user.role === 'customer' ? 'profile.html' : '#'}" class="fd-user-chip" title="User Profile">
                        <div class="fd-avatar">${userInitials}</div>
                        <div class="d-none d-md-block text-start">
                            <div class="fd-user-name">${userName}</div>
                            <div style="font-size: 0.72rem; color: var(--fd-text-light); text-transform: capitalize;">${userRole}</div>
                        </div>
                    </a>
                ` : `
                    <a href="login.html" class="btn btn-fd-outline btn-sm">Log in</a>
                    <a href="register.html" class="btn btn-fd btn-sm">Register</a>
                `}
            </div>
        </header>
    `;

    // Topbar search event
    const searchInput = document.getElementById("topbarSearch");
    if (searchInput) {
        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && searchInput.value.trim()) {
                const q = encodeURIComponent(searchInput.value.trim());
                window.location.href = `menu.html?q=${q}`;
            }
        });
    }
}

function renderPublicNavbar(holder, user, currentPage) {
    const isHome = currentPage === "index.html";
    const isBrowse = ["restaurants.html", "menu.html", "meal.html"].includes(currentPage);
    const isOffers = currentPage === "offers.html";

    holder.innerHTML = `
        <nav class="fd-public-navbar">
            <div class="container d-flex align-items-center justify-content-between">
                <a href="index.html" class="d-flex align-items-center gap-2 text-decoration-none">
                    <div class="fd-brand-icon" style="width: 34px; height: 34px; font-size: 1rem;">🥗</div>
                    <span class="fd-brand-text" style="font-size: 1.25rem;">Food DNA</span>
                </a>
                <div class="d-none d-md-flex align-items-center gap-2">
                    <a href="index.html" class="nav-link ${isHome ? 'active' : ''}">Home</a>
                    <a href="restaurants.html" class="nav-link ${currentPage === 'restaurants.html' ? 'active' : ''}">Restaurants</a>
                    <a href="menu.html" class="nav-link ${currentPage === 'menu.html' ? 'active' : ''}">Food Menu</a>
                    <a href="offers.html" class="nav-link ${isOffers ? 'active' : ''}">Offers</a>
                </div>
                <div class="d-flex align-items-center gap-2">
                    ${user ? `
                        <a href="dashboard.html" class="btn btn-fd btn-sm">My Dashboard</a>
                    ` : `
                        <a href="login.html" class="btn btn-fd-outline btn-sm">Log in</a>
                        <a href="register.html" class="btn btn-fd btn-sm">Sign Up</a>
                    `}
                </div>
            </div>
        </nav>
    `;
}

function initMobileDrawer() {
    const toggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("fdSidebar");
    const backdrop = document.getElementById("fdBackdrop");

    if (!toggle || !sidebar) return;

    toggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        if (backdrop) backdrop.classList.toggle("show");
    });

    if (backdrop) {
        backdrop.addEventListener("click", () => {
            sidebar.classList.remove("open");
            backdrop.classList.remove("show");
        });
    }
}
