(() => {
  const reloadButton = document.getElementById("reload-btn");
  const saveButton = document.getElementById("save-all-btn");
  const statusNode = document.getElementById("status");
  const loadingNode = document.getElementById("loading");
  const emptyNode = document.getElementById("empty");
  const groupsNode = document.getElementById("groups");

  let commandStates = [];

  const setStatus = (message, type = "") => {
    if (!statusNode) return;
    statusNode.textContent = message || "";
    statusNode.className = `status${type ? ` ${type}` : ""}`;
  };

  const cloneValue = (value) => JSON.parse(JSON.stringify(value));

  const parseFormValue = (schema, inputNode) => {
    const valueType = schema.type;

    if (valueType === "bool") {
      return Boolean(inputNode.checked);
    }
    if (valueType === "int") {
      const text = String(inputNode.value || "").trim();
      if (!text) {
        throw new Error("需要整数");
      }
      const parsed = Number.parseInt(text, 10);
      if (!Number.isFinite(parsed)) {
        throw new Error("需要整数");
      }
      return parsed;
    }
    if (valueType === "float") {
      const text = String(inputNode.value || "").trim();
      if (!text) {
        throw new Error("需要数字");
      }
      const parsed = Number.parseFloat(text);
      if (!Number.isFinite(parsed)) {
        throw new Error("需要数字");
      }
      return parsed;
    }
    return String(inputNode.value || "");
  };

  const renderCommands = () => {
    if (!groupsNode || !loadingNode || !emptyNode) return;

    groupsNode.innerHTML = "";
    loadingNode.classList.add("hidden");

    if (!commandStates.length) {
      emptyNode.classList.remove("hidden");
      return;
    }

    emptyNode.classList.add("hidden");

    const groupMap = new Map();
    for (const item of commandStates) {
      const groupName = item.module_path || "unknown";
      if (!groupMap.has(groupName)) {
        groupMap.set(groupName, []);
      }
      groupMap.get(groupName).push(item);
    }

    const sortedGroups = Array.from(groupMap.keys()).sort((a, b) => a.localeCompare(b));
    for (const groupName of sortedGroups) {
      const container = document.createElement("section");
      container.className = "group";

      const head = document.createElement("div");
      head.className = "group-head";
      head.textContent = groupName;
      container.appendChild(head);

      const items = groupMap.get(groupName) || [];
      items.sort((a, b) => a.display_name.localeCompare(b.display_name));

      for (const command of items) {
        const itemNode = document.createElement("article");
        itemNode.className = "command-item";
        itemNode.dataset.commandKey = command.command_key;

        const headNode = document.createElement("div");
        headNode.className = "command-head";

        const nameNode = document.createElement("span");
        nameNode.className = "command-name";
        nameNode.textContent = command.display_name;

        const keyNode = document.createElement("span");
        keyNode.className = "command-key";
        keyNode.textContent = command.command_key;

        const switchNode = document.createElement("label");
        switchNode.className = "switch";

        const enabledInput = document.createElement("input");
        enabledInput.type = "checkbox";
        enabledInput.checked = Boolean(command.enabled);
        enabledInput.dataset.role = "enabled";

        const switchText = document.createElement("span");
        switchText.textContent = "启用";

        switchNode.appendChild(enabledInput);
        switchNode.appendChild(switchText);

        headNode.appendChild(nameNode);
        headNode.appendChild(keyNode);
        headNode.appendChild(switchNode);
        itemNode.appendChild(headNode);

        if (command.permission) {
          const permNode = document.createElement("div");
          permNode.className = "command-perm";
          permNode.textContent = `权限: ${command.permission}`;
          itemNode.appendChild(permNode);
        }

        const schema = command.param_schema || {};
        const paramNames = Object.keys(schema);
        if (paramNames.length) {
          const paramsNode = document.createElement("div");
          paramsNode.className = "params";

          for (const paramName of paramNames) {
            const definition = schema[paramName] || {};
            const paramNode = document.createElement("section");
            paramNode.className = "param";

            const labelNode = document.createElement("p");
            labelNode.className = "param-label";
            labelNode.textContent = definition.label || paramName;
            paramNode.appendChild(labelNode);

            if (definition.description) {
              const descNode = document.createElement("p");
              descNode.className = "param-desc";
              descNode.textContent = definition.description;
              paramNode.appendChild(descNode);
            }

            let inputNode;
            const currentValue = command.param_values?.[paramName];

            if (definition.type === "bool") {
              inputNode = document.createElement("input");
              inputNode.type = "checkbox";
              inputNode.checked = Boolean(currentValue);
            } else if (Array.isArray(definition.enum) && definition.enum.length) {
              inputNode = document.createElement("select");
              inputNode.className = "select";
              for (const enumValue of definition.enum) {
                const option = document.createElement("option");
                option.value = String(enumValue);
                option.textContent = String(enumValue);
                inputNode.appendChild(option);
              }
              inputNode.value = String(currentValue ?? "");
            } else {
              inputNode = document.createElement("input");
              inputNode.className = "input";
              if (definition.type === "int" || definition.type === "float") {
                inputNode.type = "number";
                if (definition.type === "float") {
                  inputNode.step = "any";
                } else {
                  inputNode.step = "1";
                }
                if (definition.min !== undefined) {
                  inputNode.min = String(definition.min);
                }
                if (definition.max !== undefined) {
                  inputNode.max = String(definition.max);
                }
                inputNode.value = String(currentValue ?? "");
              } else {
                inputNode.type = "text";
                inputNode.value = String(currentValue ?? "");
              }
            }

            inputNode.dataset.role = "param";
            inputNode.dataset.paramName = paramName;
            inputNode.dataset.paramSchema = JSON.stringify(definition);
            paramNode.appendChild(inputNode);
            paramsNode.appendChild(paramNode);
          }

          itemNode.appendChild(paramsNode);
        }

        container.appendChild(itemNode);
      }

      groupsNode.appendChild(container);
    }
  };

  const collectCommandPayload = () => {
    if (!groupsNode) {
      return [];
    }

    const entries = [];
    const commandNodes = groupsNode.querySelectorAll(".command-item");
    for (const node of commandNodes) {
      const commandKey = node.dataset.commandKey;
      if (!commandKey) {
        continue;
      }

      const enabledInput = node.querySelector("input[data-role='enabled']");
      const params = {};
      const paramNodes = node.querySelectorAll("[data-role='param']");

      for (const inputNode of paramNodes) {
        const paramName = inputNode.dataset.paramName;
        const schemaRaw = inputNode.dataset.paramSchema;
        if (!paramName || !schemaRaw) {
          continue;
        }

        let schema;
        try {
          schema = JSON.parse(schemaRaw);
        } catch (error) {
          throw new Error(`参数 schema 无效: ${paramName}`);
        }

        try {
          const value = parseFormValue(schema, inputNode);
          if (schema.required && schema.type === "string" && !String(value).trim()) {
            throw new Error("不能为空");
          }
          params[paramName] = value;
        } catch (error) {
          const message = error instanceof Error ? error.message : "参数格式错误";
          throw new Error(`${commandKey}.${paramName}: ${message}`);
        }
      }

      entries.push({
        command_key: commandKey,
        enabled: Boolean(enabledInput?.checked),
        params,
      });
    }

    return entries;
  };

  const loadCommands = async () => {
    if (loadingNode) {
      loadingNode.classList.remove("hidden");
    }
    setStatus("");

    try {
      const response = await fetch("/webui/api/commands", {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });
      if (!response.ok) {
        throw new Error(`加载失败 (${response.status})`);
      }

      const data = await response.json();
      const commands = Array.isArray(data.commands) ? data.commands : [];
      commandStates = cloneValue(commands);
      renderCommands();
      setStatus(`已加载 ${commandStates.length} 条命令`, "success");
    } catch (error) {
      renderCommands();
      const message = error instanceof Error ? error.message : "加载失败";
      setStatus(message, "error");
    }
  };

  const saveCommands = async () => {
    if (!saveButton) {
      return;
    }

    let payload;
    try {
      payload = collectCommandPayload();
    } catch (error) {
      const message = error instanceof Error ? error.message : "参数校验失败";
      setStatus(message, "error");
      return;
    }

    saveButton.disabled = true;
    setStatus("保存中...");

    try {
      const response = await fetch("/webui/api/commands/batch", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ commands: payload }),
      });
      const data = await response.json();

      if (!response.ok || !data.ok) {
        let message = data.message || `保存失败 (${response.status})`;
        if (Array.isArray(data.errors) && data.errors.length) {
          const firstError = data.errors[0];
          if (firstError && typeof firstError === "object" && firstError.message) {
            message = String(firstError.message);
          }
        }
        throw new Error(message);
      }

      setStatus("保存成功，已即时生效", "success");
      await loadCommands();
    } catch (error) {
      const message = error instanceof Error ? error.message : "保存失败";
      setStatus(message, "error");
    } finally {
      saveButton.disabled = false;
    }
  };

  if (reloadButton) {
    reloadButton.addEventListener("click", () => {
      loadCommands();
    });
  }

  if (saveButton) {
    saveButton.addEventListener("click", () => {
      saveCommands();
    });
  }

  loadCommands();
})();
