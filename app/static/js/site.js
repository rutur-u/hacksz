import { getMe, refreshMe, request, setBusy } from "./api.js";

const guestAction = document.querySelector("[data-guest-action]");
const userAction = document.querySelector("[data-user-action]");
const userName = document.querySelector("[data-user-name]");
const staffLink = document.querySelector("[data-staff-link]");
const userLink = document.querySelector("[data-user-link]");
const logoutButton = document.querySelector("[data-logout]");
const themeToggle = document.querySelector("[data-theme-toggle]");
const navToggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle?.setAttribute("aria-pressed", String(theme === "dark"));
  themeToggle?.setAttribute(
    "aria-label",
    theme === "dark" ? "切换到浅色模式" : "切换到深色模式",
  );
}

applyTheme(document.documentElement.dataset.theme || "light");

themeToggle?.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem("theme", next);
  } catch (error) {
    // Storage can be unavailable in private mode; the theme still applies.
  }
});

function closeNav() {
  if (!nav || !navToggle) return;
  nav.classList.remove("is-open");
  navToggle.setAttribute("aria-expanded", "false");
  navToggle.setAttribute("aria-label", "打开导航菜单");
}

navToggle?.addEventListener("click", () => {
  if (!nav) return;
  const open = nav.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", String(open));
  navToggle.setAttribute("aria-label", open ? "关闭导航菜单" : "打开导航菜单");
});

nav?.addEventListener("click", (event) => {
  if (event.target.closest("a")) closeNav();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeNav();
});

window.matchMedia("(min-width: 861px)").addEventListener("change", (event) => {
  if (event.matches) closeNav();
});

function renderSession(session) {
  const user = session?.user ?? null;
  const isStaff = user?.role === "admin" || user?.role === "superadmin";
  if (staffLink) staffLink.hidden = !isStaff;
  if (userLink) userLink.hidden = !user;
  if (guestAction) guestAction.hidden = Boolean(user);
  if (userAction) userAction.hidden = !user;
  if (userName && user) {
    userName.textContent = user.full_name;
    userName.title = `${user.full_name} · ${user.email}`;
  }
}

getMe().then(renderSession).catch(() => renderSession(null));
window.addEventListener("auth:changed", (event) => renderSession(event.detail));

logoutButton?.addEventListener("click", async () => {
  setBusy(logoutButton, true, "Signing out…");
  try {
    await request("/api/auth/logout", { method: "POST" });
    await refreshMe();
    if (document.querySelector("[data-admin-page]")) window.location.href = "/";
  } catch (error) {
    logoutButton.title = error.message;
  } finally {
    setBusy(logoutButton, false);
  }
});
