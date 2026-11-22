import {
  escapeHtml,
  formatDate,
  getMe,
  refreshMe,
  request,
  setBusy,
  state,
} from "./api.js";

const forms = document.querySelector("#auth-forms");
const account = document.querySelector("#account");
const accountDetails = document.querySelector("#account-details");
const applicationPanel = document.querySelector("#admin-application");
const applicationHistory = document.querySelector("#application-history");
const feedback = document.querySelector("#auth-feedback");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");
const applicationForm = document.querySelector("#application-form");

function optional(value) {
  return value.trim() || null;
}

function showFeedback(message, kind = "success") {
  feedback.innerHTML = message ? state(message, kind) : "";
}

function detailRow(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || "Not provided")}</dd></div>`;
}

function renderAccount(session) {
  const { user } = session;
  const profile = session.student_profile;
  const admin = session.admin_profile;
  const rows = [
    detailRow("Name", user.full_name),
    detailRow("Email", user.email),
    detailRow("Role", user.role),
    detailRow("Account status", user.status),
    detailRow("Member since", formatDate(user.created_at)),
  ];
  if (profile) {
    rows.push(
      detailRow("Student number", profile.student_number),
      detailRow("Faculty", profile.faculty),
      detailRow("Study year", profile.study_year),
      detailRow("Phone", profile.phone),
    );
  }
  if (admin) {
    rows.push(detailRow("Position", admin.position), detailRow("Department", admin.department));
  }
  accountDetails.innerHTML = `<dl class="profile-grid">${rows.join("")}</dl>`;
}

function renderSession(session) {
  const user = session?.user ?? null;
  forms.hidden = Boolean(user);
  account.hidden = !user;
  applicationPanel.hidden = user?.role !== "student";
  if (user) {
    renderAccount(session);
    if (user.role === "student") loadApplications();
  } else {
    applicationHistory.innerHTML = "";
  }
}

async function loadApplications() {
  applicationHistory.innerHTML = state("Loading your applications…");
  try {
    const data = await request("/api/admin-applications/me");
    applicationHistory.innerHTML = data.items.length
      ? data.items.map((item) => `
        <article class="list-row">
          <div class="list-row-main">
            <div class="list-row-title">
              <h4>${escapeHtml(item.requested_position)}</h4>
              <span class="pill pill-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span>
            </div>
            <p>${escapeHtml(item.motivation)}</p>
            <p class="muted">Submitted ${escapeHtml(formatDate(item.created_at))}${item.department ? ` · ${escapeHtml(item.department)}` : ""}</p>
            ${item.decision_note ? `<p><strong>Decision note:</strong> ${escapeHtml(item.decision_note)}</p>` : ""}
          </div>
        </article>`).join("")
      : state("You have not submitted an administrator application.", "empty");
  } catch (error) {
    applicationHistory.innerHTML = state(error.message, "error");
  }
}

async function signOut(button) {
  setBusy(button, true, "Signing out…");
  try {
    await request("/api/auth/logout", { method: "POST" });
    await refreshMe();
    showFeedback("You have been signed out.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = loginForm.querySelector("button[type=submit]");
  const data = new FormData(loginForm);
  setBusy(button, true, "Signing in…");
  showFeedback("");
  try {
    await request("/api/auth/login", {
      method: "POST",
      body: { email: data.get("email"), password: data.get("password") },
    });
    await refreshMe();
    showFeedback("Welcome back. You are now signed in.");
    const next = new URLSearchParams(window.location.search).get("next");
    if (next?.startsWith("/") && !next.startsWith("//")) {
      window.location.assign(next);
    } else {
      account.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = registerForm.querySelector("button[type=submit]");
  const data = new FormData(registerForm);
  const email = data.get("email").trim();
  setBusy(button, true, "Creating account…");
  showFeedback("");
  try {
    await request("/api/auth/register", {
      method: "POST",
      body: {
        email,
        password: data.get("password"),
        full_name: data.get("full_name").trim(),
        student_number: optional(data.get("student_number")),
        faculty: optional(data.get("faculty")),
        study_year: data.get("study_year") ? Number(data.get("study_year")) : null,
        phone: optional(data.get("phone")),
      },
    });
    registerForm.reset();
    document.querySelector("#login-email").value = email;
    showFeedback("Your account is ready. Sign in with your new password.");
    window.location.hash = "login";
    document.querySelector("#login-password").focus();
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

applicationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = applicationForm.querySelector("button[type=submit]");
  const data = new FormData(applicationForm);
  setBusy(button, true, "Submitting…");
  showFeedback("");
  try {
    await request("/api/admin-applications", {
      method: "POST",
      body: {
        requested_position: data.get("requested_position").trim(),
        department: optional(data.get("department")),
        motivation: data.get("motivation").trim(),
      },
    });
    applicationForm.reset();
    showFeedback("Your administrator application has been submitted.");
    await loadApplications();
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

document.querySelector("#account-logout").addEventListener("click", (event) => {
  signOut(event.currentTarget);
});

window.addEventListener("auth:changed", (event) => renderSession(event.detail));
getMe().then(renderSession).catch((error) => {
  forms.hidden = false;
  showFeedback(error.message, "error");
});
