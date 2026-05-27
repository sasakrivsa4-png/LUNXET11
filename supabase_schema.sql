-- ============================================
-- Виконай це в Supabase → SQL Editor → Run
-- ============================================

-- 1. Товари
CREATE TABLE products (
  id          SERIAL PRIMARY KEY,
  name        TEXT    NOT NULL,
  price       INTEGER NOT NULL,
  description TEXT    DEFAULT '',
  category    TEXT    DEFAULT '',
  sizes       TEXT[]  DEFAULT '{}',
  images      TEXT[]  DEFAULT '{}',
  active      BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Коди авторизації (тимчасові)
CREATE TABLE auth_codes (
  id         SERIAL PRIMARY KEY,
  contact    TEXT NOT NULL,
  code       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Користувачі
CREATE TABLE users (
  id         SERIAL PRIMARY KEY,
  contact    TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Замовлення
CREATE TABLE orders (
  id           SERIAL PRIMARY KEY,
  order_uid    TEXT NOT NULL,
  user_contact TEXT DEFAULT 'guest',
  items        JSONB DEFAULT '[]',
  total        INTEGER DEFAULT 0,
  address      TEXT DEFAULT '',
  status       TEXT DEFAULT 'new',
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Дозволи (щоб API міг читати/писати)
-- ============================================
ALTER TABLE products   ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE users      ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders     ENABLE ROW LEVEL SECURITY;

-- Products: публічне читання, запис тільки через service_role
CREATE POLICY "read products" ON products FOR SELECT USING (true);
CREATE POLICY "write products" ON products FOR ALL USING (auth.role() = 'service_role');

-- Решта тільки через service_role
CREATE POLICY "auth_codes all" ON auth_codes FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "users all"      ON users      FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "orders all"     ON orders     FOR ALL USING (auth.role() = 'service_role');
