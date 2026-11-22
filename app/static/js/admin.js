import {
  WEEKDAYS,
  escapeHtml,
  formatDate,
  formatTime,
  getMe,
  query,
  request,
  setBusy,
  state,
} from "./api.js";

const access = document.querySelector("#admin-access");
const workspace = document.querySelector("#admin-workspace");
const feedback = document.querySelector("#admin-feedback");
const classSelect = document.querySelector("#admin-class-select");
const classList = document.querySelector("#admin-class-list");
const classForm = document.querySelector("#class-form");
const meetingForm = document.querySelector("#meeting-form");
const meetingList = document.querySelector("#meeting-list");
const membershipList = document.querySelector("#membership-list");
const newsForm = document.querySelector("#news-form");
const newsList = document.querySelector("#news-list");
const studentList = document.querySelector("#student-list");
const applicationList = document.querySelector("#admin-application-list");
const adminDirectory = document.querySelector("#admin-directory");

let currentUser = null;
let isSuperadmin = false;
let classes = [];
let newsItems = [];
let selectedClassId = null;
let membershipSequence = 0;

function optional(value) {
  return value.trim() || null;
}

function showFeedback(message, kind = "success") {
  feedback.innerHTML = message ? state(message, kind) : "";
}

function selectedClass() {
  return classes.find((course) => course.id === selectedClassId) ?? null;
}

function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const active = button.dataset.tab === name;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== name;
  });
  if (name === "members") loadMemberships();
}

function renderClassOptions() {
  const options = classes.map((course) =>
    `<option value="${course.id}">${escapeHtml(course.title)} (${escapeHtml(course.code)})</option>`).join("");
  classSelect.innerHTML = options || '<option value="">No classes available</option>';
  classSelect.disabled = !classes.length;
  classSelect.value = selectedClassId ? String(selectedClassId) : "";

  const newsClass = newsForm.elements.class_id;
  const selected = newsClass.value;
  newsClass.innerHTML = `<option value="">No related class</option>${options}`;
  newsClass.value = selected;
}

function renderClasses() {
  classList.innerHTML = classes.length ? classes.map((course) => `
    <article class="list-row${course.id === selectedClassId ? " is-selected" : ""}" data-class-row="${course.id}">
      <div class="list-row-main">
        <div class="list-row-title">
          <h3>${escapeHtml(course.title)}</h3>
          <span class="pill pill-${escapeHtml(course.status)}">${escapeHtml(course.status)}</span>
        </div>
        <p class="muted">${escapeHtml(course.code)} · ${escapeHtml(course.teacher_name)}${course.category ? ` · ${escapeHtml(course.category)}` : ""}</p>
        <p>${escapeHtml(course.description || "No description")}</p>
        <p class="muted">${course.meetings.length} weekly ${course.meetings.length === 1 ? "slot" : "slots"}${course.capacity ? ` · Capacity ${course.capacity}` : ""}</p>
      </div>
      <div class="row-actions">
        <button class="btn btn-ghost btn-sm" type="button" data-action="select" data-id="${course.id}">Select</button>
        <a class="btn btn-ghost btn-sm" href="/classes/${course.id}">View</a>
        ${isSuperadmin ? `
          <button class="btn btn-ghost btn-sm" type="button" data-action="edit" data-id="${course.id}">Edit</button>
          ${course.status !== "archived" ? `<button class="btn btn-danger btn-sm" type="button" data-action="archive" data-id="${course.id}">Archive</button>` : ""}
        ` : ""}
      </div>
    </article>`).join("") : state("No classes exist yet.", "empty");
}

function renderMeetings() {
  const course = selectedClass();
  meetingForm.hidden = !course;
  if (!course) {
    meetingList.innerHTML = state("Create or select a class before managing meetings.", "empty");
    return;
  }
  const meetings = [...course.meetings].sort((a, b) =>
    a.weekday - b.weekday || a.start_time.localeCompare(b.start_time));
  meetingList.innerHTML = meetings.length ? meetings.map((meeting) => `
    <article class="list-row">
      <div class="list-row-main">
        <div class="list-row-title">
          <h3>${escapeHtml(WEEKDAYS[meeting.weekday])}, ${escapeHtml(formatTime(meeting.start_time))}–${escapeHtml(formatTime(meeting.end_time))}</h3>
          ${meeting.audience === "members" ? '<span class="pill">Members only</span>' : ""}
        </div>
        <p>${escapeHtml(meeting.room || "Room to be announced")}</p>
        ${meeting.note ? `<p class="muted">${escapeHtml(meeting.note)}</p>` : ""}
      </div>
      <div class="row-actions">
        <button class="btn btn-ghost btn-sm" type="button" data-meeting-action="edit" data-id="${meeting.id}">Edit</button>
        <button class="btn btn-danger btn-sm" type="button" data-meeting-action="delete" data-id="${meeting.id}">Delete</button>
      </div>
    </article>`).join("") : state("This class has no weekly meetings yet.", "empty");
}

function renderNews() {
  newsList.innerHTML = newsItems.length ? newsItems.map((post) => {
    const course = classes.find((item) => item.id === post.class_id);
    return `
      <article class="list-row">
        <div class="list-row-main">
          <div class="list-row-title">
            <h3>${escapeHtml(post.title)}</h3>
            <span class="pill">${post.audience === "members" ? "Members only" : "Public"}</span>
          </div>
          <p class="pre-line">${escapeHtml(post.body)}</p>
          <p class="muted">${escapeHtml(formatDate(post.published_at))}${course ? ` · ${escapeHtml(course.title)}` : ""}</p>
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost btn-sm" type="button" data-news-action="edit" data-id="${post.id}">Edit</button>
          <button class="btn btn-danger btn-sm" type="button" data-news-action="delete" data-id="${post.id}">Delete</button>
        </div>
      </article>`;
  }).join("") : state("No news posts have been created yet.", "empty");
}

async function reloadClass(classId) {
  const updated = await request(`/api/classes/${classId}`);
  classes = classes.map((course) => course.id === classId ? updated : course);
  renderClasses();
  renderClassOptions();
  renderMeetings();
}

async function loadClasses() {
  classList.innerHTML = state("Loading classes…");
  try {
    const data = await request("/api/classes?limit=100");
    classes = data.items;
    if (!classes.some((course) => course.id === selectedClassId)) {
      selectedClassId = classes[0]?.id ?? null;
    }
    renderClasses();
    renderClassOptions();
    renderMeetings();
    renderNews();
  } catch (error) {
    classList.innerHTML = state(error.message, "error");
    meetingList.innerHTML = state("Meetings cannot load without the class catalogue.", "error");
  }
}

function openClassForm(course = null) {
  classForm.reset();
  classForm.hidden = false;
  classForm.elements.id.value = course?.id ?? "";
  classForm.elements.code.required = !course;
  document.querySelector("#class-code-field").hidden = Boolean(course);
  document.querySelector("#class-form-title").textContent = course ? "Edit class" : "Create a class";
  if (course) {
    ["title", "teacher_name", "category", "capacity", "description", "status"].forEach((name) => {
      classForm.elements[name].value = course[name] ?? "";
    });
  }
  classForm.scrollIntoView({ behavior: "smooth", block: "start" });
  classForm.elements.title.focus();
}

classForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = classForm.querySelector("button[type=submit]");
  const data = new FormData(classForm);
  const id = data.get("id");
  const body = {
    title: data.get("title").trim(),
    description: optional(data.get("description")),
    category: optional(data.get("category")),
    teacher_name: data.get("teacher_name").trim(),
    capacity: data.get("capacity") ? Number(data.get("capacity")) : null,
    status: data.get("status"),
  };
  setBusy(button, true, "Saving…");
  showFeedback("");
  try {
    const saved = await request(id ? `/api/classes/${id}` : "/api/classes", {
      method: id ? "PATCH" : "POST",
      body: id ? body : { ...body, code: data.get("code").trim() },
    });
    selectedClassId = saved.id;
    classForm.hidden = true;
    await loadClasses();
    showFeedback(id ? "Class updated." : "Class created.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

document.querySelector("#new-class").addEventListener("click", () => openClassForm());
document.querySelector("#cancel-class-edit").addEventListener("click", () => {
  classForm.hidden = true;
});

classList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  const course = classes.find((item) => item.id === id);
  if (button.dataset.action === "select") {
    selectedClassId = id;
    renderClasses();
    renderClassOptions();
    renderMeetings();
    showFeedback(`${course.title} selected.`);
  } else if (button.dataset.action === "edit" && isSuperadmin) {
    openClassForm(course);
  } else if (button.dataset.action === "archive" && isSuperadmin) {
    if (!window.confirm(`Archive ${course.title}? Students will no longer see it.`)) return;
    setBusy(button, true, "Archiving…");
    try {
      await request(`/api/classes/${id}/archive`, { method: "POST" });
      await loadClasses();
      showFeedback("Class archived.");
    } catch (error) {
      showFeedback(error.message, "error");
    }
  }
});

classSelect.addEventListener("change", () => {
  selectedClassId = Number(classSelect.value) || null;
  renderClasses();
  renderMeetings();
  if (!document.querySelector('[data-panel="members"]').hidden) loadMemberships();
});

meetingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const course = selectedClass();
  if (!course) return;
  const button = meetingForm.querySelector("button[type=submit]");
  const data = new FormData(meetingForm);
  const id = data.get("id");
  setBusy(button, true, "Saving…");
  showFeedback("");
  try {
    await request(id ? `/api/classes/${course.id}/meetings/${id}` : `/api/classes/${course.id}/meetings`, {
      method: id ? "PATCH" : "POST",
      body: {
        weekday: Number(data.get("weekday")),
        start_time: data.get("start_time"),
        end_time: data.get("end_time"),
        room: optional(data.get("room")),
        note: optional(data.get("note")),
        audience: data.get("audience"),
      },
    });
    meetingForm.reset();
    meetingForm.elements.id.value = "";
    document.querySelector("#meeting-form-title").textContent = "Add a meeting";
    await reloadClass(course.id);
    showFeedback(id ? "Meeting updated." : "Meeting added.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

meetingList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-meeting-action]");
  if (!button) return;
  const course = selectedClass();
  const meeting = course?.meetings.find((item) => item.id === Number(button.dataset.id));
  if (!meeting) return;
  if (button.dataset.meetingAction === "edit") {
    meetingForm.elements.id.value = meeting.id;
    meetingForm.elements.weekday.value = meeting.weekday;
    meetingForm.elements.start_time.value = formatTime(meeting.start_time);
    meetingForm.elements.end_time.value = formatTime(meeting.end_time);
    meetingForm.elements.room.value = meeting.room ?? "";
    meetingForm.elements.note.value = meeting.note ?? "";
    meetingForm.elements.audience.value = meeting.audience;
    document.querySelector("#meeting-form-title").textContent = "Edit meeting";
    meetingForm.scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (window.confirm("Delete this weekly meeting?")) {
    setBusy(button, true, "Deleting…");
    try {
      await request(`/api/classes/${course.id}/meetings/${meeting.id}`, { method: "DELETE" });
      await reloadClass(course.id);
      showFeedback("Meeting deleted.");
    } catch (error) {
      showFeedback(error.message, "error");
    }
  }
});

document.querySelector("#cancel-meeting-edit").addEventListener("click", () => {
  meetingForm.reset();
  meetingForm.elements.id.value = "";
  document.querySelector("#meeting-form-title").textContent = "Add a meeting";
});

async function loadMemberships() {
  const course = selectedClass();
  const sequence = ++membershipSequence;
  if (!course) {
    membershipList.innerHTML = state("Create or select a class before managing members.", "empty");
    return;
  }
  membershipList.innerHTML = state(`Loading ${course.title} members…`);
  try {
    const data = await request(`/api/classes/${course.id}/memberships`);
    if (sequence !== membershipSequence) return;
    membershipList.innerHTML = data.items.length ? data.items.map((membership) => `
      <article class="list-row" data-membership-row="${membership.user_id}">
        <div class="list-row-main">
          <div class="list-row-title">
            <h3>${escapeHtml(membership.user.full_name)}</h3>
            <span class="pill pill-${escapeHtml(membership.role)}">${escapeHtml(membership.role)}</span>
          </div>
          <p>${escapeHtml(membership.user.email)}</p>
          <p class="muted">Joined ${escapeHtml(formatDate(membership.created_at))}</p>
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost btn-sm" type="button" data-membership-action="role" data-user-id="${membership.user_id}" data-role="${membership.role === "member" ? "visitor" : "member"}">
            Make ${membership.role === "member" ? "visitor" : "member"}
          </button>
          <button class="btn btn-danger btn-sm" type="button" data-membership-action="remove" data-user-id="${membership.user_id}">Remove</button>
        </div>
      </article>`).join("") : state("Nobody has joined this class yet.", "empty");
  } catch (error) {
    membershipList.innerHTML = state(error.message, "error");
  }
}

membershipList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-membership-action]");
  if (!button || !selectedClassId) return;
  const userId = Number(button.dataset.userId);
  const removing = button.dataset.membershipAction === "remove";
  if (removing && !window.confirm("Remove this person from the class?")) return;
  setBusy(button, true, removing ? "Removing…" : "Saving…");
  try {
    await request(`/api/classes/${selectedClassId}/memberships/${userId}`, {
      method: removing ? "DELETE" : "PATCH",
      body: removing ? undefined : { role: button.dataset.role },
    });
    await loadMemberships();
    showFeedback(removing ? "Membership removed." : "Membership role updated.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

async function loadNews() {
  newsList.innerHTML = state("Loading news…");
  try {
    const data = await request("/api/news?limit=100");
    newsItems = data.items;
    renderNews();
  } catch (error) {
    newsList.innerHTML = state(error.message, "error");
  }
}

newsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(newsForm);
  const id = data.get("id");
  if (data.get("audience") === "members" && !data.get("class_id")) {
    showFeedback("Choose a related class for members-only news.", "error");
    return;
  }
  const button = newsForm.querySelector("button[type=submit]");
  setBusy(button, true, "Saving…");
  showFeedback("");
  try {
    await request(id ? `/api/news/${id}` : "/api/news", {
      method: id ? "PATCH" : "POST",
      body: {
        title: data.get("title").trim(),
        body: data.get("body").trim(),
        class_id: data.get("class_id") ? Number(data.get("class_id")) : null,
        audience: data.get("audience"),
      },
    });
    newsForm.reset();
    newsForm.elements.id.value = "";
    document.querySelector("#news-form-title").textContent = "Create a news post";
    await loadNews();
    showFeedback(id ? "News post updated." : "News post published.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

function resetNewsForm() {
  newsForm.reset();
  newsForm.elements.id.value = "";
  document.querySelector("#news-form-title").textContent = "Create a news post";
}

document.querySelector("#new-news").addEventListener("click", resetNewsForm);
document.querySelector("#cancel-news-edit").addEventListener("click", resetNewsForm);

newsList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-news-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  const post = newsItems.find((item) => item.id === id);
  if (button.dataset.newsAction === "edit") {
    newsForm.elements.id.value = post.id;
    newsForm.elements.title.value = post.title;
    newsForm.elements.body.value = post.body;
    newsForm.elements.class_id.value = post.class_id ?? "";
    newsForm.elements.audience.value = post.audience;
    document.querySelector("#news-form-title").textContent = "Edit news post";
    newsForm.scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (window.confirm(`Delete “${post.title}”?`)) {
    setBusy(button, true, "Deleting…");
    try {
      await request(`/api/news/${id}`, { method: "DELETE" });
      await loadNews();
      showFeedback("News post deleted.");
    } catch (error) {
      showFeedback(error.message, "error");
    }
  }
});

async function loadStudents(button = null) {
  const q = document.querySelector("#student-query").value.trim();
  studentList.innerHTML = state("Loading students…");
  if (button) setBusy(button, true, "Searching…");
  try {
    const data = await request(`/api/students${query({ q, limit: 100 })}`);
    studentList.innerHTML = data.items.length ? data.items.map((student) => `
      <article class="list-row">
        <div class="list-row-main">
          <div class="list-row-title">
            <h3>${escapeHtml(student.full_name)}</h3>
            <span class="pill pill-${escapeHtml(student.status)}">${escapeHtml(student.status)}</span>
          </div>
          <p>${escapeHtml(student.email)}</p>
          <p class="muted">User ID ${student.id}${student.profile?.student_number ? ` · ${escapeHtml(student.profile.student_number)}` : ""}${student.profile?.faculty ? ` · ${escapeHtml(student.profile.faculty)}` : ""}${student.profile?.study_year ? ` · Year ${student.profile.study_year}` : ""}</p>
        </div>
      </article>`).join("") : state("No students match this search.", "empty");
  } catch (error) {
    studentList.innerHTML = state(error.message, "error");
  } finally {
    if (button) setBusy(button, false);
  }
}

document.querySelector("#student-search").addEventListener("submit", (event) => {
  event.preventDefault();
  loadStudents(event.submitter);
});

async function loadApplications() {
  if (!isSuperadmin) return;
  applicationList.innerHTML = state("Loading applications…");
  try {
    const status = document.querySelector("#application-status-filter").value;
    const data = await request(`/api/admin-applications${query({ status })}`);
    applicationList.innerHTML = data.items.length ? data.items.map((item) => `
      <article class="list-row" data-application-row="${item.id}">
        <div class="list-row-main">
          <div class="list-row-title">
            <h3>${escapeHtml(item.applicant.full_name)} · ${escapeHtml(item.requested_position)}</h3>
            <span class="pill pill-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span>
          </div>
          <p>${escapeHtml(item.applicant.email)}${item.department ? ` · ${escapeHtml(item.department)}` : ""}</p>
          <p class="pre-line">${escapeHtml(item.motivation)}</p>
          <p class="muted">Submitted ${escapeHtml(formatDate(item.created_at))}</p>
          ${item.decision_note ? `<p><strong>Decision note:</strong> ${escapeHtml(item.decision_note)}</p>` : ""}
          ${item.status === "pending" ? `
            <div class="decision-controls">
              <label>Decision note <span class="optional">Optional</span>
                <input data-decision-note maxlength="500" placeholder="Note for the applicant">
              </label>
              <div class="row-actions">
                <button class="btn btn-primary btn-sm" type="button" data-application-action="approve" data-id="${item.id}">Approve</button>
                <button class="btn btn-danger btn-sm" type="button" data-application-action="reject" data-id="${item.id}">Reject</button>
              </div>
            </div>` : ""}
        </div>
      </article>`).join("") : state("No applications match this status.", "empty");
  } catch (error) {
    applicationList.innerHTML = state(error.message, "error");
  }
}

document.querySelector("#application-status-filter").addEventListener("change", loadApplications);

applicationList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-application-action]");
  if (!button || !isSuperadmin) return;
  const action = button.dataset.applicationAction;
  const row = button.closest("[data-application-row]");
  const note = row.querySelector("[data-decision-note]")?.value.trim() || null;
  setBusy(button, true, "Saving…");
  try {
    await request(`/api/admin-applications/${button.dataset.id}/${action}`, {
      method: "POST",
      body: { note },
    });
    await Promise.all([loadApplications(), loadAdmins(), loadStudents()]);
    showFeedback(`Application ${action === "approve" ? "approved" : "rejected"}.`);
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

async function loadAdmins() {
  if (!isSuperadmin) return;
  adminDirectory.innerHTML = state("Loading administrators…");
  try {
    const data = await request("/api/admins?limit=100");
    adminDirectory.innerHTML = data.items.length ? data.items.map((admin) => `
      <article class="list-row">
        <div class="list-row-main">
          <div class="list-row-title">
            <h3>${escapeHtml(admin.full_name)}</h3>
            <span class="pill">${escapeHtml(admin.role)}</span>
          </div>
          <p>${escapeHtml(admin.email)}</p>
          <p class="muted">${escapeHtml(admin.profile?.position || "Administrator")}${admin.profile?.department ? ` · ${escapeHtml(admin.profile.department)}` : ""}</p>
        </div>
      </article>`).join("") : state("No administrators found.", "empty");
  } catch (error) {
    adminDirectory.innerHTML = state(error.message, "error");
  }
}

document.querySelector("#grant-admin-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!isSuperadmin) return;
  const form = event.currentTarget;
  const data = new FormData(form);
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Granting…");
  try {
    await request("/api/admins/grant", {
      method: "POST",
      body: {
        user_id: Number(data.get("user_id")),
        position: data.get("position").trim(),
        department: optional(data.get("department")),
      },
    });
    form.reset();
    await Promise.all([loadAdmins(), loadStudents()]);
    showFeedback("Administrator access granted.");
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => showTab(button.dataset.tab));
});

async function initialise() {
  let session;
  try {
    session = await getMe();
  } catch (error) {
    access.innerHTML = state(error.message, "error");
    return;
  }
  currentUser = session?.user ?? null;
  if (!currentUser) {
    access.innerHTML = `
      <section class="empty-panel">
        <h2>Staff sign-in required</h2>
        <p>Sign in with an administrator account to open this workspace.</p>
        <a class="btn btn-primary" href="/register?next=%2Fadmin#login">Sign in</a>
      </section>`;
    return;
  }
  if (currentUser.role !== "admin" && currentUser.role !== "superadmin") {
    access.innerHTML = `
      <section class="empty-panel">
        <h2>Administrator access required</h2>
        <p>Your student account does not have staff permissions. You can apply for administrator access from your account page.</p>
        <a class="btn btn-primary" href="/register#account">Open your account</a>
      </section>`;
    return;
  }

  isSuperadmin = currentUser.role === "superadmin";
  access.innerHTML = "";
  workspace.hidden = false;
  document.querySelector("#admin-identity").textContent = `${currentUser.full_name} · ${currentUser.role}`;
  document.querySelectorAll(".tabs [data-superadmin], #new-class").forEach((element) => {
    element.hidden = !isSuperadmin;
  });
  showTab("classes");
  await Promise.all([
    loadClasses(),
    loadNews(),
    loadStudents(),
    loadApplications(),
    loadAdmins(),
  ]);
}

initialise();
