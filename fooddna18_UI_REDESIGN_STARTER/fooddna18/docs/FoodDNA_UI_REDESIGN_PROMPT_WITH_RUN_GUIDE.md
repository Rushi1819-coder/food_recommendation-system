# FoodDNA — Complete UI Redesign and Integration Prompt for Antigravity

## Objective

Redesign the **existing FoodDNA project** to match the attached FoodDNA reference image: an elegant, premium food-ordering and personalized meal recommendation application. The reference image is a visual guide for the styling and the 21 screen types shown in it. **Do not use the whole reference collage as a webpage background or insert the collage as an image.** Build real, responsive HTML pages and UI components.

Work directly in the currently opened FoodDNA project workspace. Inspect the actual files before editing. Implement the redesign—not just a plan, mock-up, or list of suggestions.

## 1. Visual direction

Follow the reference image closely:

- **Brand:** Food DNA / FoodDNA, with a tasteful food-and-botanical identity.
- **Palette:** deep burgundy/plum for primary actions and navigation, blush pink, warm cream/off-white backgrounds, white cards, muted rose borders, and readable dark text.
- **Mood:** elegant, warm, polished, food-focused, welcoming, and premium—not a generic Bootstrap template.
- **Typography:** elegant serif or compatible display styling for major headings; clear, accessible sans-serif body text. Use fonts already available locally or safe web-font fallbacks. Do not make the application unusable if an external font fails.
- **Decorative elements:** subtle botanical/leaf motifs and soft organic shapes where appropriate. Keep decoration behind content and do not harm contrast or usability.
- **Food imagery:** prominent, appetizing food photos on hero areas and meal cards. First inspect existing local project assets and reuse them. If suitable images do not exist, add appropriately licensed/available local assets or graceful image placeholders. Avoid broken remote image links and do not create fake order/customer data solely for screenshots.
- **Layout:** generous spacing, consistent rounded corners, restrained shadows, refined buttons, badges, tabs, form controls, and card grids.
- **Responsive:** usable at desktop, tablet, and mobile widths. Sidebars should collapse into a usable mobile navigation pattern; tables and cards must not overflow the viewport.
- **Accessibility:** semantic HTML, visible focus states, useful alt text, labels for all fields, keyboard operability, adequate contrast, and accessible dialogs/validation feedback.

Use the reference’s layout cues: a branded login/registration experience; customer dashboard with personalized recommendations; customer menu and meal detail cards; cart and checkout flow; order tracking/history; Food Memory, feedback, reverse-food-ordering and preferences screens; profile; and distinct dashboards for restaurant administration, restaurant staff/chef, delivery partners, and Super Admin.

## 2. Non-negotiable project safety rules

1. Preserve all working functionality from the existing project and its earlier phases. This is a UI redesign and integration task, not permission to rebuild the app from scratch.
2. Keep the existing Flask backend, SQLAlchemy models, database schema, migrations, REST API URLs, request/response shapes, session handling, CSRF protection, role-based access controls, and business rules unless a real defect is found and documented.
3. Do not blindly replace `backend/app/__init__.py`, the Flask application factory, route blueprints, `api.js`, or the shared layout code. Inspect their current contents and make small, compatible changes.
4. Do not delete, reset, or migrate the user's real `fooddna` database. Do not run destructive database commands. Do not create, edit, package, display, or commit `.env` contents or credentials.
5. Do not overwrite the user's existing `.env`. Do not include `.env`, any secret files, virtual environments (`venv`, `.venv`), `__pycache__`, caches, local database dumps, or sensitive credentials in any final archive.
6. Keep Cash on Delivery as the supported payment method if that is what the existing implementation provides. Do not invent a payment gateway, completed transaction, or successful payment.
7. Do not claim a page or feature works just because its HTML file exists. Connect it to existing API logic and report any feature that remains incomplete.
8. Do not stop after writing a plan. Implement the changes, inspect the result, and provide an accurate summary.

## 3. Required screens and design requirements

Audit the actual frontend directory first. Reuse current filenames and shared components wherever possible; do not create duplicate pages merely to match this list.

### A. Public / authentication screens

1. **Homepage (`index.html`)**
   - Redesign the current plain, minimal homepage to resemble the reference’s branded hero.
   - Include the Food DNA brand, restrained botanical decoration, an attractive food visual, and the headline **“Good Food, Better You.”**
   - Explain the personalized meal recommendation value proposition in concise copy.
   - Provide clear actions for browsing restaurants, browsing food, logging in, creating a customer account, and applying as a restaurant, based on existing routes/pages.
   - Keep the existing backend connection check if already implemented, but style it as a secondary utility rather than the main CTA.
   - The hero must be polished and visually balanced—not just a white box with several buttons.

2. **Login (`login.html`)**
   - Use a branded split layout or card layout similar to the reference: decorative/food visual and a clear form area.
   - Preserve supported role selection and authentication flow as implemented.
   - Provide show/hide password if appropriate, clear errors, loading state, and links to registration and password recovery.

3. **Registration (`register.html`)**
   - Match the visual system and preserve existing registration fields and API flow.
   - Enforce the project’s requested validation in both frontend and backend for new accounts:
     - Full name accepts **letters and ordinary spaces only**. Reject numbers, hyphens, apostrophes, periods, and other punctuation. Use a Unicode-aware letters-and-spaces rule if compatible with the existing implementation. Trim leading/trailing whitespace and avoid empty names.
     - New registration email addresses must end in the exact domain `@gmail.com` (case-insensitive comparison is acceptable). Reject other domains, malformed addresses, incomplete domains, and suffix tricks such as `user@gmail.com.evil`.
     - Do not unexpectedly block existing users from logging in merely because their legacy account email uses another domain. Apply the Gmail-only restriction to new-account creation flows that the user requested, not indiscriminately to login.
   - Filter invalid name characters as the user types/pastes **and** validate again on submission. Server-side validation must remain authoritative; frontend validation alone is insufficient.
   - Show concise, field-specific validation messages and preserve accessibility.
   - Update related tests and test expectations that conflict with these explicit rules.

4. **Restaurant application / application status**
   - Keep the existing workflow and make forms consistent with the design system.
   - Apply the name/Gmail rules where these forms create or register a new account, without changing unrelated identity/business fields.

### B. Customer experience

5. **Customer dashboard**
   - Create a cohesive dashboard with sidebar navigation, top search bar/profile controls, a personalized greeting, preference summary (“Your Food DNA”), and recommendation cards with food imagery, price, cuisine/diet labels, and ratings only when real data is available.
   - Use existing API results, loading states, empty states, and error states. Do not hard-code fake dynamic data.

6. **Restaurant browsing and food menu**
   - Style restaurant listings, category filters, cuisine/diet filters, search, sort controls and meal cards in line with the reference.
   - Keep existing query parameters, filtering, pagination, and API integration.
   - Include clear price, availability and add-to-cart affordances only when supported by the current API.

7. **Meal detail (`meal.html` or existing equivalent)**
   - Use a large meal image area, name, description, price, ingredient/diet/spice labels if provided, quantity controls, and Add to Cart action.
   - Preserve meal IDs and endpoint calls. Never trust client-side price for cart/order calculations.

8. **Cart (`cart.html`)**
   - Style line items, quantity controls, remove/clear controls, server-provided subtotal/delivery fee/total, empty state, and Proceed to Checkout.
   - Preserve the one-restaurant-per-cart rule if implemented. Explain restaurant conflicts clearly and only clear the cart after explicit user confirmation.

9. **Checkout / delivery address / payment**
   - Use a clear step-based or card layout resembling the reference.
   - Show an order summary and address form with accessible validation.
   - Show Cash on Delivery only if it is the supported method; clarify that payment is collected on delivery.
   - Prevent accidental double submission and show real server responses. Do not fabricate a successful order.

10. **Order confirmation/details, order history and tracking**
    - Present real order ID, items, totals, current status, address, payment status, and status history when the API provides them.
    - Use status badges and a timeline/tracking visual similar to the reference, but do not show a live map or courier location unless supported by real data.
    - Preserve authorization and ownership enforcement.

11. **Food Memory**
    - Present the customer’s food activity/history in a visual feed, using actual API data.
    - Clearly distinguish empty/loading/error states. Avoid inventing consumed meals or events.

12. **Feedback and ratings**
    - Provide a refined feedback/review form and display review cards based only on API-returned data.
    - Enforce the existing feedback eligibility rules and prevent duplicate or unauthorized feedback if the backend supports those checks.

13. **Reverse Food Ordering**
    - Style the natural-language or preference entry form and resulting meal recommendations. Preserve the existing logic; do not pretend this is AI-powered if it is rule-based.

14. **Food DNA Preferences**
    - Use clear choice chips/cards for cuisine, dietary choices, spice level, health goals and budget only when those fields exist in the current data model.
    - Load current values from the backend, persist changes through existing endpoints, and show save success/errors accurately.

15. **Customer profile**
    - Provide readable profile details and edit forms using supported fields and existing API routes.
    - Do not expose password hashes, internal IDs unnecessarily, or another user’s data.

### C. Operational and administration dashboards

16. **Restaurant Admin dashboard**
    - Use an appropriate admin sidebar, summary cards, order summaries and menu-management shortcuts.
    - Statistics must be calculated from real API data. If the backend does not provide a metric, omit it or clearly show “Not available”; do not hard-code sample business data.

17. **Restaurant menu/restaurant management**
    - Consistent meal-management table/cards, add/edit forms, availability toggles, price validation and image handling supported by the current API.
    - Preserve restaurant ownership/role checks.

18. **Chef / Staff dashboard**
    - Provide a clear pending/in-progress/completed order workflow and prominent status actions only where authorized by current routes.
    - Preserve server-side transition validation and role restrictions.

19. **Delivery partner dashboard**
    - Present assigned deliveries, addresses, delivery status actions and contact details only when exposed by existing authorized APIs.
    - Do not show a fake map, fake GPS, or fake courier location.

20. **Super Admin dashboard**
    - Provide summary cards and navigation for users, restaurant applications, staff/delivery management, reports or settings only where supported by the project.
    - Never bypass or weaken role-based access controls.

21. **User management / applications / other existing screens**
    - Apply the same visual design to all remaining pages and modals discovered in the actual project. Do not leave unrelated pages with the old design.

## 4. Shared design system and implementation

- Create or refine shared CSS variables for the burgundy, blush, cream, neutral text, border, success/warning/error states, spacing, radius, shadow and typography tokens.
- Reuse existing `css/style.css` or project stylesheet organization where appropriate instead of creating conflicting stylesheets.
- Reuse shared navigation/layout logic in existing `layout.js` and existing API helpers in `api.js` where available.
- Maintain consistent active navigation, role-appropriate links, loading skeletons/spinners, empty states, error banners, and success feedback.
- Use Bootstrap classes/components if the project already uses Bootstrap, but customize them to match the reference and avoid stock Bootstrap appearance.
- Avoid inline style duplication; avoid giant HTML files with repeated CSS/JS if shared components can do the job safely.
- Ensure every new button has a meaningful working action. Remove or visibly disable unsupported actions rather than leaving dead buttons.
- Preserve existing URLs and local server usage. All relative paths must work when served with `python -m http.server 5500` from the frontend directory.
- Avoid adding large new dependencies unless necessary; explain any required installation.

## 5. Validation and regression requirements

After implementing the redesign:

1. Run Python syntax checks for created/modified Python files.
2. Run JavaScript syntax checks for created/modified JavaScript files where the available tools permit.
3. Run focused tests for name and Gmail validation, including frontend and backend tests.
4. Run the existing automated test suite **only after confirming the configured test database name is safe**. Inspect the test setup first because the test suite may drop and recreate its dedicated `_test` database. Never point tests to the real `fooddna` database.
5. Check that every HTML page references existing local CSS/JS/assets and that every local link points to an existing page or a documented route.
6. Check browser console and network errors if a browser testing tool is available. If it is not available, say this check was not performed.
7. Perform a structural pass across all customer/admin/staff/delivery pages so no screen has been accidentally omitted.
8. Do not run migrations against the user's real database. Do not reset or seed the real database.
9. Record each check as **PASS**, **FAIL**, or **NOT RUN**, with accurate output. Never claim a test passed if it was not run.

## 6. Final deliverables

- The redesigned project in the existing workspace, with previous functionality preserved.
- Updated README/audit/progress documentation summarizing the UI changes, validation rules, checks actually run, limitations and manual browser checks still required.
- A new archive named `fooddna18_UI_REDESIGN.zip` containing the complete project source, excluding `.env`, `.venv/`, `venv/`, `__pycache__/`, caches, credentials, secrets and database dumps.
- Verify that the archive exists, can be opened, and contains the expected source files before reporting it.
- Do not overwrite the user’s original project or original archive. Keep the final package separate.

## 7. How to work

Use this sequence:

1. Inspect the current project structure and existing UI/backend integration.
2. Identify reusable assets, CSS, shared navigation and all pages.
3. Implement the shared design system and public/auth pages.
4. Implement customer pages and flows.
5. Implement Restaurant Admin, staff, delivery and Super Admin pages.
6. Apply and test the requested registration validation rules.
7. Check visual consistency and responsiveness across every existing page.
8. Run the available checks safely, update documentation, and package the verified project.

**Do the implementation now. Do not merely respond with another plan.** If any existing endpoint or feature is missing, do not invent its behavior: preserve what exists, mark the gap, and report it clearly. Prioritize a complete, consistent visual redesign while retaining working FoodDNA functionality.

## 8. Mandatory beginner-friendly run instructions (very important)

The user is a beginner working on Windows with PowerShell. Do not assume they know how to configure a Python project, databases, virtual environments, or multiple terminals. As part of this task, create and maintain **`docs/SETUP_AND_RUN_WINDOWS.md`** and add a short, prominent “Run FoodDNA locally” section to `README.md` that links to it. The instructions must be based on the actual final code, scripts, environment variables, folder layout and route configuration—not generic or guessed commands.

The run guide must be complete, numbered, copy-and-paste friendly, and explain each step in plain language. It must cover:

1. **Where to extract and open the project**: show the expected folder structure (`backend`, `frontend`, `database`, `docs`, `tests`, `requirements.txt`) and explain how to `cd` to the project root in PowerShell. Make commands work from the stated folder and explicitly say when a command needs a new PowerShell window.
2. **Python setup**: show the supported Python version after checking project dependencies; show creating and activating a local virtual environment, installing `requirements.txt`, how to activate the existing environment on later runs, and how to recover if PowerShell blocks script activation. Do not ask the user to delete an existing environment blindly.
3. **`.env` setup**: explain that the ZIP excludes `.env`; show how to copy the user's existing `.env` into the extracted project only if that is appropriate and the file exists, or how to create one from `.env.example` without overwriting an existing `.env`. Explain that users must keep real credentials private and must never paste `.env` contents into chat.
4. **Database safety before commands**: inspect `backend/init_dev_database.py`, `backend/seed_demo_data.py`, config loading, and migration behavior. Give the exact safe commands for initializing a dedicated development database (e.g. `fooddna_dev` only if the actual code supports it), and seeding demo data. Explain what each script changes. Do not recommend any command that drops, resets, migrates or seeds the real `fooddna` database. If a script could affect the real database or its behavior is unclear, do not tell the user to run it; state the safety concern and give a safe alternative. Verify the app's actual effective `DB_NAME` after `.env` loading, including how to set it in the same PowerShell window for that session if required.
5. **Starting the backend**: give the exact working `cd` and run commands based on the actual project. Explain how to recognize a successful startup and that the terminal must remain open. Include the real health-check routes only if they exist; otherwise identify the routes that actually exist.
6. **Starting the frontend**: open a second PowerShell window, navigate to the actual `frontend` directory, run the static server on the configured port, and provide the exact homepage URL. Explain that the frontend server and backend server must both remain running in separate windows. If API base URL/CORS settings must be configured, explain them exactly.
7. **Safe testing**: inspect `tests/conftest.py` and all test database safeguards. Explain that the suite may drop/recreate its configured test database. Give the exact test command only after establishing the expected test DB name and safety conditions. Explicitly instruct the user to ensure the test database is disposable and different from the real database. Never set the test DB equal to `fooddna` or `fooddna_dev` if the tests might drop/recreate it.
8. **How to stop and restart**: explain `Ctrl+C`, re-activating the virtual environment, and restarting both servers.
9. **Troubleshooting**: provide short, specific fixes for common issues, at least: wrong folder / `cd` path not found; Python or pip command not found; virtual environment activation blocked; missing package; port 5000 or 5500 already in use; missing or invalid `.env`; MySQL service stopped or access denied; database connection errors; missing `create_app`; frontend loads but API calls fail; and a failing database health endpoint. Avoid advising users to replace `backend/app/__init__.py` blindly.
10. **Expected output and next steps**: label which checks should pass, what success looks like, how the user should report an error (copy the full error text, but never credentials), and clearly separate “app starts” from “all features are validated.”

Keep the instructions aligned with the final delivered archive and verify all written paths, filenames, ports, scripts, and URLs against the actual source. Do not invent scripts, environment variables, routes, log output or success messages. If the project does not safely support a separate development database, fix that safely first where feasible; otherwise explain the limitation clearly and do not instruct the user to risk their real database.

## 9. Required final response to the user

When the implementation and packaging are finished, provide:

- The final project archive link.
- The standalone Markdown UI redesign prompt or setup guide link if generated.
- A concise status table distinguishing automated checks actually run, manual browser checks completed, and checks not run.
- A **beginner-friendly numbered “how to run it” section directly in your final response**, not merely a link to README. Use exact commands and the correct order for this project, including which commands go in PowerShell window 1 versus window 2.
- A clear warning before any command that can modify or delete database data.
- A statement that the user should send the complete error text if a step fails, while omitting passwords, secret keys and `.env` contents.

Do not say “everything works” solely because the app launches or syntax tests pass. The setup instructions and final response are part of the deliverable, not optional documentation.

