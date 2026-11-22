import { escapeHtml, request, state } from "./api.js";

const mount = document.querySelector("#home-news");

function newsArticle(post) {
  const date = new Date(post.published_at);
  const validDate = !Number.isNaN(date.getTime());
  const day = validDate ? new Intl.DateTimeFormat("en", { day: "2-digit" }).format(date) : "—";
  const month = validDate ? new Intl.DateTimeFormat("en", { month: "short" }).format(date) : "News";
  const tag = post.audience === "members" ? "Members" : post.class_id ? "Club" : "Campus";
  return `
    <article class="news-item">
      <div class="news-date" aria-hidden="true">
        <span class="news-day">${day}</span>
        <span class="news-month">${month}</span>
      </div>
      <div class="news-body">
        <span class="pill">${tag}</span>
        <h3>${escapeHtml(post.title)}</h3>
        <p>${escapeHtml(post.body)}</p>
      </div>
    </article>`;
}

async function loadNews() {
  mount.innerHTML = state("Loading news…");
  try {
    const data = await request("/api/news?limit=6");
    mount.innerHTML = data.items.length
      ? data.items.map(newsArticle).join("")
      : state("No news has been published yet. Check back soon.", "empty");
  } catch (error) {
    mount.innerHTML = `${state(error.message, "error")}
      <button class="btn btn-ghost btn-sm state-retry" type="button">Try again</button>`;
    mount.querySelector("button").addEventListener("click", loadNews, { once: true });
  }
}

loadNews();
