import {
  WEEKDAYS,
  escapeHtml,
  formatTime,
  getMe,
  request,
  setBusy,
  state,
} from "./api.js";

const page = document.querySelector("[data-class-id]");
const mount = document.querySelector("#class-detail");
const classId = Number(page.dataset.classId);
let course = null;
let session = null;
let membership = null;
let roleUnavailable = false;
let joinMessage = "";

function joinArea() {
  const next = encodeURIComponent(`/classes/${classId}`);
  if (!session?.user) {
    return `<a class="btn btn-primary" href="/register?next=${next}#login">Sign in to join</a>`;
  }
  if (membership) {
    return state(`You joined this class as a ${membership.role}.`, "success");
  }
  if (roleUnavailable) {
    return state("You already have a role in this class. The exact role is not available from this public endpoint.", "info");
  }
  if (course.status !== "published") {
    return state("This class is not open for joining.", "info");
  }
  return `
    ${joinMessage ? state(joinMessage, "error") : ""}
    <button class="btn btn-primary" type="button" data-join-class>Join as visitor</button>
    <p class="muted join-note">Joining gives you visitor access. Class staff can promote visitors to members.</p>`;
}

function render() {
  const meetings = [...course.meetings].sort((a, b) =>
    a.weekday - b.weekday || a.start_time.localeCompare(b.start_time));
  mount.innerHTML = `
    <article class="class-detail-card">
      <header class="class-detail-header">
        <div>
          <p class="eyebrow">${escapeHtml(course.code)}${course.category ? ` · ${escapeHtml(course.category)}` : ""}</p>
          <h1>${escapeHtml(course.title)}</h1>
          <p class="lead">Led by ${escapeHtml(course.teacher_name)}</p>
        </div>
        <span class="pill pill-${escapeHtml(course.status)}">${escapeHtml(course.status)}</span>
      </header>
      <div class="class-detail-body">
        <section aria-labelledby="about-class">
          <h2 id="about-class">About this class</h2>
          <p class="pre-line">${escapeHtml(course.description || "No description has been added yet.")}</p>
          <p class="muted">${course.capacity ? `Class capacity: ${course.capacity}` : "No fixed class capacity"}</p>
        </section>
        <aside class="join-panel" aria-label="Join this class">
          <h2>Take part</h2>
          ${joinArea()}
        </aside>
      </div>
      <section class="meeting-section" aria-labelledby="meeting-title">
        <h2 id="meeting-title">Weekly meetings</h2>
        ${meetings.length ? `
          <ul class="schedule-list">
            ${meetings.map((meeting) => `
              <li>
                <strong>${escapeHtml(WEEKDAYS[meeting.weekday])}</strong>
                <span>${escapeHtml(formatTime(meeting.start_time))}–${escapeHtml(formatTime(meeting.end_time))}</span>
                <span>${escapeHtml(meeting.room || "Room to be announced")}</span>
                ${meeting.audience === "members" ? "<span class=\"pill\">Members only</span>" : ""}
                ${meeting.note ? `<p class="muted">${escapeHtml(meeting.note)}</p>` : ""}
              </li>`).join("")}
          </ul>` : state("No weekly meeting slots are visible to you.", "empty")}
      </section>
    </article>`;
  document.title = `${course.title} · Campus Extra Classes`;
}

async function join(button) {
  setBusy(button, true, "Joining…");
  joinMessage = "";
  try {
    membership = await request(`/api/classes/${classId}/membership`, { method: "POST" });
  } catch (error) {
    if (error.status === 409 && error.message.includes("already have a role")) {
      roleUnavailable = true;
    } else {
      joinMessage = error.message;
    }
  }
  render();
}

mount.addEventListener("click", (event) => {
  const button = event.target.closest("[data-join-class]");
  if (button) join(button);
});

async function load() {
  mount.innerHTML = state("Loading class details…");
  const [courseResult, sessionResult] = await Promise.allSettled([
    request(`/api/classes/${classId}`),
    getMe(),
  ]);
  if (courseResult.status === "rejected") {
    mount.innerHTML = `${state(courseResult.reason.message, "error")}
      <a class="btn btn-ghost" href="/classes">Return to the catalogue</a>`;
    return;
  }
  course = courseResult.value;
  session = sessionResult.status === "fulfilled" ? sessionResult.value : null;
  render();
}

window.addEventListener("auth:changed", (event) => {
  session = event.detail;
  membership = null;
  roleUnavailable = false;
  if (course) render();
});

load();
