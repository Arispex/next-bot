(() => {
  const runningStatusNode = document.getElementById("running_status");
  const runningStatusValueNode = document.getElementById("running_status_value");
  const serverCountNode = document.getElementById("server_count");
  const userCountNode = document.getElementById("user_count");
  const commandExecuteCountNode = document.getElementById("command_execute_count");
  const connectedBotCountNode = document.getElementById("connected_bot_count");
  const connectedBotIdsNode = document.getElementById("connected_bot_ids");
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

  const renderConnectedBotIds = (ids) => {
    if (!connectedBotIdsNode) {
      return;
    }

    connectedBotIdsNode.textContent = "";
    connectedBotIdsNode.classList.remove("is-empty");

    const list = Array.isArray(ids)
      ? ids.map((item) => String(item || "").trim()).filter((item) => item.length > 0)
      : [];

    if (list.length === 0) {
      connectedBotIdsNode.textContent = "无";
      connectedBotIdsNode.classList.add("is-empty");
      return;
    }

    list.forEach((item) => {
      const node = document.createElement("span");
      node.className = "bot-id-tag";
      node.textContent = item;
      connectedBotIdsNode.appendChild(node);
    });
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
      if (connectedBotCountNode) {
        connectedBotCountNode.textContent = formatNumber(data.connected_bot_count);
      }
      renderConnectedBotIds(data.connected_bot_ids);

      const now = new Date();
      setRefreshText(
        `最近刷新：${now.toLocaleTimeString("zh-CN", { hour12: false })}`
      );
    } catch (_error) {
      renderConnectedBotIds([]);
      setRefreshText("最近刷新：加载失败");
    }
  };

  loadDashboardData();
})();
