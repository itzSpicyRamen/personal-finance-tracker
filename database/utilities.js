const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

//Registration route
app.post('/register', async (req, res) => {
  const { email, password } = req.body;
  const hashedPassword = await bcrypt.hash(password, 10);
  const query = 'INSERT INTO users(email, password) VALUES($1, $2) RETURNING *';
  try {
    const result = await pool.query(query, [email, hashedPassword]);
    res.status(201).send('User created');
  } catch (err) {
    res.status(400).send('Error creating user');
  }
});

//Login route
app.post('/login', async (req, res) => {
  const { email, password } = req.body;
  const query = 'SELECT * FROM users WHERE email = $1';
  try {
    const result = await pool.query(query, [email]);
    const user = result.rows[0];

    if (!user || !(await bcrypt.compare(password, user.password))) {
      return res.status(400).send('Invalid credentials');
    }

    const token = jwt.sign({ userId: user.id }, process.env.JWT_SECRET, { expiresIn: '1h' });
    res.json({ token });
  } catch (err) {
    res.status(400).send('Error logging in');
  }
});

// Add transaction
app.post('/transactions', async (req, res) => {
    const { userId, amount, category, type } = req.body;
    const query = 'INSERT INTO transactions(user_id, amount, category, type) VALUES($1, $2, $3, $4) RETURNING *';
    try {
      const result = await pool.query(query, [userId, amount, category, type]);
      res.status(201).json(result.rows[0]);
    } catch (err) {
      res.status(400).send('Error adding transaction');
    }
  });

  // Set budget
app.post('/budgets', async (req, res) => {
    const { userId, category, amount, month, year } = req.body;
    const query = 'INSERT INTO budgets(user_id, category, amount, month, year) VALUES($1, $2, $3, $4, $5) RETURNING *';
    try {
      const result = await pool.query(query, [userId, category, amount, month, year]);
      res.status(201).json(result.rows[0]);
    } catch (err) {
      res.status(400).send('Error setting budget');
    }
  });