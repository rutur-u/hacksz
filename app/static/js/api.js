export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function detailMessage(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg || "Invalid value").join("; ");
  }
  return fallback;
}

export async function request(path, { method = "GET", body } = {}) {
  const options = {
    method,
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);
  let payload = null;
  if (response.status !== 204) {
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
    }
  }
  if (!response.ok) {
    throw new ApiError(
      detailMessage(payload, `Request failed (${response.status})`),
      response.status,
      payload,
    );
  }
  return payload;
}

let mePromise = null;

export function getMe(force = false) {
  if (!mePromise || force) {
    mePromise = request("/api/auth/me").catch((error) => {
      if (error.status === 401) return null;
      mePromise = null;
      throw error;
    });
  }
  return mePromise;
}

export async function refreshMe() {
  const session = await getMe(true);
  window.dispatchEvent(new CustomEvent("auth:changed", { detail: session }));
  return session;
}

export function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      search.set(key, String(value));
    }
  });
  const result = search.toString();
  return result ? `?${result}` : "";
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
}

export function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatTime(value) {
  return String(value ?? "").slice(0, 5);
}

export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export function setBusy(button, busy, busyLabel = "Working…") {
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = busyLabel;
  } else if (button.dataset.label) {
    button.textContent = button.dataset.label;
    delete button.dataset.label;
  }
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

export function state(message, kind = "loading") {
  return `<div class="state state-${kind}" role="${kind === "error" ? "alert" : "status"}">${escapeHtml(message)}</div>`;
}
