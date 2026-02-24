(() => {
  const reloadButton = document.getElementById("reload-btn");
  const saveButton = document.getElementById("save-btn");
  const statusNode = document.getElementById("status");
  const statusMessageNode = document.getElementById("status-message");
  const restartAlertNode = document.getElementById("restart-alert");
  const restartMessageNode = document.getElementById("restart-message");
  const statHotNode = document.getElementById("stat-hot");
  const statRestartNode = document.getElementById("stat-restart");

  const onebotWsUrlsInput = document.getElementById("field-onebot-ws-urls");
  const onebotAccessTokenInput = document.getElementById("field-onebot-access-token");
  const ownerIdInput = document.getElementById("field-owner-id");
  const groupIdInput = document.getElementById("field-group-id");
  const webServerHostInput = document.getElementById("field-web-server-host");
  const webServerPortInput = document.getElementById("field-web-server-port");
  const webServerPublicBaseUrlInput = document.getElementById("field-web-server-public-base-url");
  const commandDisabledModeInput = document.getElementById("field-command-disabled-mode");
  const commandDisabledMessageInput = document.getElementById("field-command-disabled-message");
  const tokenToggleButton = document.getElementById("token-toggle-btn");

  const requiredNodesReady = Boolean(
    reloadButton &&
    saveButton &&
    statusNode &&
    statusMessageNode &&
    restartAlertNode &&
    restartMessageNode &&
    statHotNode &&
    statRestartNode &&
    onebotWsUrlsInput &&
    onebotAccessTokenInput &&
    ownerIdInput &&
    groupIdInput &&
    webServerHostInput &&
    webServerPortInput &&
    webServerPublicBaseUrlInput &&
    commandDisabledModeInput &&
    commandDisabledMessageInput &&
    tokenToggleButton
  );
  if (!requiredNodesReady) {
    return;
  }

  const QQ_ID_PATTERN = /^\d{5,20}$/;
  const SHOW_ICON_SVG = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>
  `;
  const HIDE_ICON_SVG = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-11-7-11-7a21.76 21.76 0 0 1 5.06-5.94"></path>
      <path d="M9.9 4.24A10.93 10.93 0 0 1 12 4c7 0 11 7 11 7a21.86 21.86 0 0 1-3.12 4.36"></path>
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"></path>
      <path d="M1 1l22 22"></path>
    </svg>
  `;

  let tokenVisible = false;

  const setStatus = (message, type = "info") => {
    const text = String(message || "").trim();
    if (!text) {
      statusNode.className = "alert hidden";
      statusMessageNode.textContent = "";
      return;
    }
    const normalizedType = ["success", "error", "warning", "info"].includes(type)
      ? type
      : "info";
    statusNode.className = `alert ${normalizedType}`;
    statusMessageNode.textContent = text;
  };

  const setRestartAlert = (fields) => {
    if (!Array.isArray(fields) || fields.length === 0) {
      restartAlertNode.classList.add("hidden");
      restartMessageNode.textContent = "";
      return;
    }
    restartAlertNode.classList.remove("hidden");
    restartMessageNode.textContent = `以下配置需重启机器人后生效：${fields.join("、")}`;
  };

  const parseJsonSafe = async (response) => {
    try {
      return await response.json();
    } catch (_error) {
      return null;
    }
  };

  const readErrorMessage = (payload, fallback) => {
    if (payload && typeof payload.message === "string" && payload.message.trim()) {
      return payload.message.trim();
    }
    return fallback;
  };

  const setTokenButtonIcon = (visible) => {
    tokenToggleButton.innerHTML = visible ? HIDE_ICON_SVG : SHOW_ICON_SVG;
    tokenToggleButton.title = visible ? "隐藏 Token" : "显示 Token";
    tokenToggleButton.setAttribute("aria-label", tokenToggleButton.title);
    onebotAccessTokenInput.type = visible ? "text" : "password";
  };

  const parseJsonArrayField = (fieldLabel, rawText) => {
    const text = String(rawText || "").trim();
    if (!text) {
      throw new Error(`${fieldLabel} 不能为空`);
    }
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (_error) {
      throw new Error(`${fieldLabel} 必须是 JSON 数组`);
    }
    if (!Array.isArray(parsed)) {
      throw new Error(`${fieldLabel} 必须是 JSON 数组`);
    }
    return parsed.map((item) => String(item).trim());
  };

  const validateWsUrls = (values) => {
    for (const value of values) {
      if (!value) {
        throw new Error("ONEBOT_WS_URLS 不能包含空项");
      }
      let parsed;
      try {
        parsed = new URL(value);
      } catch (_error) {
        throw new Error("ONEBOT_WS_URLS 必须是 ws/wss URL");
      }
      if (!["ws:", "wss:"].includes(parsed.protocol)) {
        throw new Error("ONEBOT_WS_URLS 必须是 ws/wss URL");
      }
    }
  };

  const validateQqIdList = (fieldLabel, values) => {
    for (const value of values) {
      if (!QQ_ID_PATTERN.test(value)) {
        throw new Error(`${fieldLabel} 仅支持 5-20 位数字`);
      }
    }
  };

  const buildPayload = () => {
    const onebotWsUrls = parseJsonArrayField("ONEBOT_WS_URLS", onebotWsUrlsInput.value);
    validateWsUrls(onebotWsUrls);

    const ownerId = parseJsonArrayField("OWNER_ID", ownerIdInput.value);
    validateQqIdList("OWNER_ID", ownerId);

    const groupId = parseJsonArrayField("GROUP_ID", groupIdInput.value);
    validateQqIdList("GROUP_ID", groupId);

    const onebotAccessToken = String(onebotAccessTokenInput.value || "").trim();
    if (!onebotAccessToken) {
      throw new Error("ONEBOT_ACCESS_TOKEN 不能为空");
    }

    const webServerHost = String(webServerHostInput.value || "").trim();
    if (!webServerHost) {
      throw new Error("WEB_SERVER_HOST 不能为空");
    }

    const webServerPortText = String(webServerPortInput.value || "").trim();
    if (!webServerPortText) {
      throw new Error("WEB_SERVER_PORT 不能为空");
    }
    const webServerPort = Number(webServerPortText);
    if (!Number.isInteger(webServerPort) || webServerPort < 1 || webServerPort > 65535) {
      throw new Error("WEB_SERVER_PORT 范围必须在 1-65535");
    }

    const baseUrl = String(webServerPublicBaseUrlInput.value || "").trim();
    if (!baseUrl) {
      throw new Error("WEB_SERVER_PUBLIC_BASE_URL 不能为空");
    }
    let parsedBaseUrl;
    try {
      parsedBaseUrl = new URL(baseUrl);
    } catch (_error) {
      throw new Error("WEB_SERVER_PUBLIC_BASE_URL 必须是 http/https URL");
    }
    if (!["http:", "https:"].includes(parsedBaseUrl.protocol)) {
      throw new Error("WEB_SERVER_PUBLIC_BASE_URL 必须是 http/https URL");
    }

    const commandDisabledMode = String(commandDisabledModeInput.value || "").trim().toLowerCase();
    if (!["reply", "silent"].includes(commandDisabledMode)) {
      throw new Error("COMMAND_DISABLED_MODE 仅支持 reply 或 silent");
    }

    const commandDisabledMessage = String(commandDisabledMessageInput.value || "").trim();
    if (!commandDisabledMessage) {
      throw new Error("COMMAND_DISABLED_MESSAGE 不能为空");
    }

    return {
      onebot_ws_urls: onebotWsUrls,
      onebot_access_token: onebotAccessToken,
      owner_id: ownerId,
      group_id: groupId,
      web_server_host: webServerHost,
      web_server_port: webServerPort,
      web_server_public_base_url: parsedBaseUrl.toString().replace(/\/$/, ""),
      command_disabled_mode: commandDisabledMode,
      command_disabled_message: commandDisabledMessage,
    };
  };

  const setStats = (meta) => {
    const hotFields = Array.isArray(meta?.hot_apply_fields) ? meta.hot_apply_fields : [];
    const restartFields = Array.isArray(meta?.restart_required_fields)
      ? meta.restart_required_fields
      : [];
    statHotNode.textContent = String(hotFields.length);
    statRestartNode.textContent = String(restartFields.length);
  };

  const fillForm = (data) => {
    onebotWsUrlsInput.value = JSON.stringify(data.onebot_ws_urls ?? [], null, 2);
    onebotAccessTokenInput.value = String(data.onebot_access_token ?? "");
    ownerIdInput.value = JSON.stringify(data.owner_id ?? [], null, 2);
    groupIdInput.value = JSON.stringify(data.group_id ?? [], null, 2);
    webServerHostInput.value = String(data.web_server_host ?? "");
    webServerPortInput.value = String(data.web_server_port ?? "");
    webServerPublicBaseUrlInput.value = String(data.web_server_public_base_url ?? "");
    commandDisabledModeInput.value = String(data.command_disabled_mode ?? "reply");
    commandDisabledMessageInput.value = String(data.command_disabled_message ?? "");
  };

  const loadSettings = async () => {
    setStatus("正在加载设置...", "info");
    setRestartAlert([]);
    try {
      const response = await fetch("/webui/api/settings", {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      const payload = await parseJsonSafe(response);
      if (!response.ok || !payload || payload.ok !== true || !payload.data) {
        throw new Error(readErrorMessage(payload, `加载失败（HTTP ${response.status}）`));
      }
      fillForm(payload.data);
      setStats(payload.meta || {});
      setStatus("设置加载完成", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "加载失败";
      setStatus(message, "error");
    }
  };

  const saveSettings = async () => {
    let data;
    try {
      data = buildPayload();
    } catch (error) {
      const message = error instanceof Error ? error.message : "表单校验失败";
      setStatus(message, "error");
      return;
    }

    saveButton.disabled = true;
    setStatus("正在保存...", "warning");
    try {
      const response = await fetch("/webui/api/settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ data }),
      });
      const payload = await parseJsonSafe(response);
      if (!response.ok || !payload || payload.ok !== true) {
        throw new Error(readErrorMessage(payload, "保存失败"));
      }

      const applied = Array.isArray(payload.applied_now_fields)
        ? payload.applied_now_fields
        : [];
      const restartRequired = Array.isArray(payload.restart_required_fields)
        ? payload.restart_required_fields
        : [];
      const applyText = applied.length
        ? `即时生效：${applied.join("、")}`
        : "即时生效：无";
      setStatus(`保存成功。${applyText}`, "success");
      setRestartAlert(restartRequired);
    } catch (error) {
      const message = error instanceof Error ? error.message : "保存失败";
      setStatus(message, "error");
      setRestartAlert([]);
    } finally {
      saveButton.disabled = false;
    }
  };

  reloadButton.addEventListener("click", () => {
    void loadSettings();
  });

  saveButton.addEventListener("click", () => {
    void saveSettings();
  });

  tokenToggleButton.addEventListener("click", () => {
    tokenVisible = !tokenVisible;
    setTokenButtonIcon(tokenVisible);
  });

  setTokenButtonIcon(false);
  void loadSettings();
})();
