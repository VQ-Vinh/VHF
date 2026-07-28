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
  const dialog = document.querySelector("[data-confirm-dialog]");
  const dialogMessage = dialog?.querySelector("[data-confirm-message]");
  let pendingForm = null;
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "true") return;
      event.preventDefault();
      pendingForm = form;
      if (dialogMessage) dialogMessage.textContent = form.dataset.confirm || "Confirm this action?";
      dialog?.showModal();
    });
  });
  dialog?.addEventListener("close", () => {
    if (dialog.returnValue === "confirm" && pendingForm) {
      pendingForm.dataset.confirmed = "true";
      pendingForm.requestSubmit();
    }
    pendingForm = null;
  });
  document.querySelectorAll("[data-plan-form]").forEach((form) => {
    const card = form.closest(".catalog-card");
    const editButton = card?.querySelector("[data-plan-edit]");
    const editIcon = editButton?.querySelector("[data-edit-icon]");
    const cancelIcon = editButton?.querySelector("[data-cancel-icon]");
    const fields = [...form.querySelectorAll("input:not([type='hidden'])")];
    const saveButton = form.querySelector("button[type='submit']");
    const initialValues = new Map(fields.map((field) => [field.name, field.value]));

    const isDirty = () =>
      fields.some((field) => field.value !== initialValues.get(field.name));

    const updateSaveState = () => {
      const editing = form.dataset.editing === "true";
      if (saveButton) saveButton.disabled = !editing || !isDirty() || !form.checkValidity();
    };

    const setEditing = (editing) => {
      form.dataset.editing = String(editing);
      fields.forEach((field) => {
        field.disabled = !editing;
      });
      editButton?.setAttribute("aria-pressed", String(editing));
      const label = editing ? form.dataset.cancelLabel : form.dataset.editLabel;
      if (label && editButton) {
        editButton.setAttribute("aria-label", label);
        editButton.setAttribute("title", label);
      }
      if (editIcon) editIcon.hidden = editing;
      if (cancelIcon) cancelIcon.hidden = !editing;
      updateSaveState();
      if (editing) fields[0]?.focus();
    };

    editButton?.addEventListener("click", () => {
      const editing = form.dataset.editing === "true";
      if (editing) {
        fields.forEach((field) => {
          field.value = initialValues.get(field.name) ?? "";
        });
      }
      setEditing(!editing);
    });
    fields.forEach((field) => {
      field.addEventListener("input", updateSaveState);
      field.addEventListener("change", updateSaveState);
    });
    setEditing(false);
  });
  document.querySelectorAll("[data-plan-preview]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = button.closest("form");
      if (!form) return;
      const values = new FormData(form);
      form.dataset.confirm = [
        `${values.get("name")}: ${values.get("daily_minutes")} min/day`,
        `RPM ${values.get("requests_per_minute")}, concurrency ${values.get("max_concurrency")}`,
        `devices ${values.get("max_devices")}, stations ${values.get("max_stations")}`,
      ].join("\n");
    });
  });
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      if (form.dataset.confirm && form.dataset.confirmed !== "true") return;
      form.querySelectorAll("button[type='submit'], button:not([type])").forEach((button) => {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      });
    });
  });
});
