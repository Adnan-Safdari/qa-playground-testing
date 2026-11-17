// SecureBank data layer — all bank state lives in the browser.
//
//   localStorage   "securebank:db:v1"    users, accounts, transactions
//   localStorage   "securebank:remember" remembered username ("Remember me")
//   sessionStorage "securebank:session"  logged-in username
//
// Money is stored as integer cents to keep balance arithmetic exact.
// All validation lives here so every page enforces the same business rules.

const DB_KEY = "securebank:db:v1";
const SESSION_KEY = "securebank:session";
const REMEMBER_KEY = "securebank:remember";

export const MIN_OPENING_DEPOSIT_CENTS = 2500; // $25.00
export const MAX_OPENING_DEPOSIT_CENTS = 10000000; // $100,000.00
export const MAX_TRANSFER_CENTS = 1000000; // $10,000.00 per transfer
export const SLOW_USER_DELAY_MS = 2500;

export const ACCOUNT_TYPES = [
  { value: "checking", label: "Checking" },
  { value: "savings", label: "Savings" },
];

// Shown on the login page. Every user here has implemented behaviour.
// (Customers created via /bank/register log in with their email as username.)
export const TEST_USERS = [
  { username: "standard_user", password: "bank_sauce", description: "Full access" },
  { username: "locked_user", password: "bank_sauce", description: "Locked account" },
  { username: "frozen_user", password: "bank_sauce", description: "Frozen — no transfers" },
  { username: "overdraft_user", password: "bank_sauce", description: "Negative balance" },
  { username: "slow_user", password: "bank_sauce", description: "Slow loading" },
];

// ─── Seed data ──────────────────────────────────────────────────────────────

const SEED_USERS = [
  {
    username: "standard_user",
    profile: {
      fullName: "Alex Morgan",
      email: "alex.morgan@example.com",
      phone: "+1 555 010 2030",
      address: "42 Market Street, Springfield",
    },
    accounts: [
      { number: "1002003001", type: "checking", nickname: "Everyday Checking", balance: 1245000 },
      { number: "1002003002", type: "savings", nickname: "High-Yield Savings", balance: 460000 },
    ],
  },
  {
    username: "locked_user",
    locked: true,
    profile: {
      fullName: "Jordan Lee",
      email: "jordan.lee@example.com",
      phone: "+1 555 010 4040",
      address: "7 Harbor Road, Riverton",
    },
    accounts: [{ number: "1002004001", type: "checking", nickname: "Everyday Checking", balance: 320000 }],
  },
  {
    username: "frozen_user",
    frozen: true,
    profile: {
      fullName: "Sam Rivera",
      email: "sam.rivera@example.com",
      phone: "+1 555 010 5050",
      address: "15 Oak Avenue, Lakeside",
    },
    accounts: [
      { number: "1002005001", type: "checking", nickname: "Everyday Checking", balance: 540000 },
      { number: "1002005002", type: "savings", nickname: "Rainy Day Savings", balance: 210000 },
    ],
  },
  {
    username: "overdraft_user",
    profile: {
      fullName: "Casey Kim",
      email: "casey.kim@example.com",
      phone: "+1 555 010 6060",
      address: "88 Pine Lane, Fairview",
    },
    accounts: [
      { number: "1002006001", type: "checking", nickname: "Everyday Checking", balance: -25000 },
      { number: "1002006002", type: "savings", nickname: "Emergency Savings", balance: 8000 },
    ],
  },
  {
    username: "slow_user",
    slow: true,
    profile: {
      fullName: "Taylor Brooks",
      email: "taylor.brooks@example.com",
      phone: "+1 555 010 7070",
      address: "3 Elm Court, Brookfield",
    },
    accounts: [
      { number: "1002007001", type: "checking", nickname: "Everyday Checking", balance: 730000 },
      { number: "1002007002", type: "savings", nickname: "Vacation Savings", balance: 150000 },
    ],
  },
];

// History applied to each user's first (checking) account, oldest first.
const SEED_HISTORY = [
  { date: "2026-10-01T09:00:00.000Z", description: "Direct Deposit — ACME Corp", category: "Income", amount: 320000 },
  { date: "2026-10-03T14:12:00.000Z", description: "Amazon.com", category: "Shopping", amount: -5699 },
  { date: "2026-10-05T08:30:00.000Z", description: "City Electric Co.", category: "Utilities", amount: -12450 },
  { date: "2026-10-08T18:45:00.000Z", description: "Whole Foods Market", category: "Groceries", amount: -8432 },
];

function buildSeedDb() {
  const db = { version: 1, users: {}, accounts: [], transactions: [], seq: { account: 9000000, txn: 100000 } };

  for (const seed of SEED_USERS) {
    db.users[seed.username] = {
      username: seed.username,
      password: TEST_USERS.find((u) => u.username === seed.username).password,
      locked: Boolean(seed.locked),
      frozen: Boolean(seed.frozen),
      slow: Boolean(seed.slow),
      profile: { ...seed.profile },
    };

    seed.accounts.forEach((a, i) => {
      const account = {
        id: `acc_${a.number}`,
        owner: seed.username,
        number: a.number,
        type: a.type,
        nickname: a.nickname,
        balance: a.balance,
        openedAt: "2025-01-15T10:00:00.000Z",
      };
      db.accounts.push(account);

      if (i === 0) {
        // Work backwards from the seeded closing balance to get balanceAfter values.
        let running = a.balance - SEED_HISTORY.reduce((sum, h) => sum + h.amount, 0);
        for (const h of SEED_HISTORY) {
          running += h.amount;
          db.transactions.push(makeTxn(db, { ...h, owner: seed.username, accountId: account.id, balanceAfter: running }));
        }
      }
    });
  }
  return db;
}

function makeTxn(db, { owner, accountId, date, description, category, amount, balanceAfter, reference = null }) {
  db.seq.txn += 1;
  return {
    id: `TXN${db.seq.txn}`,
    owner,
    accountId,
    accountNumber: accountId.replace(/^acc_/, ""),
    date: date || new Date().toISOString(),
    description,
    category,
    amount,
    balanceAfter,
    reference,
  };
}

// ─── Persistence ────────────────────────────────────────────────────────────

function hasStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function loadDb() {
  if (!hasStorage()) return buildSeedDb();
  try {
    const raw = localStorage.getItem(DB_KEY);
    if (raw) {
      const db = JSON.parse(raw);
      if (db && db.version === 1) return db;
    }
  } catch {
    // corrupted data — fall through and reseed
  }
  const db = buildSeedDb();
  saveDb(db);
  return db;
}

function saveDb(db) {
  if (hasStorage()) localStorage.setItem(DB_KEY, JSON.stringify(db));
  notify();
}

// ─── Change subscription (for React's useSyncExternalStore) ─────────────────

const listeners = new Set();

function notify() {
  listeners.forEach((listener) => listener());
}

export function subscribe(listener) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/** Raw JSON string of the database (stable between changes, safe as a snapshot). */
export function getDbSnapshot() {
  if (!hasStorage()) return null;
  return localStorage.getItem(DB_KEY) ?? (loadDb(), localStorage.getItem(DB_KEY));
}

/** Clears ALL browser storage for the app origin and reseeds the demo data. */
export function resetDemoData() {
  if (!hasStorage()) return;
  localStorage.clear();
  sessionStorage.clear();
  loadDb();
  notify();
}

// ─── Session ────────────────────────────────────────────────────────────────

export function getSessionUsername() {
  if (!hasStorage()) return null;
  const username = sessionStorage.getItem(SESSION_KEY);
  if (!username) return null;
  const user = loadDb().users[username];
  return user && !user.locked ? username : null;
}

function startSession(username) {
  sessionStorage.setItem(SESSION_KEY, username);
}

export function logout() {
  if (hasStorage()) sessionStorage.removeItem(SESSION_KEY);
  notify();
}

export function getRememberedUsername() {
  return hasStorage() ? localStorage.getItem(REMEMBER_KEY) || "" : "";
}

/** Finds a user by username (exact or case-insensitive) or by profile email (case-insensitive). */
function findUserByLogin(db, identifier) {
  if (db.users[identifier]) return db.users[identifier];
  const lower = identifier.toLowerCase();
  return (
    Object.values(db.users).find((u) => u.username.toLowerCase() === lower) ||
    Object.values(db.users).find((u) => (u.profile.email || "").toLowerCase() === lower) ||
    null
  );
}

/** Login accepts a username or an email address. */
export function login(username, password, rememberMe = false) {
  const errors = {};
  const identifier = (username || "").trim();
  if (!identifier) errors.username = "Username is required.";
  if (!password) errors.password = "Password is required.";
  if (Object.keys(errors).length) return { ok: false, errors };

  const user = findUserByLogin(loadDb(), identifier);
  if (!user || user.password !== password) {
    return { ok: false, errors: { form: "Invalid username or password." } };
  }
  if (user.locked) {
    return { ok: false, errors: { form: "Your account has been locked. Please contact support." } };
  }

  startSession(user.username);
  if (rememberMe) localStorage.setItem(REMEMBER_KEY, identifier);
  else localStorage.removeItem(REMEMBER_KEY);
  notify();
  return { ok: true, username: user.username };
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function getUser(username) {
  const user = loadDb().users[username];
  if (!user) return null;
  const { password: _password, ...safe } = user;
  return safe;
}

export function getAccounts(username) {
  return loadDb().accounts.filter((a) => a.owner === username);
}

export function compareTransactionsNewestFirst(a, b) {
  if (a.date !== b.date) return a.date < b.date ? 1 : -1;
  return Number(b.id.replace(/\D/g, "")) - Number(a.id.replace(/\D/g, ""));
}

export function getTransactions(username, { accountNumber } = {}) {
  return loadDb()
    .transactions.filter((t) => t.owner === username && (!accountNumber || t.accountNumber === accountNumber))
    .sort(compareTransactionsNewestFirst);
}

/**
 * Dashboard figures. Net worth = sum of balances. Income / expenses / net change
 * cover the current calendar month and exclude category "Transfer".
 */
export function summarizeFinances(accounts, transactions, now = new Date()) {
  const netWorth = accounts.reduce((sum, a) => sum + a.balance, 0);
  let income = 0;
  let expenses = 0;
  for (const t of transactions) {
    if (t.category === "Transfer") continue;
    const d = new Date(t.date);
    if (d.getFullYear() !== now.getFullYear() || d.getMonth() !== now.getMonth()) continue;
    if (t.amount > 0) income += t.amount;
    else expenses += t.amount;
  }
  return { netWorth, income, expenses, netChange: income + expenses, accountCount: accounts.length };
}

// ─── Money helpers ──────────────────────────────────────────────────────────

const MONEY_RE = /^\d{1,12}(\.\d{1,2})?$/;

/** Parses "1,234.5" style input into cents. Returns null when not a valid non-negative amount. */
export function parseAmountToCents(input) {
  const s = String(input ?? "").trim().replace(/,/g, "");
  if (!MONEY_RE.test(s)) return null;
  const [whole, frac = ""] = s.split(".");
  return Number(whole) * 100 + Number(frac.padEnd(2, "0"));
}

export function formatMoney(cents, { signed = false } = {}) {
  const value = Math.abs(cents) / 100;
  const text = value.toLocaleString("en-US", { style: "currency", currency: "USD" });
  if (cents < 0) return `-${text}`;
  return signed && cents > 0 ? `+${text}` : text;
}

export function maskAccountNumber(number) {
  return `•••• ${String(number).slice(-4)}`;
}

// ─── Shared validators ──────────────────────────────────────────────────────

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validateFullName(raw) {
  const name = (raw || "").trim();
  if (!name) return "Full name is required.";
  if (name.length < 2 || name.length > 50) return "Full name must be 2–50 characters.";
  if (!/^[A-Za-z][A-Za-z .'-]*$/.test(name)) return "Full name can only contain letters, spaces, . ' and -.";
  return null;
}

/** True when the email is already used (as a profile email or as a username) by someone other than `exceptUsername`. */
function emailTaken(db, email, exceptUsername = null) {
  const lower = email.toLowerCase();
  return Object.values(db.users).some(
    (u) => u.username !== exceptUsername && ((u.profile.email || "").toLowerCase() === lower || u.username.toLowerCase() === lower),
  );
}

function validateEmail(db, raw, exceptUsername = null) {
  const email = (raw || "").trim();
  if (!email) return "Email is required.";
  if (!EMAIL_RE.test(email)) return "Enter a valid email address.";
  if (emailTaken(db, email, exceptUsername)) return "An account already exists with this email.";
  return null;
}

/** Shared password-strength rule (register + change password). */
function validatePasswordStrength(password) {
  if (password.length < 8) return "Password must be at least 8 characters.";
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return "Password must contain at least one letter and one number.";
  return null;
}

/** Initial deposit for register / open account. Returns { cents } or { error }. */
function validateInitialDeposit(raw) {
  const trimmed = String(raw ?? "").trim();
  if (!trimmed) return { error: "Initial deposit is required." };
  const cents = parseAmountToCents(trimmed);
  if (cents === null) return { error: "Enter a valid amount." };
  if (cents < MIN_OPENING_DEPOSIT_CENTS) return { error: `Minimum initial deposit is ${formatMoney(MIN_OPENING_DEPOSIT_CENTS)}.` };
  if (cents > MAX_OPENING_DEPOSIT_CENTS) return { error: `Maximum initial deposit is ${formatMoney(MAX_OPENING_DEPOSIT_CENTS)}.` };
  return { cents };
}

/** Transfer amount. Returns { cents } or { error }. */
function validateTransferAmount(raw) {
  const trimmed = String(raw ?? "").trim();
  if (!trimmed) return { error: "Amount is required." };
  const cents = parseAmountToCents(trimmed);
  if (cents === null) return { error: "Enter a valid amount." };
  if (cents === 0) return { error: "Amount must be greater than zero." };
  return { cents };
}

function createAccount(db, { owner, type, nickname, cents }) {
  db.seq.account += 1;
  const number = `100${db.seq.account}`;
  const account = {
    id: `acc_${number}`,
    owner,
    number,
    type,
    nickname,
    balance: cents,
    openedAt: new Date().toISOString(),
  };
  db.accounts.push(account);
  db.transactions.push(
    makeTxn(db, { owner, accountId: account.id, description: "Opening deposit", category: "Deposit", amount: cents, balanceAfter: cents }),
  );
  return account;
}

// ─── Commands ───────────────────────────────────────────────────────────────

/**
 * Public sign-up. Username = lower-cased email. Creates one "Everyday Checking"
 * account funded with the initial deposit and logs the new customer in.
 */
export function registerCustomer({ fullName, email, password, initialDeposit }) {
  const db = loadDb();
  const errors = {};

  const nameError = validateFullName(fullName);
  if (nameError) errors.fullName = nameError;

  const emailError = validateEmail(db, email);
  if (emailError) errors.email = emailError;

  if (!password) errors.password = "Password is required.";
  else {
    const pwError = validatePasswordStrength(password);
    if (pwError) errors.password = pwError;
  }

  const deposit = validateInitialDeposit(initialDeposit);
  if (deposit.error) errors.initialDeposit = deposit.error;

  if (Object.keys(errors).length) return { ok: false, errors };

  const cleanEmail = email.trim();
  const username = cleanEmail.toLowerCase();
  db.users[username] = {
    username,
    password,
    locked: false,
    frozen: false,
    slow: false,
    profile: { fullName: fullName.trim(), email: cleanEmail, phone: "", address: "" },
  };
  const account = createAccount(db, { owner: username, type: "checking", nickname: "Everyday Checking", cents: deposit.cents });
  saveDb(db);
  startSession(username);
  notify();
  return { ok: true, username, account: { ...account } };
}

export function openAccount(username, { type, nickname, initialDeposit, acceptTerms }) {
  const db = loadDb();
  const errors = {};
  const name = (nickname || "").trim();

  if (!ACCOUNT_TYPES.some((t) => t.value === type)) errors.type = "Select an account type.";

  if (!name) errors.nickname = "Account nickname is required.";
  else if (name.length < 3 || name.length > 30) errors.nickname = "Nickname must be 3–30 characters.";
  else if (db.accounts.some((a) => a.owner === username && a.nickname.toLowerCase() === name.toLowerCase())) {
    errors.nickname = "You already have an account with this nickname.";
  }

  const deposit = validateInitialDeposit(initialDeposit);
  if (deposit.error) errors.initialDeposit = deposit.error;

  if (!acceptTerms) errors.acceptTerms = "You must accept the terms and conditions.";
  if (Object.keys(errors).length) return { ok: false, errors };

  const account = createAccount(db, { owner: username, type, nickname: name, cents: deposit.cents });
  saveDb(db);
  return { ok: true, account: { ...account } };
}

/**
 * Moves money from one of the user's accounts to ANY customer's account number.
 * Both rows share one TRF reference; the recipient row belongs to the recipient.
 */
export function transferFunds(username, { fromAccountNumber, toAccountNumber, amount, memo }) {
  const db = loadDb();
  const user = db.users[username];
  const errors = {};

  if (user?.frozen) {
    return { ok: false, errors: { form: "Your accounts are frozen. Transfers are disabled — please contact support." } };
  }

  const from = db.accounts.find((a) => a.number === fromAccountNumber && a.owner === username);
  if (!from) errors.fromAccount = "Select the account to transfer from.";

  const toNumber = String(toAccountNumber ?? "").trim();
  const to = toNumber ? db.accounts.find((a) => a.number === toNumber) : null;
  if (!toNumber) errors.toAccount = "Recipient account number is required.";
  else if (!to) errors.toAccount = "Recipient account not found.";
  else if (from && from.number === to.number) errors.toAccount = "You cannot transfer to the same account.";

  const note = (memo || "").trim();
  if (note.length > 50) errors.memo = "Memo must be 50 characters or fewer.";

  const parsed = validateTransferAmount(amount);
  if (parsed.error) errors.amount = parsed.error;
  else if (parsed.cents > MAX_TRANSFER_CENTS) errors.amount = `Transfers are limited to ${formatMoney(MAX_TRANSFER_CENTS)} per transaction.`;
  else if (from && parsed.cents > from.balance) errors.amount = "Insufficient balance.";

  if (Object.keys(errors).length) return { ok: false, errors };

  const cents = parsed.cents;
  db.seq.txn += 1;
  const reference = `TRF${db.seq.txn}`;
  from.balance -= cents;
  to.balance += cents;
  const now = new Date().toISOString();
  const suffix = note ? ` — ${note}` : "";
  db.transactions.push(
    makeTxn(db, { owner: from.owner, accountId: from.id, date: now, description: `Transfer to ${to.number}${suffix}`, category: "Transfer", amount: -cents, balanceAfter: from.balance, reference }),
    makeTxn(db, { owner: to.owner, accountId: to.id, date: now, description: `Transfer from ${from.number}${suffix}`, category: "Transfer", amount: cents, balanceAfter: to.balance, reference }),
  );
  saveDb(db);
  return { ok: true, reference, amount: cents, from: { ...from }, to: { number: to.number } };
}

export function updateProfile(username, { fullName, email, phone, address }) {
  const db = loadDb();
  const user = db.users[username];
  const errors = {};
  const next = {
    fullName: (fullName || "").trim(),
    email: (email || "").trim(),
    phone: (phone || "").trim(),
    address: (address || "").trim(),
  };

  const nameError = validateFullName(next.fullName);
  if (nameError) errors.fullName = nameError;

  const emailError = validateEmail(db, next.email, username);
  if (emailError) errors.email = emailError;

  const digits = next.phone.replace(/\D/g, "");
  if (!next.phone) errors.phone = "Phone number is required.";
  else if (!/^\+?[0-9 ()-]+$/.test(next.phone) || digits.length < 10 || digits.length > 15) {
    errors.phone = "Enter a valid phone number (10–15 digits).";
  }

  if (next.address.length > 100) errors.address = "Address must be 100 characters or fewer.";
  if (Object.keys(errors).length) return { ok: false, errors };

  user.profile = next;
  saveDb(db);
  return { ok: true, profile: next };
}

export function changePassword(username, { currentPassword, newPassword, confirmPassword }) {
  const db = loadDb();
  const user = db.users[username];
  const errors = {};

  if (!currentPassword) errors.currentPassword = "Current password is required.";
  else if (currentPassword !== user.password) errors.currentPassword = "Current password is incorrect.";

  if (!newPassword) errors.newPassword = "New password is required.";
  else if (newPassword === currentPassword) errors.newPassword = "New password must be different from the current password.";
  else {
    const pwError = validatePasswordStrength(newPassword);
    if (pwError) errors.newPassword = pwError;
  }

  if (!confirmPassword) errors.confirmPassword = "Please confirm the new password.";
  else if (newPassword && confirmPassword !== newPassword) errors.confirmPassword = "Passwords do not match.";

  if (Object.keys(errors).length) return { ok: false, errors };

  user.password = newPassword;
  saveDb(db);
  return { ok: true };
}
