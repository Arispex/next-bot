(() => {
  const root = document.documentElement;
  const sidebar = document.getElementById("webui-sidebar");
  const toggleButton = document.getElementById("sidebar-toggle");
  const menuLabels = Array.from(document.querySelectorAll(".menu-label"));
  const brand = document.getElementById("sidebar-brand");
  const subtitle = document.getElementById("sidebar-subtitle");
  const themeToggle = document.getElementById("theme-toggle");
  const themeLabel = document.getElementById("theme-toggle-label");

  let sidebarCollapsed = false;

  const applySidebarState = () => {
    if (!sidebar) return;
    if (sidebarCollapsed) {
      sidebar.classList.remove("w-72");
      sidebar.classList.add("w-20");
      menuLabels.forEach((node) => node.classList.add("hidden"));
      if (brand) brand.classList.add("hidden");
      if (subtitle) subtitle.classList.add("hidden");
      return;
    }

    sidebar.classList.remove("w-20");
    sidebar.classList.add("w-72");
    menuLabels.forEach((node) => node.classList.remove("hidden"));
    if (brand) brand.classList.remove("hidden");
    if (subtitle) subtitle.classList.remove("hidden");
  };

  const syncThemeButton = () => {
    if (!themeLabel) return;
    themeLabel.textContent = root.classList.contains("dark") ? "Light" : "Dark";
  };

  if (toggleButton) {
    toggleButton.addEventListener("click", () => {
      sidebarCollapsed = !sidebarCollapsed;
      applySidebarState();
    });
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const isDark = root.classList.toggle("dark");
      try {
        localStorage.setItem("nextbot-webui-theme", isDark ? "dark" : "light");
      } catch (error) {
        // Ignore storage errors.
      }
      syncThemeButton();
    });
  }

  applySidebarState();
  syncThemeButton();
})();
