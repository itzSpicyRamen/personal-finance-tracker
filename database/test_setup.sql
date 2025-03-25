-- Insert a test user
INSERT INTO users (email, password) VALUES ('user@example.com', 'hashed_password');

-- Insert categories
INSERT INTO categories (name) VALUES ('Groceries'), ('Salary'), ('Entertainment');

-- Insert transactions
INSERT INTO transactions (user_id, amount, category_id, type)
VALUES (1, 50.00, 1, 'expense'), (1, 2000.00, 2, 'income');

-- Insert a budget
INSERT INTO budgets (user_id, category_id, amount, month, year)
VALUES (1, 1, 300.00, 3, 2025);

SELECT * FROM users;
SELECT * FROM categories;
SELECT * FROM transactions;
SELECT * FROM budgets;