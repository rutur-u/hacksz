import { getMe, refreshMe, request, setBusy } from "./api.js";

const guestAction = document.querySelector("[data-guest-action]");
const userAction = document.querySelector("[data-user-action]");
const userName = document.querySelector("[data-user-name]");
const staffLink = document.querySelector("[data-staff-link]");
const logoutButton = document.querySelector("[data-logout]");

function renderSession(session) {
  const user = session?.user ?? null;
  const isStaff = user?.role === "admin" || user?.role === "superadmin";
  if (staffLink) staffLink.hidden = !isStaff;
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
