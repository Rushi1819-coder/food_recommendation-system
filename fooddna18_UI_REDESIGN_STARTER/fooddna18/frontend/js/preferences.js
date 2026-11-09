/*
 * Food DNA - preferences page (Phase 5).
 *
 * Needs js/api.js and js/browse.js (for el, fillSelect, showLoading,
 * showError, SPICE_ORDER). Saved values and the dropdown choices both come
 * from the Flask API; nothing is hard-coded. Server text is inserted with
 * textContent only.
 */

/* name -> { label, max length (same as the database column), options key } */
const PREFERENCE_FIELDS = {
    cuisine: { label: "Cuisine", max: 80, options: "cuisines" },
    meal_type: { label: "Meal type", max: 50, options: "meal_types" },
    taste: { label: "Taste", max: 50, options: "tastes" },
    spice_level: { label: "Spice level", max: 30, options: "spice_levels" },
    portion_size: { label: "Portion size", max: 30, options: "portion_sizes" },
    food_type: { label: "Food type", max: 30, options: "food_types" },
    dietary_preference: { label: "Dietary preference", max: 80, options: "dietary_preferences" }
};

/** Select the option equal to `value` (ignoring case); add it if missing. */
function setSelectValue(select, value) {
    if (!value) {
        select.value = "";
        return;
    }
    const wanted = String(value).toLowerCase();
    const match = Array.from(select.options).find(
        (option) => option.value.toLowerCase() === wanted
    );
    if (match) {
        select.value = match.value;
        return;
    }
    // A saved value that no dish currently offers must still be shown.
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value);
    select.appendChild(option);
    select.value = String(value);
}

async function initPreferencesPage() {
    const form = document.getElementById("preferencesForm");
    const message = document.getElementById("pageMessage");
    const savedAt = document.getElementById("savedAt");
    const afterSave = document.getElementById("afterSave");
    const saveButton = document.getElementById("saveButton");
    const clearButton = document.getElementById("clearButton");

    const user = await requireLogin();
    if (!user) {
        return;
    }
    if (user.role !== "customer") {
        showMessage(
            message,
            "info",
            "Food preferences are available to customer accounts only."
        );
        return;
    }

    function clearFieldErrors() {
        Array.from(form.elements).forEach((control) => {
            control.classList.remove("is-invalid");
        });
        document.querySelectorAll(".invalid-feedback").forEach((box) => {
            box.textContent = "";
        });
    }

    function showFieldError(name, text) {
        const control = form.elements[name];
        const box = document.getElementById(`err-${name}`);
        if (control) {
            control.classList.add("is-invalid");
        }
        if (box) {
            box.textContent = text;
        }
    }

    /** Same rules as the backend. Returns { values, errors }. */
    function readForm() {
        const values = {};
        const errors = {};
        Object.entries(PREFERENCE_FIELDS).forEach(([name, field]) => {
            const text = form.elements[name].value.trim();
            if (text === "") {
                values[name] = null;
            } else if (text.length > field.max) {
                errors[name] = `${field.label} must be at most ${field.max} characters.`;
            } else if (!PREFERENCE_TEXT_RULE.test(text)) {
                errors[name] = `${field.label} contains characters that are not allowed.`;
            } else {
                values[name] = text;
            }
        });

        const budget = form.elements.budget.value.trim();
        if (budget === "") {
            values.budget = null;
        } else if (!BUDGET_RULE.test(budget)) {
            errors.budget = "Budget must be a positive number with at most 2 decimals.";
        } else if (Number(budget) <= 0) {
            errors.budget = "Budget must be greater than 0.";
        } else {
            values.budget = budget;
        }
        return { values, errors };
    }

    function fillForm(preferences) {
        Object.keys(PREFERENCE_FIELDS).forEach((name) => {
            setSelectValue(form.elements[name], preferences ? preferences[name] : "");
        });
        form.elements.budget.value =
            preferences && preferences.budget ? preferences.budget : "";

        if (preferences && preferences.updated_at) {
            const when = new Date(preferences.updated_at);
            savedAt.textContent = Number.isNaN(when.getTime())
                ? ""
                : `Last saved: ${when.toLocaleString()}`;
        } else {
            savedAt.textContent = "You have not saved any preferences yet.";
        }
    }

    async function load() {
        form.hidden = true;
        afterSave.hidden = true;
        showLoading(message, "Loading your preferences...");

        const [saved, filters] = await Promise.all([
            fetchPreferences(),
            fetchMealFilters()
        ]);

        if (!saved.ok) {
            showError(
                message,
                saved.data.error || "Could not load your preferences.",
                load
            );
            return;
        }

        if (filters.ok) {
            const options = filters.data.filters;
            Object.entries(PREFERENCE_FIELDS).forEach(([name, field]) => {
                let list = options[field.options] || [];
                if (name === "spice_level") {
                    list = [...list].sort((a, b) => {
                        const ia = SPICE_ORDER.indexOf(String(a).toLowerCase());
                        const ib = SPICE_ORDER.indexOf(String(b).toLowerCase());
                        return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
                    });
                }
                fillSelect(form.elements[name], list);
            });
            clearMessage(message);
        } else {
            showMessage(
                message,
                "warning",
                "The list of available choices could not be loaded, so the " +
                "dropdowns may be incomplete. Your saved values are still shown."
            );
        }

        fillForm(saved.data.preferences);
        form.hidden = false;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearFieldErrors();
        afterSave.hidden = true;

        const { values, errors } = readForm();
        if (Object.keys(errors).length) {
            Object.entries(errors).forEach(([name, text]) => showFieldError(name, text));
            showMessage(message, "warning", "Please correct the highlighted fields.");
            return;
        }

        setBusy(saveButton, true, "Saving...");
        const response = await savePreferences(values);
        setBusy(saveButton, false);

        if (!response.ok) {
            const fieldErrors = response.data.errors || {};
            Object.entries(fieldErrors).forEach(([name, text]) => showFieldError(name, text));
            showMessage(
                message,
                response.status === 400 ? "warning" : "danger",
                response.data.error || "Could not save your preferences."
            );
            return;
        }

        fillForm(response.data.preferences);
        showMessage(message, "success", "Your preferences were saved.");
        afterSave.hidden = false;
    });

    clearButton.addEventListener("click", () => {
        clearFieldErrors();
        fillForm(null);
        savedAt.textContent = "Fields cleared. Press Save preferences to store this.";
        clearMessage(message);
    });

    return load();
}
