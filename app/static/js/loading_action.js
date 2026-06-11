(function () {
  function init() {
    document.querySelectorAll("[data-loading-action-form]").forEach((form) => {
      const submitOnce = () => {
        if (form.dataset.loadingSubmitted === "true") {
          return;
        }
        form.dataset.loadingSubmitted = "true";
        form.submit();
      };

      window.setTimeout(submitOnce, Number(form.dataset.loadingDelay || "180"));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
