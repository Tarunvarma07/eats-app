/**
 * app.js — Shared auth helpers for the EAT System frontend.
 * Loaded by index.html, register.html, setup.html, dashboard.html, admin.html
 */

// Reads from a global config injected by the server, falls back to localhost for dev
const API_BASE = window.APP_CONFIG?.apiBase ?? 'http://localhost:8000';
const API = '';   // same origin — backend serves the frontend

// ── HTML escaping utility (XSS prevention) ─────────────────────────────────────
function escapeHtml(unsafe) {
  if (unsafe === null || unsafe === undefined) return '';
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── Form validation utility ──────────────────────────────────────────────────────
/**
 * Validates a form and shows inline error messages.
 * Returns true if valid, false if not.
 */
function validateForm(fields) {
  let valid = true;
  fields.forEach(({ id, label, rules }) => {
    const input = document.getElementById(id);
    const errorEl = document.getElementById(`${id}-error`);
    const value = input?.value?.trim() ?? '';
    let errorMsg = '';

    if (rules.required && !value) {
      errorMsg = `${label} is required`;
    } else if (rules.email && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      errorMsg = `${label} must be a valid email address`;
    } else if (rules.minLength && value.length < rules.minLength) {
      errorMsg = `${label} must be at least ${rules.minLength} characters`;
    } else if (rules.dateRange && rules.dateRange.start && rules.dateRange.end) {
      if (new Date(rules.dateRange.start) > new Date(rules.dateRange.end)) {
        errorMsg = 'Start date must be before end date';
      }
    }

    if (errorEl) {
      errorEl.textContent = errorMsg;
      errorEl.style.display = errorMsg ? 'block' : 'none';
    }
    if (errorMsg) valid = false;
  });
  return valid;
}

// ── Error/Success display utilities ────────────────────────────────────────────
function showError(message, containerId = 'global-error') {
  const el = document.getElementById(containerId);
  if (el) {
    el.textContent = message;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 5000);
  } else {
    console.error('UI Error:', message);
  }
}

function showSuccess(message, containerId = 'global-success') {
  const el = document.getElementById(containerId);
  if (el) {
    el.textContent = message;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
  }
}

// ── Token storage (localStorage for persistence across page loads) ──
const TOKEN_KEY = 'access_token';
const ROLE_KEY = 'user_role';

function saveToken(token) { localStorage.setItem(TOKEN_KEY, token); }
function getToken()       { return localStorage.getItem(TOKEN_KEY); }
function clearToken()     { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ROLE_KEY); }

// ── JWT payload decode (no verification — just for reading claims) ──────────
function parseJwt(token) {
  try {
    const b64url = token.split('.')[1];
    // Pad to valid base64 length
    const b64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
    return JSON.parse(atob(padded));
  } catch { return null; }
}

// Convenience: get user info from stored token
function currentUser() {
  const t = getToken();
  if (!t) return null;
  return parseJwt(t);   // { user_id, role, name, email, department, exp, jti }
}

// ── Redirect helpers ────────────────────────────────────────────────────────
function requireAuth(redirectTo = '/app/index.html') {
  if (!getToken()) { window.location.href = redirectTo; return false; }
  const p = parseJwt(getToken());
  if (!p) { clearToken(); window.location.href = redirectTo; return false; }
  // Check expiry client-side (server is authoritative, but avoids needless calls)
  if (p.exp && Date.now() / 1000 > p.exp) {
    clearToken(); window.location.href = redirectTo; return false;
  }
  return true;
}

async function redirectIfLoggedIn() {
  const token = getToken();
  if (!token) return;
  
  // Try to validate token with backend to check if it's still valid (not blacklisted)
  try {
    const res = await fetch('/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      // Token is valid, get user role from token and redirect
      const p = parseJwt(token);
      if (p && p.role) {
        window.location.href = p.role === 'admin' ? '/app/admin.html' : '/app/dashboard.html';
      }
    } else {
      // Token is invalid or blacklisted, clear it
      clearToken();
    }
  } catch (e) {
    // If request fails, clear token to be safe
    clearToken();
  }
}

// ── Token refresh ─────────────────────────────────────────────────────────────
async function tryRefresh() {
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include', // sends httpOnly cookie
    });
    if (res.ok) {
      const data = await res.json();
      saveToken(data.access_token); // store in localStorage
      console.log('Token refresh successful');
      return true;
    } else {
      console.error('Token refresh failed:', res.status, res.statusText);
    }
  } catch (e) {
    console.error('Token refresh error:', e);
  }
  return false;
}

// ── API wrapper with automatic token refresh ─────────────────────────────────
async function apiFetch(path, options = {}) {
  // Inject the current access token into the Authorization header
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response = await fetch(API + path, {
    ...options,
    headers,
    credentials: 'include', // sends the httpOnly refresh cookie automatically
  });

  // If 401, try to refresh the access token once (but NOT for login endpoint)
  if (response.status === 401 && !options._retry && !path.includes('/login')) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      // Retry the original request with the new token
      return apiFetch(path, { ...options, _retry: true });
    } else {
      // Refresh failed — send to login
      clearToken();
      window.location.href = '/app/index.html';
      return;
    }
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `Request failed (${response.status})`);
  }

  if (response.status === 204) return null;
  return response.json();
}

// ── On page load, initialize authenticated UI if token exists ────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const token = getToken();
  if (token) {
    // Call page-specific init function if it exists
    if (typeof initAuthenticatedUI === 'function') {
      initAuthenticatedUI();
    }
  }
});

// ── Formatting helpers ───────────────────────────────────────────────────────
function fmtTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata'
  });
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata'
  });
}

function fmtDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    hour12: true, timeZone: 'Asia/Kolkata'
  });
}

// ── Status badge HTML ────────────────────────────────────────────────────────
function statusBadge(status) {
  const map = {
    'Active':     ['badge-active', 'Logged In'],
    'Late':       ['badge-late',   'Late'],
    'Logged Out': ['badge-out',    'Logged Out'],
  };
  const [cls, label] = map[status] || ['badge-out', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

// ── Avatar initials helper ───────────────────────────────────────────────────
function initials(name) {
  return (name || '?').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
}
