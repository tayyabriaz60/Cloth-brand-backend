FEATURE: inventory         DATE: 2026-11-05        SHOP: Demo
Who uses it:        owner (all), cashier (view, stock in)
When, how often:    stock in: several times a week; adjustments: rare;
                    count: [ASSUMED] monthly
How it is done today: [ASSUMED] register/notebook, memory
What goes wrong today: [ASSUMED] stock unknown, finished design noticed
  too late, differences found at month end with no explanation
Shopkeeper's exact words: [FILL IN]

MUST
1. See current stock of every product (gaz or piece), search by name or
   design number, filter by category / fabric type / color / low / out.
2. Add stock when new maal arrives (quantity, cost, supplier name, note).
3. Adjust stock with a reason: damaged, missing, measurement correction,
   supplier return, count correction. A note is required. Owner only.
4. Physical count: enter the real quantity, the system records the
   difference as an adjustment. Owner only.
5. Movement history: who changed what, when, why, with the balance after
   each movement. Filters by product, type, date.
6. Low-stock and out-of-stock clearly visible.
7. Totals are shown separately per unit (gaz, piece).
SHOULD: stock value (owner only) based on last purchase cost.
WON'T (not in I1): thaan/roll records, variants, meter/yard conversion,
  barcode, FIFO, supplier accounts, purchase returns screen.

Data involved: stock_movements (exists), products (add fabric_type,
  color), adjust_reason on movements.
Screens: Inventory (list + summary), Stock In panel, Adjust panel, Count
  panel, Movements page.
Who may see or change what: cashier sees stock and can add stock, never
  sees cost or value, cannot adjust or count.
Real example: [PASTE a page of the real stock register]

DONE TEST (in the app, with gaz):
1. Product "Cotton" gets 300 gaz by stock in (cost Rs 400/gaz).
2. A bill sells 10 gaz: stock 290.
3. Adjust -5 gaz "damaged": stock 285.
4. Count: real quantity 280, system makes -5 "count correction": 280.
5. Movement history shows 4 lines with balances 300, 290, 285, 280.
6. Cashier can add stock but cannot adjust or count and sees no cost.
7. Trying to adjust below zero is rejected with a clear message.
