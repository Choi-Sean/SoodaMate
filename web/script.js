// Store badges link to #download until the app is actually live — swap the
// href to the real store listing URLs once submitted (see
// docs/APP_STORE_SUBMISSION.md at the repo root).
document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const target = document.querySelector(link.getAttribute("href"));
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
