(function () {
  const fqdnPattern = /^(?=.{1,253}$)(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;

  function init() {
    document.querySelectorAll("[data-user-pet-form]").forEach(initPetForm);
    document.querySelectorAll("[data-confirm-delete]").forEach(initDeleteConfirmation);
  }

  function initPetForm(form) {
    form.querySelectorAll("[data-pet-widget]").forEach((widget) => initPetWidget(form, widget));
  }

  function initPetWidget(form, widget) {
    const input = widget.querySelector("[data-pet-input]");
    const addButton = widget.querySelector("[data-pet-add]");
    const removeButton = widget.querySelector("[data-pet-remove]");
    const list = widget.querySelector("[data-pet-list]");
    const hidden = widget.querySelector("[data-pet-hidden]");
    const status = widget.querySelector("[data-pet-status]");

    if (!input || !addButton || !removeButton || !list || !hidden) {
      return;
    }

    const setStatus = (message, isError = false) => {
      if (!status) {
        return;
      }
      status.textContent = message;
      status.classList.toggle("pet-status-error", Boolean(isError));
      status.classList.toggle("pet-status-success", !isError && Boolean(message));
    };

    const syncHidden = () => {
      hidden.value = Array.from(list.options).map((option) => option.value).join("\n");
    };

    const hasPet = (value) => Array.from(list.options).some((option) => option.value === value);

    const parsePetValues = () => input.value
      .split(/[\s,;]+/)
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);

    const addPet = () => {
      const values = parsePetValues();
      if (!values.length) {
        setStatus("Enter one or more pet FQDNs before clicking +.", true);
        return;
      }

      const invalidValues = values.filter((value) => !fqdnPattern.test(value));
      if (invalidValues.length) {
        setStatus(`Invalid FQDN-like value${invalidValues.length === 1 ? "" : "s"}: ${invalidValues.join(", ")}.`, true);
        return;
      }

      const addedValues = [];
      const skippedValues = [];
      const seenValues = new Set();
      values.forEach((value) => {
        if (seenValues.has(value) || hasPet(value)) {
          skippedValues.push(value);
          return;
        }
        seenValues.add(value);
        list.add(new Option(value, value));
        addedValues.push(value);
      });

      if (!addedValues.length) {
        setStatus("All pasted pets are already in the list.", true);
        return;
      }

      input.value = "";
      input.focus();
      const skippedMessage = skippedValues.length ? ` Skipped ${skippedValues.length} duplicate${skippedValues.length === 1 ? "" : "s"}.` : "";
      setStatus(`Added ${addedValues.length} pet${addedValues.length === 1 ? "" : "s"}.${skippedMessage}`);
      syncHidden();
    };

    const removeSelected = () => {
      const selected = Array.from(list.selectedOptions);
      if (!selected.length) {
        setStatus("Select one or more pets to remove.", true);
        return;
      }

      selected.forEach((option) => option.remove());
      syncHidden();
      setStatus(`Removed ${selected.length} pet${selected.length === 1 ? "" : "s"}.`);
    };

    addButton.addEventListener("click", addPet);
    removeButton.addEventListener("click", removeSelected);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        addPet();
      }
    });
    form.addEventListener("submit", syncHidden);
    syncHidden();
  }

  function initDeleteConfirmation(form) {
    const message = form.getAttribute("data-confirm-delete") || "Delete this user?";
    form.addEventListener("submit", (event) => {
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
