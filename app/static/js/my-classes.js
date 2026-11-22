import { getMe, state } from "./api.js";

const mount = document.querySelector("#my-classes");

function render(session) {
  if (!session?.user) {
    mount.innerHTML = `
      <section class="empty-panel">
        <h2>Sign in to see your classes</h2>
        <p>Your personal class list is connected to your student account.</p>
        <a class="btn btn-primary" href="/register?next=%2Fmy-classes#login">Sign in</a>
      </section>`;
    return;
  }
  mount.innerHTML = `
    <section class="empty-panel">
      <p class="eyebrow">Backend connection pending</p>
      <h2>Your personal class list is not available yet</h2>
      <p>The current API does not provide a way to read your own memberships, so this page cannot show an accurate schedule yet. No placeholder classes are being displayed.</p>
      <p>You can still browse the catalogue and join published classes as a visitor.</p>
      <a class="btn btn-primary" href="/classes">Browse classes</a>
    </section>`;
}

window.addEventListener("auth:changed", (event) => render(event.detail));
getMe().then(render).catch((error) => {
  mount.innerHTML = state(error.message, "error");
});
