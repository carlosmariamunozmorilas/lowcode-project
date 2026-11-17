# Predict, then prove (Session 5, step 7)

Run against a freshly generated demo database (`scripts/generate_shop_data.py`)
with the kit's `tools/sql.py`, which opens a **plain connection with SQLite's
defaults** unless `--fk` is added. The demo database already has good rows:
the stores Luna Home (id 1), Brote Cosmetics and Roble Muebles.

**The predictions are Carlos's, written before anything is run.**

| Test | What is tried | I predict (accept / reject) | What happened | Surprised? Why? |
|---|---|---|---|---|
| A · Duplicate | a second store called *Luna Home* | ✍️ | | |
| B · Breaks a CHECK | a store with a contribution margin of 1.5 (150 %) | ✍️ | | |
| C · Points at id 999 | an action for store 999, which does not exist | ✍️ | | |
| C again, with `--fk` | the same action, foreign keys switched on | ✍️ | | |
| D · Delete rule | delete Luna Home, which has actions and orders (on a copy) | ✍️ | | |
| D again, with `--fk` | the same delete, foreign keys switched on | ✍️ | | |

## The statements

```sql
-- A
INSERT INTO clients (name, sector, products, audience, main_channels, avg_order_value_eur,
  contribution_margin, purchase_frequency, monthly_budget_eur, roi_target, business_model)
VALUES ('Luna Home', 'Homeware', 'Lamps', 'Buyers', 'Meta', 65, 0.35, 'occasional', 5000, 0.2, 'dtc');

-- B
INSERT INTO clients (name, sector, products, audience, main_channels, avg_order_value_eur,
  contribution_margin, purchase_frequency, monthly_budget_eur, roi_target, business_model)
VALUES ('Margin Test', 'Homeware', 'Lamps', 'Buyers', 'Meta', 65, 1.5, 'occasional', 5000, 0.2, 'dtc');

-- C (then the same with --fk)
INSERT INTO actions (client_id, discipline, title, benefit_type, requester_id)
VALUES (999, 'ecommerce', 'Orphan test', 'contribution', 4);

-- D (on a copy of the database; then the same with --fk)
DELETE FROM clients WHERE id = 1;
```
