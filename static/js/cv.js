document.addEventListener("DOMContentLoaded", () => {
  const printButton = document.querySelector("[data-print-cv]");
  printButton?.addEventListener("click", () => window.print());
});
