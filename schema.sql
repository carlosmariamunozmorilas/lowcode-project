CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(title) <= 200),
    description TEXT CHECK (description IS NULL OR length(description) <= 2000),
    lever TEXT NOT NULL CHECK (lever IN (
        'paid_prospecting',
        'seo_content',
        'email_traffic',
        'checkout_friction',
        'product_page',
        'trust_signals',
        'bundles',
        'cross_sell',
        'free_shipping'
    )),
    cost_eur REAL NOT NULL DEFAULT 0 CHECK (cost_eur >= 0),
    cost_hours REAL NOT NULL DEFAULT 0 CHECK (cost_hours >= 0),
    status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN (
        'submitted',
        'assigned',
        'in_review',
        'approved',
        'closed',
        'rejected',
        'cancelled'
    )),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
