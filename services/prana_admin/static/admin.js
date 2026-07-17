document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar");
  const menu = document.querySelector("[data-menu-button]");
  menu?.addEventListener("click", () => sidebar?.classList.toggle("open"));
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "Confirm this action?")) event.preventDefault();
    });
  });
});
