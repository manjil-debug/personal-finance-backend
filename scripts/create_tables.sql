-- =============================================================
-- Personal Finance Tracker — Database Schema
-- PostgreSQL 16 + pg_uuidv7 extension
-- =============================================================

-- pgcrypto is required for gen_random_bytes used in uuid_v7()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- UUID v7-like function (time-ordered, sortable)
CREATE OR REPLACE FUNCTION uuid_v7()
RETURNS uuid AS $$
SELECT (
    lpad(to_hex((extract(epoch FROM clock_timestamp()) * 1000)::bigint), 12, '0') ||
    encode(gen_random_bytes(10), 'hex')
)::uuid;
$$ LANGUAGE sql;

-- =============================================================
-- ENUMS
-- =============================================================

CREATE TYPE auth_provider    AS ENUM ('local', 'google');
CREATE TYPE account_type     AS ENUM ('checking', 'savings', 'credit_card', 'cash', 'investment', 'loan', 'other');
CREATE TYPE category_type    AS ENUM ('income', 'expense');
CREATE TYPE transaction_type AS ENUM ('income', 'expense', 'transfer');
CREATE TYPE budget_period    AS ENUM ('weekly', 'monthly', 'yearly');

-- =============================================================
-- TABLES
-- =============================================================

-- -------------------------------------------------------------
-- users
-- -------------------------------------------------------------
CREATE TABLE users (
    id            UUID         PRIMARY KEY DEFAULT uuid_v7(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    full_name     VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),                          -- NULL for Google-only accounts
    google_id     VARCHAR(255) UNIQUE,                   -- NULL for local-only accounts
    avatar_url    TEXT,
    provider      auth_provider NOT NULL DEFAULT 'local',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    is_verified   BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_auth_method CHECK (
        (provider = 'local'  AND password_hash IS NOT NULL) OR
        (provider = 'google' AND google_id     IS NOT NULL)
    )
);

-- -------------------------------------------------------------
-- refresh_tokens
-- -------------------------------------------------------------
CREATE TABLE refresh_tokens (
    id         UUID        PRIMARY KEY DEFAULT uuid_v7(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,             -- store SHA-256 of the token, never plaintext
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,                              -- NULL = still valid
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- accounts  (bank accounts, wallets, credit cards, etc.)
-- -------------------------------------------------------------
CREATE TABLE accounts (
    id         UUID         PRIMARY KEY DEFAULT uuid_v7(),
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL,
    type       account_type NOT NULL,
    balance    NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    currency   CHAR(3)        NOT NULL DEFAULT 'USD',
    color      CHAR(7),                                  -- hex colour, e.g. #4CAF50
    icon       VARCHAR(50),
    is_active  BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- categories  (user-defined + system defaults, supports subcategories)
-- -------------------------------------------------------------
CREATE TABLE categories (
    id        UUID          PRIMARY KEY DEFAULT uuid_v7(),
    user_id   UUID          REFERENCES users(id) ON DELETE CASCADE, -- NULL = system category
    parent_id UUID          REFERENCES categories(id) ON DELETE SET NULL,
    name      VARCHAR(100)  NOT NULL,
    type      category_type NOT NULL,
    color     CHAR(7),
    icon      VARCHAR(50),
    is_system BOOLEAN        NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_system_category CHECK (
        (is_system = TRUE  AND user_id IS NULL) OR
        (is_system = FALSE AND user_id IS NOT NULL)
    )
);

-- -------------------------------------------------------------
-- transactions
-- -------------------------------------------------------------
CREATE TABLE transactions (
    id          UUID             PRIMARY KEY DEFAULT uuid_v7(),
    user_id     UUID             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id  UUID             NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id UUID             REFERENCES categories(id) ON DELETE SET NULL,
    type        transaction_type NOT NULL,
    amount      NUMERIC(18, 2)   NOT NULL,
    currency    CHAR(3)          NOT NULL DEFAULT 'USD',
    description VARCHAR(255)     NOT NULL,
    notes       TEXT,
    date        DATE             NOT NULL,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_positive_amount CHECK (amount > 0)
);

-- -------------------------------------------------------------
-- transfers  (links the two transaction records for account-to-account moves)
-- Each transfer creates:
--   • an 'expense' transaction on the source account
--   • an 'income'  transaction on the destination account
-- then ties them together here.
-- -------------------------------------------------------------
CREATE TABLE transfers (
    id                  UUID PRIMARY KEY DEFAULT uuid_v7(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    to_transaction_id   UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_different_transactions CHECK (from_transaction_id <> to_transaction_id)
);

-- -------------------------------------------------------------
-- budgets
-- -------------------------------------------------------------
CREATE TABLE budgets (
    id          UUID          PRIMARY KEY DEFAULT uuid_v7(),
    user_id     UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID          REFERENCES categories(id) ON DELETE SET NULL,
    name        VARCHAR(100)  NOT NULL,
    amount      NUMERIC(18, 2) NOT NULL,
    period      budget_period  NOT NULL DEFAULT 'monthly',
    start_date  DATE           NOT NULL,
    end_date    DATE,                                    -- NULL = recurring / no end
    is_active   BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_positive_budget   CHECK (amount > 0),
    CONSTRAINT chk_budget_date_range CHECK (end_date IS NULL OR end_date > start_date)
);

-- =============================================================
-- INDEXES
-- =============================================================

CREATE INDEX idx_refresh_tokens_user_id       ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at    ON refresh_tokens(expires_at);

CREATE INDEX idx_accounts_user_id             ON accounts(user_id);

CREATE INDEX idx_categories_user_id           ON categories(user_id);
CREATE INDEX idx_categories_parent_id         ON categories(parent_id);

CREATE INDEX idx_transactions_user_id         ON transactions(user_id);
CREATE INDEX idx_transactions_account_id      ON transactions(account_id);
CREATE INDEX idx_transactions_category_id     ON transactions(category_id);
CREATE INDEX idx_transactions_date            ON transactions(date);
CREATE INDEX idx_transactions_user_date       ON transactions(user_id, date DESC);

CREATE INDEX idx_budgets_user_id              ON budgets(user_id);
CREATE INDEX idx_budgets_category_id          ON budgets(category_id);

-- =============================================================
-- UPDATED_AT TRIGGER
-- =============================================================

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_budgets_updated_at
    BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================
-- SEED — system-level default categories
-- (user_id = NULL, is_system = TRUE)
-- =============================================================

INSERT INTO categories (name, type, icon, is_system) VALUES
    -- Expense
    ('Food & Dining',      'expense', 'utensils',        TRUE),
    ('Transportation',     'expense', 'car',              TRUE),
    ('Shopping',           'expense', 'shopping-bag',     TRUE),
    ('Entertainment',      'expense', 'film',             TRUE),
    ('Health & Fitness',   'expense', 'heart',            TRUE),
    ('Housing',            'expense', 'home',             TRUE),
    ('Utilities',          'expense', 'zap',              TRUE),
    ('Education',          'expense', 'book',             TRUE),
    ('Travel',             'expense', 'plane',            TRUE),
    ('Personal Care',      'expense', 'smile',            TRUE),
    ('Gifts & Donations',  'expense', 'gift',             TRUE),
    ('Other Expense',      'expense', 'more-horizontal',  TRUE),
    -- Income
    ('Salary',             'income',  'briefcase',        TRUE),
    ('Freelance',          'income',  'laptop',           TRUE),
    ('Investment Returns', 'income',  'trending-up',      TRUE),
    ('Rental Income',      'income',  'home',             TRUE),
    ('Other Income',       'income',  'plus-circle',      TRUE);
