# FoodDNA - How recommendations work (Phase 5)

Status: **implemented, not yet tested against Flask and MySQL.** The pure
scoring functions were smoke-checked in isolation (see `README.md` section 7);
the pytest files in `tests/test_recommendations.py` are written but unrun.

There is no machine learning and no external service. Every score can be
reproduced by hand from the customer's saved preferences and the `meals`
columns. Code: `backend/app/services/recommendation_service.py`.

## 1. Inputs

* **Preferences** - one row per customer in `user_preferences`: `cuisine`,
  `meal_type`, `taste`, `spice_level`, `portion_size`, `food_type`,
  `dietary_preference` (text) and `budget` (decimal). Every field is optional.
* **Meals** - exactly the meals Phase 4 browsing shows (`meal_service.visible_meal_rows`):
  `meals.is_available`, category `is_active`, restaurant `status = 'approved'`.
  A meal that cannot be browsed can never be recommended.

A customer with no saved preference (no row, or a row whose fields are all
blank) gets an empty result with a message asking them to set preferences.
Nothing is invented for them and nothing is recorded.

## 2. Step 1 - hard rules (a meal that breaks one is removed)

| Rule | Applies when the customer set... | A meal is kept if... |
|---|---|---|
| Budget | `budget` | `meals.price <= budget`. Budget means "the most I will pay for one dish"; the schema has no per-order budget concept. |
| Food type | `food_type` = Veg | meal food type is Veg or Vegan |
| Food type | `food_type` = Vegan | meal food type is Vegan |
| Dietary | `dietary_preference` | the meal's `dietary_preference` is compatible (below) |

* `food_type` Non-Veg (or any other value) is **not** a hard rule: people who
  eat meat also eat vegetarian food. It is only a scoring preference.
* Dietary compatibility (case-insensitive): **Vegetarian** accepts Vegetarian
  and Vegan; **Eggetarian** accepts Eggetarian, Vegetarian and Vegan; any other
  label (Vegan, Gluten-Free, High-Protein, ...) must match exactly. A meal
  with **no** dietary label (`NULL`) is removed whenever a dietary preference
  is set, because its suitability cannot be shown.
* Missing data on an optional **soft** attribute never removes a meal; it just
  earns no points. Only the three hard rules remove meals.
* The response counts removed meals per rule (first failing rule, in the order
  budget, food type, dietary) in `summary.excluded` so the page can explain
  an empty or short list.

## 3. Step 2 - scoring (only meals that passed step 1)

| Preference | Points | Earned when |
|---|---|---|
| cuisine | 20 | equal to the meal's cuisine |
| meal_type | 15 | equal |
| taste | 15 | equal |
| spice_level | 15 | equal; **half** (7.5) if one step away on `none < mild < medium < hot < extra hot` |
| portion_size | 10 | equal |
| food_type | 10 | equal, or (Veg/Vegan) compatible type |
| dietary_preference | 10 | always, once the meal passed the hard rule |
| budget | 5 | always, once the meal passed the hard rule |

Comparisons ignore case and surrounding spaces.

`score = 100 x points earned / points available`, where "available" is the sum
of the weights of the preferences the customer actually set. So a customer who
sets only two preferences can still reach 100, and the number reads as "how
much of what you asked for this dish gives you". It is rounded to 2 decimals.

A meal that earns **0** points is not recommended (it matches nothing the
customer asked for). If the customer set only hard-rule preferences (for
example budget only), every eligible meal earns points and scores 100.

## 4. Step 3 - ranking and output

Sort by score (highest first), then price (lowest first), then name, then id,
so the same data always gives the same order. Keep the first `limit` (default
10, maximum 30). Each item carries `reasons`, the sentences for the points it
earned (for example "Cuisine matches your preference: Chinese", "Spice level is
close to your choice (Hot instead of Medium)", "Price 160.50 is within your
budget of 200.00").

## 5. History and Food Memory

`POST /api/recommendations` stores the returned items in `recommendations`
(`user_id`, `meal_id`, `score`, `reason`, `generated_at`). If the same meal was
already recommended to the same customer within the last **60 minutes**
(`RECOMMENDATION_DEDUPE_MINUTES`), that row is refreshed instead of adding a
new one. `GET /api/recommendations` is read-only. Only ids, the score and the
explanation text are stored.

Food Memory (`food_memory_service.py`) logs `recommendations_viewed` (5-minute
dedupe), `recommendation_selected` and `meal_viewed` (30-minute dedupe per
meal). `record_event` is the single entry point; Phase 6 will register
`added_to_cart` and `order_placed` there. **Food Memory is not used for scoring
yet.**

## 6. Limitations

* Only exact (case-insensitive) matches count, apart from the spice-level
  neighbour credit and the Veg/Vegan and dietary compatibility rules. "Punjabi"
  and "North Indian" are different cuisines to the scorer.
* All attribute values are free text typed by restaurants and customers. The
  preference form offers values found in the current catalogue, but nothing
  stops a restaurant labelling the same thing two ways.
* The weights are judgement calls, not learned from data. Change `WEIGHTS` in
  one place to tune them.
* No popularity, rating, price-closeness, time-of-day or order-history signals.
* Dishes without a dietary label are hidden for customers with a dietary
  preference (safety over coverage).
* The whole visible catalogue is scored in Python per request; fine for
  hundreds or low thousands of dishes, not for very large catalogues.
* Not verified on a real database yet (see README section 7).
