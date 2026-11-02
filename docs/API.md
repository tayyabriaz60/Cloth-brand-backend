# Cloth POS API

Base URL locally: `http://localhost:8000`

All business routes require `Authorization: Bearer <access_token>` except `POST /api/auth/login` and `GET /health`.

Errors always look like:

```json
{"code": "not_found", "message": "Not found"}
```

Quantities are strings with 2 decimal places (`"3.50"`). Money is integer rupees.

“Today” is the Asia/Karachi calendar day, converted to UTC for storage and queries.

Cross-shop: if `product_id`, `customer_id`, `supplier_id`, `bill_id` or an image id does not belong to the caller’s shop, the API returns **404** `{"code":"not_found"}`. It does not say that the row exists elsewhere.

Cashier responses never include `cost_price`, `profit`, `today_sales`, `today_received`, or `week_sales`. Bill `total` / `paid_amount` are the customer-facing amounts (not profit) and are returned to both roles on bill endpoints.

---

## Auth

### POST /api/auth/login

Role: public.

Request:

```json
{"username": "owner", "password": "owner123"}
```

Username is matched lower-case. Success **200**:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "Demo Owner", "role": "owner"},
  "shop": {
    "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "name_ur": "ڈیمو کلاتھ ہاؤس",
    "name_en": "Demo Cloth House",
    "address": null,
    "phone": null,
    "footer_text": "شکریہ! دوبارہ تشریف لائیں",
    "paper_width": 80,
    "auto_print": false,
    "settings": {}
  }
}
```

Errors: `401 invalid_credentials`, `429 too_many_attempts`, `422 validation_error`.

### GET /api/auth/me

Role: any logged-in user. **200** same `user` + `shop` as login (no token). `401 not_authenticated`.

### POST /api/auth/change-password

Role: any logged-in user. New password min 10 characters and different from current.

Request:

```json
{"current_password": "owner123", "new_password": "new-password-1"}
```

Success **204** empty body.

Errors: `422 wrong_password`, `422 same_password`, `422 weak_password` (or `422 validation_error` if shorter than 10).

---

## Categories

### GET /api/categories

Role: owner, cashier. **200**:

```json
{"items": [{"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "name_ur": "ان اسٹچڈ", "name_en": "Unstitched", "sort_order": 0}]}
```

---

## Products

### GET /api/products

Query: `q` (optional, case-insensitive search of `name_ur`, `name_en`, `design_no`), `category_id` (optional UUID), `include_inactive` (default `false`).

Role: both. Owner items include `cost_price`. Cashier items do not.

**200 owner:**

```json
{
  "items": [{
    "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
    "name_ur": "لان پرنٹڈ",
    "name_en": "Printed Lawn",
    "design_no": "LW-101",
    "unit": "gaz",
    "sale_price": 480,
    "min_stock": "20.00",
    "category": {"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "name_ur": "ان اسٹچڈ", "name_en": "Unstitched"},
    "images": [{"id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee", "public_url": "https://img.example/shops/.../x.webp", "sort_order": 0}],
    "stock": "120.50",
    "is_low_stock": false,
    "is_active": true,
    "cost_price": 380
  }]
}
```

`stock` is `SUM(stock_movements.qty_change)`. `is_low_stock` is `stock < min_stock`.

### POST /api/products

Role: **owner**. Success **201** (owner product object as above).

Request:

```json
{
  "name_ur": "لان پرنٹڈ",
  "name_en": "Printed Lawn",
  "design_no": "LW-101",
  "unit": "gaz",
  "cost_price": 380,
  "sale_price": 480,
  "min_stock": "20.00",
  "category_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
  "is_active": true,
  "opening_stock": "120.50"
}
```

`unit` must be `gaz` or `piece`. `opening_stock` is optional; if set, adds an `opening` stock movement. `category_id` must belong to this shop or be omitted.

Errors: `403 owner_only`, `404 not_found` (bad category), `422 invalid_unit`.

### PATCH /api/products/{id}

Role: **owner**. Body: any subset of the create fields except `opening_stock`. **200** owner product object.

---

## Customers

### GET /api/customers

Query: `q` (optional name search). Role: both. `balance` = SUM(udhaar) − SUM(payment).

```json
{"items": [{"id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "name": "Ahmed Raza", "phone": "03001234567", "note": "Regular customer", "balance": 500}]}
```

### POST /api/customers

**201**:

```json
{"id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "name": "Ahmed Raza", "phone": "03001234567", "note": null, "balance": 0}
```

Request: `{"name": "Ahmed Raza", "phone": "03001234567", "note": null}`

### PATCH /api/customers/{id}

Body: any of `name`, `phone`, `note`. **200** customer object.

### GET /api/customers/{id}/ledger

Newest first. `bill_no` is set when the entry is tied to a bill.

```json
{
  "items": [{
    "id": "11111111-1111-1111-1111-111111111111",
    "entry_type": "udhaar",
    "amount": 600,
    "bill_id": "22222222-2222-2222-2222-222222222222",
    "bill_no": 1,
    "note": null,
    "created_at": "2026-11-02T12:00:00"
  }]
}
```

`entry_type` is `udhaar` or `payment`. Amount is always a positive integer.

---

## Bills

The **server** recomputes `subtotal`, `discount` (rupees), and `total`. Client totals are ignored.

`subtotal` = sum of `round(qty × rate)` (half-up, whole rupees).  
`discount_type`: `amount` (rupees) or `percent` (0–100, then rounded to rupees).  
`total` = subtotal − discount.

Rules:

- `items` not empty; each `qty > 0`, `rate >= 0`
- discount rupees ≤ subtotal
- `cash` / `online`: `paid_amount` must equal `total`
- `udhaar`: `customer_id` required and `0 <= paid_amount < total`
- products must be active; missing/other-shop ids → `404 not_found`
- low or negative stock does **not** block the sale; it adds strings to `warnings`

One transaction: bill + items (name snapshot + rate) + negative `stock_movements` (`reason=sale`, `ref_id=bill id`) + ledger `udhaar` for `total - paid_amount` when that is > 0.

Bill `id` is a client UUID. If that id already exists **for this shop**, the existing bill is returned with **200** (no second write). A new bill is **201**. `bill_no` is sequential per shop.

### POST /api/bills

Request:

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
  "items": [{"product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd", "qty": "3.50", "rate": 200}],
  "discount": 0,
  "discount_type": "amount",
  "payment_type": "udhaar",
  "paid_amount": 100,
  "customer_lang": "ur",
  "note": null
}
```

**201 / 200**:

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "bill_no": 1,
  "customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
  "subtotal": 700,
  "discount": 0,
  "total": 700,
  "paid_amount": 100,
  "payment_type": "udhaar",
  "customer_lang": "ur",
  "note": null,
  "items": [{
    "id": "33333333-3333-3333-3333-333333333333",
    "product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
    "name_snapshot": "لان پرنٹڈ",
    "qty": "3.50",
    "unit": "gaz",
    "rate": 200,
    "line_total": 700
  }],
  "warnings": [],
  "created_at": "2026-11-02T12:00:00"
}
```

Example warning: `"لان پرنٹڈ: low_stock"`. Negative remaining stock: `"لان پرنٹڈ: negative_stock"`.

Errors: `422 empty_items`, `422 udhaar_needs_customer`, `422 invalid_paid_amount`, `422 discount_too_high`, `422 inactive_product`, `422 invalid_discount_type`, `422 invalid_payment_type`, `422 invalid_customer_lang`, `404 not_found`, `409 conflict`.

### GET /api/bills?date=YYYY-MM-DD

Default `date` = today (Karachi). **200** `{"items": [ <BillOut>, ... ]}` (`warnings` is `[]` on list/get).

- **Owner:** any Karachi date.
- **Cashier:** only today. Omit `date`, or pass today's date. A date in the past (or any day that is not today) returns **403** `{"code":"forbidden","message":"Cashiers can only see today's bills"}`.

### GET /api/bills/{id}

**200** one `BillOut`. **404 not_found**.

---

## Stock

### GET /api/stock?q=

Active products with qty and low flag. Owner rows include `cost_price`.

```json
{
  "items": [{
    "product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
    "name_ur": "لان پرنٹڈ",
    "name_en": "Printed Lawn",
    "design_no": "LW-101",
    "unit": "gaz",
    "qty": "120.50",
    "min_stock": "20.00",
    "is_low_stock": false
  }]
}
```

### GET /api/stock/{product_id}/history

Newest first.

```json
{
  "items": [{
    "id": "44444444-4444-4444-4444-444444444444",
    "qty_change": "-3.50",
    "reason": "sale",
    "ref_id": "22222222-2222-2222-2222-222222222222",
    "note": null,
    "created_at": "2026-11-02T12:00:00"
  }]
}
```

`reason`: `sale` | `purchase` | `return` | `adjust` | `opening`.

### POST /api/stock/purchase

Role: owner, cashier. If `cost_price` is sent **and** the caller is owner, the product’s cost is updated. Cashier `cost_price` is ignored.

```json
{"product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd", "qty": "12.00", "cost_price": 380, "supplier_name": "Ali Mills", "note": "bale"}
```

**201** a stock row (owner includes `cost_price`).

### POST /api/stock/adjust

Role: **owner**. `qty_change` may be negative; cannot be 0. `note` is required.

```json
{"product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd", "qty_change": "-0.50", "note": "torn end"}
```

**201** owner stock row. Errors: `403 owner_only`, `422 qty_change_zero`.

---

## Udhaar

### GET /api/udhaar

Customers with `balance > 0`, oldest unpaid first (`days_since_oldest` is Karachi days since the oldest udhaar entry).

```json
{
  "items": [{
    "customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "name": "Ahmed Raza",
    "phone": "03001234567",
    "balance": 500,
    "days_since_oldest": 0
  }]
}
```

### POST /api/ledger/payment

`amount > 0` and `amount <= current balance`.

```json
{"customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "amount": 200, "note": "cash"}
```

**201**:

```json
{
  "id": "55555555-5555-5555-5555-555555555555",
  "entry_type": "payment",
  "amount": 200,
  "bill_id": null,
  "bill_no": null,
  "note": "cash",
  "created_at": "2026-11-02T12:00:00"
}
```

Errors: `422 payment_exceeds_balance`, `404 not_found`.

---

## Dashboard

### GET /api/dashboard

**Owner 200:**

```json
{
  "today_sales": 700,
  "today_received": 200,
  "total_udhaar": 500,
  "low_stock_count": 1,
  "top_udhaar": [{"customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "name": "Ahmed Raza", "balance": 500}],
  "low_stock": [{"product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd", "name_ur": "لان پرنٹڈ", "name_en": "Printed Lawn", "stock": "6.50", "min_stock": "20.00"}],
  "last_bills": [{"id": "22222222-2222-2222-2222-222222222222", "bill_no": 1, "total": 700, "paid_amount": 200, "payment_type": "udhaar", "created_at": "2026-11-02T12:00:00"}],
  "week_sales": [{"date": "2026-10-27", "total": 0}]
}
```

`today_received` = sum of `paid_amount` on today’s bills + today’s ledger payments. `week_sales` is 7 Karachi dates, oldest first, including today.

**Cashier 200** — only:

```json
{
  "total_udhaar": 500,
  "low_stock_count": 1,
  "top_udhaar": [{"customer_id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "name": "Ahmed Raza", "balance": 500}],
  "low_stock": [{"product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd", "name_ur": "لان پرنٹڈ", "name_en": "Printed Lawn", "stock": "6.50", "min_stock": "20.00"}],
  "last_bills": [{"id": "22222222-2222-2222-2222-222222222222", "bill_no": 1, "payment_type": "udhaar", "created_at": "2026-11-02T12:00:00"}]
}
```

Cashier `last_bills` have no `total` or `paid_amount`.

---

## Shop

### GET /api/shop

Role: both.

```json
{
  "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  "name_ur": "ڈیمو کلاتھ ہاؤس",
  "name_en": "Demo Cloth House",
  "address": null,
  "phone": null,
  "footer_text": "شکریہ! دوبارہ تشریف لائیں",
  "paper_width": 80,
  "auto_print": false
}
```

### PATCH /api/shop

Role: **owner**. Any of `name_ur`, `name_en`, `address`, `phone`, `footer_text`, `paper_width` (58 or 80), `auto_print`. **200** same shape. `403 owner_only`, `422 invalid_paper_width`.

---

## Users

### GET /api/users

Role: **owner**.

```json
{"items": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "Demo Owner", "username": "owner", "role": "owner", "is_active": true}]}
```

### POST /api/users

Role: **owner**. Always creates a **cashier**. Username stored lower-case, globally unique. Password min 10 characters.

```json
{"name": "Ali", "username": "ali", "password": "cashier-pass-1"}
```

**201** staff object. Errors: `409 conflict` (username taken), `422 weak_password`.

### PATCH /api/users/{id}

Role: **owner**. `{"is_active": false}`. Cannot deactivate yourself (`422 cannot_modify_self`).

---

## Uploads

Role: **owner** for every route in this section. Cashier gets **403** `{"code":"owner_only"}`.

If any required `R2_*` variable is unset, upload routes return **503** `{"code":"r2_unavailable","message":"Image uploads are not configured"}`. Other routes still work.

### POST /api/uploads/presign

Role: **owner**.

```json
{"content_type": "image/webp", "product_id": "dddddddd-dddd-dddd-dddd-dddddddddddd"}
```

`content_type` must be `image/webp`, `image/jpeg`, or `image/png`. **200**:

```json
{
  "upload_url": "https://<account>.r2.cloudflarestorage.com/...",
  "key": "shops/<shop_id>/products/<uuid>.webp",
  "public_url": "https://images.example/<key>"
}
```

Browser PUTs the file to `upload_url` with the same `Content-Type`. URL is valid 5 minutes. Size is limited in the browser, not here.

Errors: `403 owner_only`, `422 invalid_content_type`, `404 not_found`, `503 r2_unavailable`.

### POST /api/products/{id}/images

Role: **owner**.

```json
{"key": "shops/<shop_id>/products/<uuid>.webp"}
```

Key must start with `shops/<caller shop_id>/products/`. Max 3 images per product. **201**:

```json
{"id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee", "public_url": "https://images.example/...", "sort_order": 0}
```

Errors: `403 owner_only`, `422 invalid_key`, `422 image_limit`.

### DELETE /api/product-images/{id}

Role: **owner**. **204**. **404 not_found**. `403 owner_only`.

---

## Other

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok","database":"ok"}` |
| GET | /docs | OpenAPI UI |

Laptop script (not HTTP): `python -m scripts.set_password <username>` — asks for the new password twice with no echo. Same rules as change-password (min 10, different from current). Never prints the password.

---

## Error codes

| HTTP | code | when |
|---|---|---|
| 401 | not_authenticated | missing/bad token |
| 401 | invalid_credentials | login |
| 403 | owner_only | cashier hit an owner route |
| 403 | forbidden | cashier asked for bills on a day other than today |
| 404 | not_found | missing, or belongs to another shop |
| 409 | conflict | username taken, or bill id clash |
| 422 | validation_error | Pydantic (bad types/missing fields) |
| 422 | empty_items | bill with no lines |
| 422 | udhaar_needs_customer | |
| 422 | invalid_paid_amount | |
| 422 | discount_too_high | |
| 422 | inactive_product | |
| 422 | payment_exceeds_balance | |
| 422 | wrong_password / same_password / weak_password | |
| 422 | cannot_modify_self | |
| 422 | invalid_unit / invalid_paper_width / invalid_key / invalid_content_type / image_limit / qty_change_zero | |
| 429 | too_many_attempts | login |
| 503 | r2_unavailable | uploads only |
| 503 | database_unavailable | /health |
