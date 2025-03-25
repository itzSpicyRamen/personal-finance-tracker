-- Note: tables subject to change, current tables for initial setup --

-- Users Table --
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL
);

-- Categories Table --
CREATE TABLE categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL
);

-- Transactions Table --
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  amount DECIMAL(10, 2) NOT NULL,
  category_id INT REFERENCES categories(id),
  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  type VARCHAR(50) CHECK (type IN ('income', 'expense'))
);

-- Budgets Table --
CREATE TABLE budgets (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  category_id INT REFERENCES categories(id),
  amount DECIMAL(10, 2) NOT NULL,
  month INT,
  year INT
);
