/**
 * Must match backend (api/auth.py): min 8 chars, upper, lower, digit, special.
 */
const MIN_LEN = 8;
const RE_UPPER = /[A-Z]/;
const RE_LOWER = /[a-z]/;
const RE_DIGIT = /\d/;
const RE_SPECIAL = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/;

export const PASSWORD_REQUIREMENTS = [
  `At least ${MIN_LEN} characters`,
  'One uppercase letter',
  'One lowercase letter',
  'One digit',
  'One special character (!@#$%^&*...)',
];

export function validatePassword(password) {
  if (!password || password.length < MIN_LEN) return { ok: false, message: `Password must be at least ${MIN_LEN} characters` };
  if (!RE_UPPER.test(password)) return { ok: false, message: 'Password must contain at least one uppercase letter' };
  if (!RE_LOWER.test(password)) return { ok: false, message: 'Password must contain at least one lowercase letter' };
  if (!RE_DIGIT.test(password)) return { ok: false, message: 'Password must contain at least one digit' };
  if (!RE_SPECIAL.test(password)) return { ok: false, message: 'Password must contain at least one special character' };
  return { ok: true };
}
