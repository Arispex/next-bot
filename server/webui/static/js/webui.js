(() => {
  const root = document.documentElement;
  const sidebar = document.getElementById("webui-sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const themeToggle = document.getElementById("theme-toggle");
  const sidebarStateKey = "nextbot-webui-sidebar-collapsed";

  let sidebarCollapsed = false;

  const applySidebarState = () => {
    if (!sidebar) {
      return;
    }
    sidebar.classList.toggle("is-collapsed", sidebarCollapsed);
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-label", sidebarCollapsed ? "展开侧边栏" : "隐藏侧边栏");
    }
  };

  const syncThemeButton = () => {
    if (!themeToggle) {
      return;
    }
    const dark = root.classList.contains("dark");
    themeToggle.setAttribute("aria-label", dark ? "切换到浅色主题" : "切换到深色主题");
  };

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      sidebarCollapsed = !sidebarCollapsed;
      applySidebarState();
      try {
        localStorage.setItem(sidebarStateKey, sidebarCollapsed ? "1" : "0");
      } catch (error) {
        // Ignore storage errors.
      }
    });
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const dark = root.classList.toggle("dark");
      try {
        localStorage.setItem("nextbot-webui-theme", dark ? "dark" : "light");
      } catch (error) {
        // Ignore storage errors.
      }
      syncThemeButton();
    });
  }

  try {
    sidebarCollapsed = localStorage.getItem(sidebarStateKey) === "1";
  } catch (error) {
    sidebarCollapsed = false;
  }

  applySidebarState();
  syncThemeButton();
})();
