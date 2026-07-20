document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar");
  const menu = document.querySelector("[data-menu-button]");
  const scrim = document.querySelector("[data-sidebar-scrim]");
  const setMenuOpen = (open) => {
    sidebar?.classList.toggle("open", open);
    scrim?.classList.toggle("open", open);
    menu?.setAttribute("aria-expanded", String(open));
  };
  menu?.addEventListener("click", () => setMenuOpen(!sidebar?.classList.contains("open")));
  scrim?.addEventListener("click", () => setMenuOpen(false));
  sidebar?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenuOpen(false)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuOpen(false);
  });
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "Confirm this action?")) event.preventDefault();
    });
  });
});
