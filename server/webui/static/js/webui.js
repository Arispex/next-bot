(() => {
  const root = document.documentElement;
  const sidebar = document.getElementById("webui-sidebar");
  const sidebarOverlay = document.getElementById("sidebar-overlay");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const themeToggle = document.getElementById("theme-toggle");
  const sidebarLinks = sidebar ? sidebar.querySelectorAll("a[href]") : [];
  const sidebarStateKey = "nextbot-webui-sidebar-collapsed";
  const mobileMedia = window.matchMedia("(max-width: 840px)");

  let desktopCollapsed = false;
  let mobileOpen = false;
  let mobileMode = mobileMedia.matches;

  const setExpanded = (expanded) => {
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    }
  };

  const setMobileOpen = (next) => {
    mobileOpen = next;
    applySidebarState();
  };

  const applySidebarState = () => {
    if (!sidebar) {
      return;
    }

    mobileMode = mobileMedia.matches;

    if (mobileMode) {
      sidebar.classList.remove("is-collapsed");
      sidebar.classList.toggle("is-mobile-open", mobileOpen);
      if (sidebarOverlay) {
        sidebarOverlay.classList.toggle("is-visible", mobileOpen);
        sidebarOverlay.setAttribute("aria-hidden", mobileOpen ? "false" : "true");
      }
      document.body.classList.toggle("sidebar-open-lock", mobileOpen);
      setExpanded(mobileOpen);
      if (sidebarToggle) {
        sidebarToggle.setAttribute("aria-label", mobileOpen ? "关闭导航菜单" : "打开导航菜单");
      }
      return;
    }

    mobileOpen = false;
    sidebar.classList.remove("is-mobile-open");
    sidebar.classList.toggle("is-collapsed", desktopCollapsed);
    if (sidebarOverlay) {
      sidebarOverlay.classList.remove("is-visible");
      sidebarOverlay.setAttribute("aria-hidden", "true");
    }
    document.body.classList.remove("sidebar-open-lock");
    setExpanded(!desktopCollapsed);
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-label", desktopCollapsed ? "展开侧边栏" : "隐藏侧边栏");
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
      if (mobileMedia.matches) {
        setMobileOpen(!mobileOpen);
        return;
      }

      desktopCollapsed = !desktopCollapsed;
      applySidebarState();
      try {
        localStorage.setItem(sidebarStateKey, desktopCollapsed ? "1" : "0");
      } catch (error) {
        // Ignore storage errors.
      }
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", () => {
      if (mobileMedia.matches) {
        setMobileOpen(false);
      }
    });
  }

  if (sidebarLinks.length > 0) {
    sidebarLinks.forEach((link) => {
      link.addEventListener("click", () => {
        if (mobileMedia.matches) {
          setMobileOpen(false);
        }
      });
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mobileMedia.matches && mobileOpen) {
      setMobileOpen(false);
    }
  });

  if (mobileMedia.addEventListener) {
    mobileMedia.addEventListener("change", () => {
      applySidebarState();
    });
  } else if (mobileMedia.addListener) {
    mobileMedia.addListener(() => {
      applySidebarState();
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
    desktopCollapsed = localStorage.getItem(sidebarStateKey) === "1";
  } catch (error) {
    desktopCollapsed = false;
  }

  applySidebarState();
  syncThemeButton();
})();
