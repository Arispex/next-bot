(() => {
  const runningStatusNode = document.getElementById("running_status");
  const runningStatusValueNode = document.getElementById("running_status_value");
  const serverCountNode = document.getElementById("server_count");
  const userCountNode = document.getElementById("user_count");
  const commandExecuteCountNode = document.getElementById("command_execute_count");
  const refreshTextNode = document.getElementById("dashboard-refresh-text");

  const formatNumber = (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return "--";
    }
    return parsed.toLocaleString("zh-CN");
  };

  const setRefreshText = (text) => {
    if (!refreshTextNode) {
      return;
    }
    refreshTextNode.textContent = text;
  };

  const loadDashboardData = async () => {
    try {
      const response = await fetch("/webui/api/dashboard", {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = await response.json();
      if (!payload || payload.ok !== true || !payload.data) {
        throw new Error("invalid payload");
      }

      const data = payload.data;
      const runningStatus = String(data.running_status || "Running");

      if (runningStatusNode) {
        runningStatusNode.textContent = runningStatus;
      }
      if (runningStatusValueNode) {
        runningStatusValueNode.textContent = runningStatus;
      }
      if (serverCountNode) {
        serverCountNode.textContent = formatNumber(data.server_count);
      }
      if (userCountNode) {
        userCountNode.textContent = formatNumber(data.user_count);
      }
      if (commandExecuteCountNode) {
        commandExecuteCountNode.textContent = formatNumber(data.command_execute_count);
      }

      const now = new Date();
      setRefreshText(
        `最近刷新：${now.toLocaleTimeString("zh-CN", { hour12: false })}`
      );
    } catch (_error) {
      setRefreshText("最近刷新：加载失败");
    }
  };

  loadDashboardData();
})();
