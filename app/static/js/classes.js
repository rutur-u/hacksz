import {
  WEEKDAYS,
  escapeHtml,
  formatTime,
  getMe,
  query,
  request,
  state,
} from "./api.js";

const form = document.querySelector("#class-filters");
const results = document.querySelector("#class-results");
const count = document.querySelector("#class-count");
const categoryInput = document.querySelector("#class-category");
const weekdayInput = document.querySelector("#class-weekday");
const searchInput = form.elements.q;
const statusInput = document.querySelector("#class-status");
let loadSequence = 0;
let catalogue = [];

function meetingText(meeting) {
  return `${WEEKDAYS[meeting.weekday]} ${formatTime(meeting.start_time)}–${formatTime(meeting.end_time)}${meeting.room ? ` · ${meeting.room}` : ""}`;
}

const CATEGORY_BADGES = {
  "体育": { className: "club-badge-sports", emoji: "⚽" },
  "科技": { className: "club-badge-tech", emoji: "🤖" },
  "艺术": { className: "club-badge-art", emoji: "🎨" },
  "语言": { className: "club-badge-lang", emoji: "🎵" },
};

function categoryBadge(category) {
  const meta = CATEGORY_BADGES[category] || {};
  const icon = meta.emoji ? `<span aria-hidden="true">${meta.emoji}</span>` : "";
  const modifier = meta.className ? ` ${meta.className}` : "";
  return `<span class="club-badge${modifier}">${icon}${escapeHtml(category)}</span>`;
}

function classCard(course) {
  const meetings = [...course.meetings].sort((a, b) =>
    a.weekday - b.weekday || a.start_time.localeCompare(b.start_time));
  return `
    <article class="catalogue-card">
      <div class="catalogue-card-head">
        <div>
          <p class="card-eyebrow">${escapeHtml(course.code)}</p>
          <h2><a href="/classes/${course.id}">${escapeHtml(course.title)}</a></h2>
        </div>
        ${course.category ? categoryBadge(course.category) : ""}
      </div>
      <p class="catalogue-teacher">Led by ${escapeHtml(course.teacher_name)}</p>
      ${course.description ? `<p class="catalogue-description">${escapeHtml(course.description)}</p>` : ""}
      <ul class="meeting-summary">
        ${meetings.length
          ? meetings.map((meeting) => `<li>${escapeHtml(meetingText(meeting))}${meeting.audience === "members" ? " · Members only" : ""}</li>`).join("")
          : "<li>No visible weekly meeting slots</li>"}
      </ul>
      <div class="catalogue-card-foot">
        <span class="pill pill-${escapeHtml(course.status)}">${escapeHtml(course.status)}</span>
        <span class="muted">${course.capacity ? `Capacity ${course.capacity}` : "Open capacity"}</span>
        <a class="card-more" href="/classes/${course.id}">View class <span aria-hidden="true">→</span></a>
      </div>
    </article>`;
}

function emptyState() {
  return `<div class="state state-empty" role="status">
    <p>没有找到匹配的社团</p>
    <button class="btn btn-ghost btn-sm" type="button" data-clear-filters>Clear filters</button>
  </div>`;
}

function syncUrl() {
  const params = query({
    q: form.elements.q.value.trim(),
    category: form.elements.category.value,
    weekday: form.elements.weekday.value,
    status: form.elements.status.value,
  });
  window.history.replaceState(null, "", `${window.location.pathname}${params}`);
}

function populateCategories(selected) {
  const categories = [...new Set(catalogue.map((item) => item.category).filter(Boolean))].sort();
  categoryInput.innerHTML = `<option value="">All categories</option>${categories.map((category) =>
    `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("")}`;
  categoryInput.value = selected;
}

function scoreCourse(course, tokens) {
  const title = String(course.title ?? "").toLowerCase();
  const haystack = [title, course.code, course.description, course.teacher_name, course.category]
    .map((value) => String(value ?? "").toLowerCase())
    .join(" ");
  let total = 0;
  for (const token of tokens) {
    let tokenScore = -1;
    if (title.startsWith(token)) tokenScore = 0;
    else if (title.split(/\s+/).some((word) => word.startsWith(token))) tokenScore = 1;
    else if (title.includes(token)) tokenScore = 2;
    else if (haystack.includes(token)) tokenScore = 3;
    if (tokenScore < 0) return -1;
    total += tokenScore;
  }
  return total;
}

function render() {
  const tokens = searchInput.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const category = categoryInput.value;
  const weekday = weekdayInput.value;
  const status = statusInput.value;
  const items = catalogue
    .map((course, index) => ({
      course,
      index,
      score: tokens.length ? scoreCourse(course, tokens) : 0,
    }))
    .filter((entry) =>
      entry.score >= 0
      && (!category || entry.course.category === category)
      && (!status || entry.course.status === status)
      && (weekday === "" || entry.course.meetings.some((meeting) => String(meeting.weekday) === weekday)))
    .sort((a, b) => a.score - b.score || a.index - b.index)
    .map((entry) => entry.course);

  count.textContent = weekday === ""
    ? `${items.length} ${items.length === 1 ? "class" : "classes"} found`
    : `${items.length} ${items.length === 1 ? "class" : "classes"} meet on ${WEEKDAYS[Number(weekday)]}`;
  results.innerHTML = items.length
    ? items.map(classCard).join("")
    : emptyState();
  syncUrl();
}

async function loadCatalogue(selectedCategory = "") {
  const sequence = ++loadSequence;
  results.innerHTML = state("Loading classes…");
  count.textContent = "";
  try {
    const data = await request("/api/classes?limit=100");
    if (sequence !== loadSequence) return;
    catalogue = data.items;
    populateCategories(selectedCategory);
    render();
  } catch (error) {
    if (sequence === loadSequence) results.innerHTML = state(error.message, "error");
  }
}

function clearFilters() {
  form.reset();
  render();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  render();
});

searchInput.addEventListener("input", render);

[categoryInput, weekdayInput, statusInput].forEach((input) => {
  input.addEventListener("change", render);
});

document.querySelector("#clear-filters").addEventListener("click", clearFilters);

results.addEventListener("click", (event) => {
  if (event.target.closest("[data-clear-filters]")) clearFilters();
});

async function initialise() {
  const session = await getMe().catch(() => null);
  const isStaff = session?.user.role === "admin" || session?.user.role === "superadmin";
  document.querySelector("#class-status-field").hidden = !isStaff;
  if (!isStaff) statusInput.value = "";

  const params = new URLSearchParams(window.location.search);
  searchInput.value = params.get("q") || "";
  weekdayInput.value = params.get("weekday") || "";
  if (isStaff) statusInput.value = params.get("status") || "";

  await loadCatalogue(params.get("category") || "");
}

initialise();
