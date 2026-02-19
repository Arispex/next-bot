(function () {
  try {
    var stored = localStorage.getItem("nextbot-webui-theme");
    var shouldUseDark =
      stored === "dark" ||
      (stored !== "light" &&
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (shouldUseDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } catch (error) {
    document.documentElement.classList.remove("dark");
  }
})();
