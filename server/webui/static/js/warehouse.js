(function () {
  "use strict";

  const api = window.NextBotWebUIApi;
  if (!api) {
    console.error("NextBotWebUIApi 未加载");
    return;
  }

  const state = {
    user: null,           // { user_id, user_name }
    capacity: 100,
    used: 0,
    slots: new Map(),     // slot_index -> { item_id, prefix_id, quantity, min_tier, min_tier_label }
    tiers: [],            // [{ key, label }]
    editingSlot: null,    // current slot_index in modal
  };

  const itemNameMap = new Map();
  const prefixNameMap = new Map();

  const els = {
    searchInput: null,
    searchDropdown: null,
    summary: null,
    summaryName: null,
    summaryQq: null,
    summaryUsed: null,
    summaryCapacity: null,
    gridCard: null,
    grid: null,
    empty: null,
    alert: null,
    modal: null,
    modalTitle: null,
    modalAlert: null,
    modalForm: null,
    modalClose: null,
    modalCancel: null,
    modalSave: null,
    modalDelete: null,
    fieldSlot: null,
    fieldItemId: null,
    fieldPrefixId: null,
    fieldQuantity: null,
    fieldValue: null,
    fieldMinTier: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function clearChildren(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function showAlert(text, kind) {
    if (!els.alert) return;
    els.alert.textContent = text;
    els.alert.style.display = "block";
    els.alert.style.background = kind === "error" ? "#fee2e2" : "#dcfce7";
    els.alert.style.color = kind === "error" ? "#991b1b" : "#166534";
    els.alert.style.border = "1px solid " + (kind === "error" ? "#fecaca" : "#bbf7d0");
  }

  function clearAlert() {
    if (!els.alert) return;
    els.alert.style.display = "none";
    els.alert.textContent = "";
  }

  function showModalAlert(text) {
    if (!els.modalAlert) return;
    els.modalAlert.textContent = text;
    els.modalAlert.style.display = "block";
    els.modalAlert.style.background = "#fee2e2";
    els.modalAlert.style.color = "#991b1b";
    els.modalAlert.style.border = "1px solid #fecaca";
  }

  function clearModalAlert() {
    if (!els.modalAlert) return;
    els.modalAlert.style.display = "none";
    els.modalAlert.textContent = "";
  }

  async function loadDicts() {
    try {
      const [itemRes, prefixRes] = await Promise.all([
        fetch("/assets/dicts/item.json"),
        fetch("/assets/dicts/prefix.json"),
      ]);
      if (itemRes.ok) {
        const list = await itemRes.json();
        if (Array.isArray(list)) list.forEach(function (e) {
          const id = Number(e && e.id || 0);
          const name = String(e && e.name || "").trim();
          if (id > 0 && name) itemNameMap.set(id, name);
        });
      }
      if (prefixRes.ok) {
        const list = await prefixRes.json();
        if (Array.isArray(list)) list.forEach(function (e) {
          const id = Number(e && e.id || 0);
          const name = String(e && e.name || "").trim();
          if (id > 0 && name) prefixNameMap.set(id, name);
        });
      }
    } catch (e) { /* ignore — will fall back to numeric ids */ }
  }

  async function loadTiers() {
    try {
      const payload = await api.apiRequest("/webui/api/warehouse/tiers", {
        method: "GET",
        headers: { "Accept": "application/json" },
        action: "加载",
        expectedStatus: 200,
      });
      const data = api.unwrapData(payload);
      state.tiers = Array.isArray(data) ? data : [];
    } catch (err) {
      showAlert(err && err.message ? err.message : "加载进度列表失败", "error");
    }
  }

  function populateTierSelect(selectedKey) {
    if (!els.fieldMinTier) return;
    clearChildren(els.fieldMinTier);
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "请选择进度";
    placeholder.disabled = true;
    if (!selectedKey) placeholder.selected = true;
    els.fieldMinTier.appendChild(placeholder);
    state.tiers.forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t.key;
      opt.textContent = t.label;
      if (selectedKey && t.key === selectedKey) opt.selected = true;
      els.fieldMinTier.appendChild(opt);
    });
  }

  async function loadWarehouse(userId) {
    clearAlert();
    if (!userId) {
      showAlert("加载仓库失败，请输入用户 QQ 或用户名", "error");
      return;
    }
    try {
      const payload = await api.apiRequest(
        "/webui/api/warehouse?user_id=" + encodeURIComponent(userId),
        {
          method: "GET",
          headers: { "Accept": "application/json" },
          action: "加载",
          expectedStatus: 200,
        }
      );
      const data = api.unwrapData(payload);
      state.user = { user_id: data.user_id, user_name: data.user_name };
      state.capacity = Number(data.capacity || 100);
      state.used = Number(data.used || 0);
      state.slots.clear();
      (data.slots || []).forEach(function (s) {
        state.slots.set(Number(s.slot_index), s);
      });
      renderSummary();
      renderGrid();
    } catch (err) {
      showAlert(err && err.message ? err.message : "加载仓库失败", "error");
      hideAll();
    }
  }

  function hideAll() {
    if (els.summary) els.summary.style.display = "none";
    if (els.gridCard) els.gridCard.style.display = "none";
    if (els.empty) els.empty.style.display = "block";
  }

  function renderSummary() {
    if (!state.user) return hideAll();
    els.summary.style.display = "block";
    els.summaryName.textContent = state.user.user_name || "(无用户名)";
    els.summaryQq.textContent = "（QQ：" + state.user.user_id + "）";
    els.summaryUsed.textContent = String(state.used);
    els.summaryCapacity.textContent = String(state.capacity);
    els.empty.style.display = "none";
  }

  function renderGrid() {
    if (!state.user) return;
    els.gridCard.style.display = "block";
    clearChildren(els.grid);
    for (let i = 1; i <= state.capacity; i++) {
      const slot = state.slots.get(i);
      const occupied = !!slot;

      const cell = document.createElement("div");
      cell.style.position = "relative";
      cell.style.aspectRatio = "4 / 5";
      cell.style.border = "1px solid " + (occupied ? "#fcd34d" : "#e2e8f0");
      cell.style.background = occupied ? "#fffbeb" : "#fafaf9";
      cell.style.borderRadius = "8px";
      cell.style.padding = "14px 4px 4px 4px";
      cell.style.display = "flex";
      cell.style.flexDirection = "column";
      cell.style.alignItems = "center";
      cell.style.justifyContent = "center";
      cell.style.gap = "2px";
      cell.style.cursor = "pointer";
      cell.style.transition = "transform 0.1s, box-shadow 0.1s";
      cell.style.overflow = "hidden";
      cell.style.minWidth = "0";
      cell.style.minHeight = "0";
      cell.onmouseenter = function () {
        cell.style.transform = "scale(1.04)";
        cell.style.boxShadow = "0 4px 12px rgba(0,0,0,0.08)";
        cell.style.zIndex = "2";
      };
      cell.onmouseleave = function () {
        cell.style.transform = "";
        cell.style.boxShadow = "";
        cell.style.zIndex = "";
      };
      cell.onclick = function () { openModal(i, slot); };

      const idEl = document.createElement("div");
      idEl.textContent = "#" + i;
      idEl.style.position = "absolute";
      idEl.style.top = "3px";
      idEl.style.left = "5px";
      idEl.style.fontSize = "9px";
      idEl.style.fontWeight = "700";
      idEl.style.color = "#94a3b8";
      cell.appendChild(idEl);

      const iconWrap = document.createElement("div");
      iconWrap.style.display = "flex";
      iconWrap.style.alignItems = "center";
      iconWrap.style.justifyContent = "center";
      iconWrap.style.flexShrink = "0";
      if (occupied) {
        const img = document.createElement("img");
        img.src = "/assets/items/Item_" + slot.item_id + ".png";
        img.alt = String(slot.item_id);
        img.style.width = "40px";
        img.style.height = "40px";
        img.style.maxWidth = "100%";
        img.style.objectFit = "contain";
        img.style.objectFit = "contain";
        img.style.imageRendering = "pixelated";
        img.onerror = function () { img.style.display = "none"; };
        iconWrap.appendChild(img);
      } else {
        const empty = document.createElement("div");
        empty.textContent = "+";
        empty.style.fontSize = "20px";
        empty.style.color = "#cbd5e1";
        iconWrap.appendChild(empty);
      }
      cell.appendChild(iconWrap);

      if (occupied) {
        if (Number(slot.quantity || 0) > 1) {
          const stack = document.createElement("div");
          stack.textContent = "×" + slot.quantity;
          stack.style.position = "absolute";
          stack.style.top = "2px";
          stack.style.right = "4px";
          stack.style.fontSize = "9px";
          stack.style.fontWeight = "800";
          stack.style.padding = "1px 4px";
          stack.style.background = "#fffbeb";
          stack.style.color = "#b45309";
          stack.style.border = "1px solid #fde68a";
          stack.style.borderRadius = "4px";
          cell.appendChild(stack);
        }

        const itemName = itemNameMap.get(Number(slot.item_id)) || ("ID:" + slot.item_id);
        const prefixId = Number(slot.prefix_id || 0);
        const prefixName = prefixId > 0 ? (prefixNameMap.get(prefixId) || "前缀ID:" + prefixId) : "";

        if (prefixName) {
          const prefixEl = document.createElement("div");
          prefixEl.textContent = prefixName;
          prefixEl.style.fontSize = "8px";
          prefixEl.style.fontWeight = "700";
          prefixEl.style.color = "#b45309";
          prefixEl.style.overflow = "hidden";
          prefixEl.style.textOverflow = "ellipsis";
          prefixEl.style.whiteSpace = "nowrap";
          prefixEl.style.lineHeight = "1.2";
          prefixEl.style.maxWidth = "100%";
          prefixEl.style.textAlign = "center";
          cell.appendChild(prefixEl);
        }

        const nameEl = document.createElement("div");
        nameEl.textContent = itemName;
        nameEl.title = (prefixName ? prefixName + " " : "") + itemName + " · " + (slot.min_tier_label || slot.min_tier || "");
        nameEl.style.fontSize = "9px";
        nameEl.style.fontWeight = "700";
        nameEl.style.color = "#1e293b";
        nameEl.style.overflow = "hidden";
        nameEl.style.textOverflow = "ellipsis";
        nameEl.style.whiteSpace = "nowrap";
        nameEl.style.lineHeight = "1.2";
        nameEl.style.maxWidth = "100%";
        nameEl.style.textAlign = "center";
        cell.appendChild(nameEl);

        if (slot.min_tier_label) {
          const tierEl = document.createElement("div");
          tierEl.textContent = slot.min_tier_label;
          tierEl.style.fontSize = "8px";
          tierEl.style.fontWeight = "600";
          tierEl.style.color = "#b45309";
          tierEl.style.background = "#fef3c7";
          tierEl.style.padding = "1px 4px";
          tierEl.style.borderRadius = "4px";
          tierEl.style.marginTop = "1px";
          tierEl.style.maxWidth = "100%";
          tierEl.style.overflow = "hidden";
          tierEl.style.textOverflow = "ellipsis";
          tierEl.style.whiteSpace = "nowrap";
          cell.appendChild(tierEl);
        }

        if (Number(slot.value || 0) > 0) {
          const valueEl = document.createElement("div");
          valueEl.textContent = "💰 " + slot.value;
          valueEl.style.fontSize = "9px";
          valueEl.style.fontWeight = "700";
          valueEl.style.color = "#b45309";
          valueEl.style.lineHeight = "1.2";
          valueEl.style.marginTop = "1px";
          valueEl.style.maxWidth = "100%";
          valueEl.style.overflow = "hidden";
          valueEl.style.textOverflow = "ellipsis";
          valueEl.style.whiteSpace = "nowrap";
          valueEl.style.textAlign = "center";
          cell.appendChild(valueEl);
        }
      }

      els.grid.appendChild(cell);
    }
  }

  function openModal(slotIndex, slot) {
    state.editingSlot = slotIndex;
    clearModalAlert();
    els.modalTitle.textContent = slot ? "编辑物品" : "添加物品";
    els.fieldSlot.value = "#" + slotIndex;
    els.fieldItemId.value = slot ? String(slot.item_id) : "";
    els.fieldPrefixId.value = slot ? String(slot.prefix_id) : "0";
    els.fieldQuantity.value = slot ? String(slot.quantity) : "1";
    els.fieldValue.value = slot ? String(slot.value || 0) : "0";
    populateTierSelect(slot ? slot.min_tier : "");
    els.modalDelete.style.display = slot ? "inline-block" : "none";
    els.modal.style.display = "flex";
  }

  function closeModal() {
    state.editingSlot = null;
    els.modal.style.display = "none";
    clearModalAlert();
  }

  async function saveModal(ev) {
    ev.preventDefault();
    if (!state.user || !state.editingSlot) return;
    clearModalAlert();

    const itemId = parseInt(els.fieldItemId.value, 10);
    const prefixId = parseInt(els.fieldPrefixId.value, 10);
    const quantity = parseInt(els.fieldQuantity.value, 10);
    const value = parseInt(els.fieldValue.value, 10);
    const minTier = els.fieldMinTier.value;

    if (isNaN(itemId) || itemId < 1) return showModalAlert("物品 ID 必须为正整数");
    if (isNaN(prefixId) || prefixId < 0) return showModalAlert("前缀 ID 必须为非负整数");
    if (isNaN(quantity) || quantity < 1) return showModalAlert("数量必须为正整数");
    if (isNaN(value) || value < 0) return showModalAlert("单价必须为非负整数");
    if (!minTier) return showModalAlert("请选择最低进度");

    try {
      await api.apiRequest(
        "/webui/api/warehouse/" + encodeURIComponent(state.user.user_id) + "/" + state.editingSlot,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_id: itemId, prefix_id: prefixId, quantity: quantity, value: value, min_tier: minTier }),
          action: "保存",
          expectedStatus: 200,
        }
      );
      closeModal();
      await loadWarehouse(state.user.user_id);
      showAlert("保存成功，#" + (state.editingSlot || ""), "success");
    } catch (err) {
      showModalAlert(err && err.message ? err.message : "保存失败");
    }
  }

  async function deleteSlot() {
    if (!state.user || !state.editingSlot) return;
    if (!confirm("确认清空 #" + state.editingSlot + " 吗？")) return;
    clearModalAlert();
    try {
      await api.apiRequest(
        "/webui/api/warehouse/" + encodeURIComponent(state.user.user_id) + "/" + state.editingSlot,
        {
          method: "DELETE",
          headers: { "Accept": "application/json" },
          action: "删除",
          expectedStatus: 200,
        }
      );
      const slotShown = state.editingSlot;
      closeModal();
      await loadWarehouse(state.user.user_id);
      showAlert("删除成功，#" + slotShown, "success");
    } catch (err) {
      showModalAlert(err && err.message ? err.message : "删除失败");
    }
  }

  function bindElements() {
    els.searchInput = $("wh-search-input");
    els.searchDropdown = $("wh-search-dropdown");
    els.summary = $("wh-summary");
    els.summaryName = $("wh-summary-name");
    els.summaryQq = $("wh-summary-qq");
    els.summaryUsed = $("wh-summary-used");
    els.summaryCapacity = $("wh-summary-capacity");
    els.gridCard = $("wh-grid-card");
    els.grid = $("wh-grid");
    els.empty = $("wh-empty");
    els.alert = $("wh-alert");
    els.modal = $("wh-modal");
    els.modalTitle = $("wh-modal-title");
    els.modalAlert = $("wh-modal-alert");
    els.modalForm = $("wh-modal-form");
    els.modalClose = $("wh-modal-close");
    els.modalCancel = $("wh-modal-cancel");
    els.modalSave = $("wh-modal-save");
    els.modalDelete = $("wh-modal-delete");
    els.fieldSlot = $("wh-field-slot");
    els.fieldItemId = $("wh-field-item-id");
    els.fieldPrefixId = $("wh-field-prefix-id");
    els.fieldQuantity = $("wh-field-quantity");
    els.fieldValue = $("wh-field-value");
    els.fieldMinTier = $("wh-field-min-tier");
  }

  let searchTimer = null;
  let lastSearchKeyword = "";

  function showDropdown() {
    if (els.searchDropdown) els.searchDropdown.style.display = "block";
  }

  function hideDropdown() {
    if (els.searchDropdown) els.searchDropdown.style.display = "none";
  }

  function renderDropdownMessage(text) {
    if (!els.searchDropdown) return;
    clearChildren(els.searchDropdown);
    const msg = document.createElement("div");
    msg.textContent = text;
    msg.style.padding = "10px 14px";
    msg.style.color = "#94a3b8";
    msg.style.fontSize = "13px";
    els.searchDropdown.appendChild(msg);
    showDropdown();
  }

  function renderDropdownResults(users) {
    if (!els.searchDropdown) return;
    clearChildren(els.searchDropdown);
    if (!users.length) {
      renderDropdownMessage("无匹配用户");
      return;
    }
    users.forEach(function (u) {
      const item = document.createElement("div");
      item.style.padding = "8px 14px";
      item.style.cursor = "pointer";
      item.style.borderBottom = "1px solid #f1f5f9";
      item.style.display = "flex";
      item.style.justifyContent = "space-between";
      item.style.alignItems = "center";
      item.onmouseenter = function () { item.style.background = "#f8fafc"; };
      item.onmouseleave = function () { item.style.background = ""; };
      item.onclick = function () {
        els.searchInput.value = String(u.name || "");
        hideDropdown();
        loadWarehouse(String(u.user_id));
      };

      const nameSpan = document.createElement("span");
      nameSpan.textContent = String(u.name || "(无用户名)");
      nameSpan.style.fontWeight = "600";
      nameSpan.style.color = "#1e293b";
      item.appendChild(nameSpan);

      const qqSpan = document.createElement("span");
      qqSpan.textContent = String(u.user_id || "");
      qqSpan.style.fontSize = "12px";
      qqSpan.style.color = "#94a3b8";
      item.appendChild(qqSpan);

      els.searchDropdown.appendChild(item);
    });
    showDropdown();
  }

  async function searchUsers(keyword) {
    if (lastSearchKeyword === keyword) return;
    lastSearchKeyword = keyword;
    try {
      const url = "/webui/api/users?per_page=20" + (keyword ? "&q=" + encodeURIComponent(keyword) : "");
      const payload = await api.apiRequest(url, {
        method: "GET",
        headers: { "Accept": "application/json" },
        action: "搜索用户",
        expectedStatus: 200,
      });
      const users = api.unwrapData(payload) || [];
      // Only render if the keyword still matches what's in the input
      const current = (els.searchInput.value || "").trim().toLowerCase();
      if (current === keyword) {
        renderDropdownResults(Array.isArray(users) ? users.slice(0, 20) : []);
      }
    } catch (err) {
      renderDropdownMessage(err && err.message ? err.message : "搜索失败");
    }
  }

  function bindEvents() {
    els.searchInput.addEventListener("input", function () {
      const keyword = (els.searchInput.value || "").trim().toLowerCase();
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(function () { searchUsers(keyword); }, 200);
    });
    els.searchInput.addEventListener("focus", function () {
      const keyword = (els.searchInput.value || "").trim().toLowerCase();
      lastSearchKeyword = "__force__";
      searchUsers(keyword);
    });
    document.addEventListener("click", function (ev) {
      const wrap = $("wh-search-wrap");
      if (wrap && !wrap.contains(ev.target)) hideDropdown();
    });
    els.searchInput.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hideDropdown();
    });

    els.modalClose.addEventListener("click", closeModal);
    els.modalCancel.addEventListener("click", closeModal);
    els.modal.addEventListener("click", function (ev) {
      if (ev.target === els.modal) closeModal();
    });
    els.modalForm.addEventListener("submit", saveModal);
    els.modalDelete.addEventListener("click", deleteSlot);
  }

  document.addEventListener("DOMContentLoaded", async function () {
    bindElements();
    bindEvents();
    await Promise.all([loadDicts(), loadTiers()]);

    // Auto-load if `?user_id=X` is present in URL
    try {
      const params = new URLSearchParams(window.location.search);
      const presetUserId = (params.get("user_id") || "").trim();
      if (presetUserId) {
        els.searchInput.value = presetUserId;
        await loadWarehouse(presetUserId);
        if (state.user && state.user.user_name) {
          els.searchInput.value = state.user.user_name;
        }
      }
    } catch (e) { /* ignore */ }
  });
})();
