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
    slots: new Map(),     // slot_index -> { item_id, prefix_id, quantity, min_tier, min_tier_label, value }
    tiers: [],            // [{ key, label }]
    editingSlot: null,    // current slot_index in modal
  };

  const TIER_RANK = new Map();   // tier key -> rank index for tier-chip styling

  const itemNameMap = new Map();
  const prefixNameMap = new Map();

  const els = {};

  function $(id) { return document.getElementById(id); }

  function clearChildren(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function showAlert(node, text, kind) {
    if (!node) return;
    const msg = node.querySelector(".alert-message") || node;
    msg.textContent = text;
    node.classList.remove("hidden", "success", "error");
    node.classList.add(kind === "error" ? "error" : "success");
  }

  function hideAlert(node) {
    if (!node) return;
    node.classList.add("hidden");
    const msg = node.querySelector(".alert-message");
    if (msg) msg.textContent = "";
  }

  function showModal(modal) {
    if (!modal) return;
    modal.classList.remove("hidden");
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.add("hidden");
  }

  // ---------- Data load ----------

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
    } catch (e) { /* fall back to numeric ids */ }
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
      // Rank index for tier-chip color (skip "none", first real boss = rank 0)
      TIER_RANK.clear();
      let rank = 0;
      state.tiers.forEach(function (t) {
        if (t.key === "none") {
          TIER_RANK.set(t.key, -1);
        } else {
          TIER_RANK.set(t.key, rank);
          rank += 1;
        }
      });
    } catch (err) {
      showAlert(els.alert, err && err.message ? err.message : "加载进度列表失败", "error");
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
    hideAlert(els.alert);
    if (!userId) {
      showAlert(els.alert, "加载仓库失败，请输入用户 QQ 或用户名", "error");
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
      showAlert(els.alert, err && err.message ? err.message : "加载仓库失败", "error");
      hideAll();
    }
  }

  function hideAll() {
    state.user = null;
    els.summary.classList.add("hidden");
    els.gridCard.classList.add("hidden");
    els.empty.classList.remove("hidden");
  }

  function renderSummary() {
    if (!state.user) return hideAll();
    els.summary.classList.remove("hidden");
    els.summaryName.textContent = state.user.user_name || "(无用户名)";
    els.summaryQq.textContent = state.user.user_id;
    els.summaryUsed.textContent = String(state.used);
    els.summaryCapacity.textContent = String(state.capacity);
    els.empty.classList.add("hidden");
  }

  function renderGrid() {
    if (!state.user) return;
    els.gridCard.classList.remove("hidden");
    clearChildren(els.grid);
    for (let i = 1; i <= state.capacity; i++) {
      els.grid.appendChild(renderSlot(i, state.slots.get(i)));
    }
  }

  function renderSlot(slotIndex, slot) {
    const occupied = !!slot;
    const cell = document.createElement("div");
    cell.className = "wh-slot" + (occupied ? " is-occupied" : "");
    cell.addEventListener("click", function () { openModal(slotIndex, slot); });

    const idEl = document.createElement("div");
    idEl.className = "wh-slot-id";
    idEl.textContent = "#" + slotIndex;
    cell.appendChild(idEl);

    const iconWrap = document.createElement("div");
    iconWrap.className = "wh-slot-icon";
    if (occupied) {
      const img = document.createElement("img");
      img.src = "/assets/items/Item_" + slot.item_id + ".png";
      img.alt = String(slot.item_id);
      img.addEventListener("error", function () { img.style.display = "none"; });
      iconWrap.appendChild(img);
    } else {
      const empty = document.createElement("div");
      empty.className = "wh-slot-empty-icon";
      empty.textContent = "+";
      iconWrap.appendChild(empty);
    }
    cell.appendChild(iconWrap);

    if (!occupied) return cell;

    if (Number(slot.quantity || 0) > 1) {
      const stack = document.createElement("div");
      stack.className = "wh-slot-stack";
      stack.textContent = "×" + slot.quantity;
      cell.appendChild(stack);
    }

    const itemName = itemNameMap.get(Number(slot.item_id)) || ("ID:" + slot.item_id);
    const prefixId = Number(slot.prefix_id || 0);
    const prefixName = prefixId > 0 ? (prefixNameMap.get(prefixId) || "前缀 ID:" + prefixId) : "";

    if (prefixName) {
      const prefixEl = document.createElement("div");
      prefixEl.className = "wh-slot-prefix";
      prefixEl.textContent = prefixName;
      cell.appendChild(prefixEl);
    }

    const nameEl = document.createElement("div");
    nameEl.className = "wh-slot-name";
    nameEl.textContent = itemName;
    nameEl.title = (prefixName ? prefixName + " " : "") + itemName + " · " + (slot.min_tier_label || slot.min_tier || "");
    cell.appendChild(nameEl);

    if (slot.min_tier_label && slot.min_tier !== "none") {
      const tierEl = document.createElement("div");
      const rank = TIER_RANK.has(String(slot.min_tier)) ? TIER_RANK.get(String(slot.min_tier)) : -1;
      tierEl.className = "tier-chip" + (rank >= 0 ? " tier-" + rank : " tier-none");
      tierEl.textContent = slot.min_tier_label;
      cell.appendChild(tierEl);
    }

    if (Number(slot.value || 0) > 0) {
      const valueEl = document.createElement("div");
      valueEl.className = "wh-slot-value";
      valueEl.textContent = "💰 " + slot.value;
      cell.appendChild(valueEl);
    }

    return cell;
  }

  // ---------- Modal ----------

  function openModal(slotIndex, slot) {
    state.editingSlot = slotIndex;
    hideAlert(els.modalAlert);
    els.modalTitle.textContent = slot ? "编辑物品" : "添加物品";
    els.fieldSlot.value = "#" + slotIndex;
    els.fieldItemId.value = slot ? String(slot.item_id) : "";
    els.fieldPrefixId.value = slot ? String(slot.prefix_id) : "0";
    els.fieldQuantity.value = slot ? String(slot.quantity) : "1";
    els.fieldValue.value = slot ? String(slot.value || 0) : "0";
    populateTierSelect(slot ? slot.min_tier : "");
    if (slot) {
      els.modalDelete.classList.remove("hidden");
    } else {
      els.modalDelete.classList.add("hidden");
    }
    showModal(els.modal);
    setTimeout(function () { els.fieldItemId.focus(); }, 30);
  }

  function closeModal() {
    state.editingSlot = null;
    hideModal(els.modal);
    hideAlert(els.modalAlert);
  }

  async function saveModal(ev) {
    ev.preventDefault();
    if (!state.user || !state.editingSlot) return;
    hideAlert(els.modalAlert);

    const itemId = parseInt(els.fieldItemId.value, 10);
    const prefixId = parseInt(els.fieldPrefixId.value, 10);
    const quantity = parseInt(els.fieldQuantity.value, 10);
    const value = parseInt(els.fieldValue.value, 10);
    const minTier = els.fieldMinTier.value;

    if (isNaN(itemId) || itemId < 1) return showAlert(els.modalAlert, "保存失败，物品 ID 必须为正整数", "error");
    if (isNaN(prefixId) || prefixId < 0) return showAlert(els.modalAlert, "保存失败，前缀 ID 必须为非负整数", "error");
    if (isNaN(quantity) || quantity < 1) return showAlert(els.modalAlert, "保存失败，数量必须为正整数", "error");
    if (isNaN(value) || value < 0) return showAlert(els.modalAlert, "保存失败，单价必须为非负整数", "error");
    if (!minTier) return showAlert(els.modalAlert, "保存失败，请选择最低进度", "error");

    try {
      await api.apiRequest(
        "/webui/api/warehouse/" + encodeURIComponent(state.user.user_id) + "/" + state.editingSlot,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            item_id: itemId, prefix_id: prefixId, quantity: quantity,
            value: value, min_tier: minTier,
          }),
          action: "保存",
          expectedStatus: 200,
        }
      );
      const slotShown = state.editingSlot;
      closeModal();
      await loadWarehouse(state.user.user_id);
      showAlert(els.alert, "保存成功，#" + slotShown, "success");
    } catch (err) {
      showAlert(els.modalAlert, err && err.message ? err.message : "保存失败", "error");
    }
  }

  function openDeleteModal() {
    if (!state.user || !state.editingSlot) return;
    hideAlert(els.deleteAlert);
    els.deleteSlot.textContent = "#" + state.editingSlot;
    showModal(els.deleteModal);
  }

  function closeDeleteModal() {
    hideModal(els.deleteModal);
  }

  async function confirmDelete() {
    if (!state.user || !state.editingSlot) return;
    hideAlert(els.deleteAlert);
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
      closeDeleteModal();
      closeModal();
      await loadWarehouse(state.user.user_id);
      showAlert(els.alert, "删除成功，#" + slotShown, "success");
    } catch (err) {
      showAlert(els.deleteAlert, err && err.message ? err.message : "删除失败", "error");
    }
  }

  // ---------- Search dropdown ----------

  let searchTimer = null;
  let lastSearchKeyword = "";

  function showDropdown() { els.searchDropdown.classList.remove("hidden"); }
  function hideDropdown() { els.searchDropdown.classList.add("hidden"); }

  function renderDropdownMessage(text) {
    if (!els.searchDropdown) return;
    clearChildren(els.searchDropdown);
    const msg = document.createElement("div");
    msg.className = "search-dropdown-empty";
    msg.textContent = text;
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
      item.className = "search-dropdown-item";
      item.addEventListener("click", function () {
        els.searchInput.value = String(u.name || "");
        hideDropdown();
        loadWarehouse(String(u.user_id));
      });

      const nameSpan = document.createElement("span");
      nameSpan.className = "name";
      nameSpan.textContent = String(u.name || "(无用户名)");
      item.appendChild(nameSpan);

      const qqSpan = document.createElement("span");
      qqSpan.className = "qq";
      qqSpan.textContent = String(u.user_id || "");
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
      const current = (els.searchInput.value || "").trim().toLowerCase();
      if (current === keyword) {
        renderDropdownResults(Array.isArray(users) ? users.slice(0, 20) : []);
      }
    } catch (err) {
      renderDropdownMessage(err && err.message ? err.message : "搜索失败");
    }
  }

  // ---------- Bind ----------

  function bindElements() {
    els.searchInput = $("wh-search-input");
    els.searchDropdown = $("wh-search-dropdown");
    els.searchWrap = els.searchInput ? els.searchInput.closest(".search-input-wrap") : null;
    els.reloadBtn = $("wh-reload-btn");
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
    els.modalDelete = $("wh-modal-delete");
    els.fieldSlot = $("wh-field-slot");
    els.fieldItemId = $("wh-field-item-id");
    els.fieldPrefixId = $("wh-field-prefix-id");
    els.fieldQuantity = $("wh-field-quantity");
    els.fieldValue = $("wh-field-value");
    els.fieldMinTier = $("wh-field-min-tier");
    els.deleteModal = $("wh-delete-modal");
    els.deleteAlert = $("wh-delete-alert");
    els.deleteSlot = $("wh-delete-slot");
    els.deleteConfirm = $("wh-delete-confirm");
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
    els.searchInput.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hideDropdown();
    });
    document.addEventListener("click", function (ev) {
      if (els.searchWrap && !els.searchWrap.contains(ev.target)) hideDropdown();
    });

    els.reloadBtn.addEventListener("click", function () {
      if (state.user && state.user.user_id) {
        loadWarehouse(state.user.user_id);
      }
    });

    els.modalForm.addEventListener("submit", saveModal);
    els.modalDelete.addEventListener("click", openDeleteModal);
    els.deleteConfirm.addEventListener("click", confirmDelete);

    document.querySelectorAll("[data-modal-close]").forEach(function (el) {
      el.addEventListener("click", function () {
        const targetId = el.getAttribute("data-modal-close");
        const target = document.getElementById(targetId);
        if (target) target.classList.add("hidden");
      });
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        document.querySelectorAll(".modal:not(.hidden)").forEach(function (m) {
          m.classList.add("hidden");
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async function () {
    bindElements();
    bindEvents();
    await Promise.all([loadDicts(), loadTiers()]);

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
