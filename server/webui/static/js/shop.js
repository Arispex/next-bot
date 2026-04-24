(function () {
  "use strict";

  const api = window.NextBotWebUIApi;
  if (!api) {
    console.error("NextBotWebUIApi 未加载");
    return;
  }

  const state = {
    shops: [],
    selectedShopId: null,
    selectedShopDetail: null,
    tiers: [],
    servers: [],
    editingShopId: null,
    editingItemId: null,
  };

  const els = {};

  function $(id) { return document.getElementById(id); }

  function clearChildren(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function showAlert(node, text, kind) {
    if (!node) return;
    node.textContent = text;
    node.style.display = "block";
    node.style.background = kind === "error" ? "#fee2e2" : "#dcfce7";
    node.style.color = kind === "error" ? "#991b1b" : "#166534";
    node.style.border = "1px solid " + (kind === "error" ? "#fecaca" : "#bbf7d0");
  }

  function hideAlert(node) {
    if (!node) return;
    node.style.display = "none";
    node.textContent = "";
  }

  async function callApi(url, opts = {}) {
    return api.apiRequest(url, opts);
  }

  async function loadMeta() {
    try {
      const tierRes = await callApi("/webui/api/shops/meta/tiers", { action: "加载进度选项" });
      state.tiers = api.unwrapData(tierRes) || [];
    } catch (err) { state.tiers = []; }
    try {
      const srvRes = await callApi("/webui/api/shops/meta/servers", { action: "加载服务器列表" });
      state.servers = api.unwrapData(srvRes) || [];
    } catch (err) { state.servers = []; }
  }

  async function loadShops() {
    try {
      const res = await callApi("/webui/api/shops", { action: "加载商店列表" });
      state.shops = api.unwrapData(res) || [];
      renderShopList();
      if (state.selectedShopId !== null) {
        const exists = state.shops.find((s) => s.id === state.selectedShopId);
        if (!exists) {
          state.selectedShopId = null;
          state.selectedShopDetail = null;
          renderShopDetail();
        } else {
          await loadShopDetail(state.selectedShopId);
        }
      }
    } catch (err) {
      showAlert(els.alert, err.message || "加载失败", "error");
    }
  }

  function renderShopList() {
    clearChildren(els.shopList);
    if (state.shops.length === 0) {
      els.shopListEmpty.style.display = "block";
      return;
    }
    els.shopListEmpty.style.display = "none";
    state.shops.forEach((shop) => {
      const card = document.createElement("div");
      card.style.padding = "10px 12px";
      card.style.border = "1px solid var(--color-border, #e2e8f0)";
      card.style.borderRadius = "8px";
      card.style.cursor = "pointer";
      card.style.display = "flex";
      card.style.justifyContent = "space-between";
      card.style.alignItems = "center";
      card.style.gap = "8px";
      if (shop.id === state.selectedShopId) {
        card.style.background = "rgba(59,130,246,0.08)";
        card.style.borderColor = "rgba(59,130,246,0.40)";
      }

      const left = document.createElement("div");
      left.style.flex = "1 1 auto";
      left.style.minWidth = "0";
      const title = document.createElement("div");
      title.style.fontWeight = "700";
      title.style.fontSize = "14px";
      title.style.overflow = "hidden";
      title.style.textOverflow = "ellipsis";
      title.style.whiteSpace = "nowrap";
      title.textContent = (shop.enabled ? "" : "[下架] ") + shop.name;
      const meta = document.createElement("div");
      meta.style.fontSize = "11px";
      meta.style.color = "var(--color-text-muted, #94a3b8)";
      meta.style.marginTop = "2px";
      meta.textContent = "ID " + shop.id + "  ·  " + (shop.item_count || 0) + " 件商品  ·  排序 " + shop.sort_order;
      left.appendChild(title);
      left.appendChild(meta);
      card.appendChild(left);

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn btn-ghost";
      editBtn.style.padding = "4px 10px";
      editBtn.style.fontSize = "12px";
      editBtn.textContent = "编辑";
      editBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openShopModal(shop);
      });
      card.appendChild(editBtn);

      card.addEventListener("click", () => {
        state.selectedShopId = shop.id;
        renderShopList();
        loadShopDetail(shop.id);
      });

      els.shopList.appendChild(card);
    });
  }

  async function loadShopDetail(shopId) {
    try {
      const res = await callApi("/webui/api/shops/" + shopId, { action: "加载商店详情" });
      state.selectedShopDetail = api.unwrapData(res);
      renderShopDetail();
    } catch (err) {
      showAlert(els.alert, err.message || "加载失败", "error");
    }
  }

  function renderShopDetail() {
    const detail = state.selectedShopDetail;
    if (!detail) {
      els.detailHeader.style.display = "none";
      els.itemList.style.display = "none";
      els.itemEmpty.style.display = "none";
      els.detailPlaceholder.style.display = "block";
      return;
    }
    els.detailPlaceholder.style.display = "none";
    els.detailHeader.style.display = "block";
    els.detailName.textContent = (detail.enabled ? "" : "[下架] ") + detail.name;
    els.detailMeta.textContent = "ID " + detail.id + "  ·  " + (detail.item_count || 0) + " 件商品  ·  排序 " + detail.sort_order;
    els.detailDesc.textContent = detail.description || "（暂无说明）";

    clearChildren(els.itemList);
    const items = Array.isArray(detail.items) ? detail.items : [];
    if (items.length === 0) {
      els.itemList.style.display = "none";
      els.itemEmpty.style.display = "block";
    } else {
      els.itemList.style.display = "flex";
      els.itemEmpty.style.display = "none";
      items.forEach((it) => els.itemList.appendChild(renderItemRow(it)));
    }
  }

  function renderItemRow(it) {
    const row = document.createElement("div");
    row.style.padding = "10px 12px";
    row.style.border = "1px solid var(--color-border, #e2e8f0)";
    row.style.borderRadius = "8px";
    row.style.display = "flex";
    row.style.alignItems = "center";
    row.style.gap = "12px";

    const left = document.createElement("div");
    left.style.flex = "1 1 auto";
    left.style.minWidth = "0";

    const head = document.createElement("div");
    head.style.display = "flex";
    head.style.alignItems = "center";
    head.style.gap = "8px";
    head.style.flexWrap = "wrap";

    const kind = document.createElement("span");
    kind.style.fontSize = "11px";
    kind.style.fontWeight = "700";
    kind.style.padding = "2px 8px";
    kind.style.borderRadius = "6px";
    if (it.kind === "item") {
      kind.style.background = "#dbeafe";
      kind.style.color = "#1e40af";
      kind.textContent = "物品";
    } else {
      kind.style.background = "#ede9fe";
      kind.style.color = "#6d28d9";
      kind.textContent = "指令";
    }
    head.appendChild(kind);

    const name = document.createElement("span");
    name.style.fontWeight = "700";
    name.style.fontSize = "14px";
    name.textContent = (it.enabled ? "" : "[下架] ") + (it.name || "未命名");
    head.appendChild(name);

    const price = document.createElement("span");
    price.style.fontSize = "12px";
    price.style.fontWeight = "700";
    price.style.color = "#b45309";
    price.textContent = "💰 " + it.price;
    head.appendChild(price);

    left.appendChild(head);

    if (it.description) {
      const desc = document.createElement("div");
      desc.style.fontSize = "12px";
      desc.style.color = "var(--color-text-muted, #64748b)";
      desc.style.marginTop = "4px";
      desc.textContent = it.description;
      left.appendChild(desc);
    }

    const meta = document.createElement("div");
    meta.style.fontSize = "11px";
    meta.style.color = "var(--color-text-muted, #94a3b8)";
    meta.style.marginTop = "4px";
    if (it.kind === "item") {
      const parts = [
        "item_id=" + it.item_id,
        "prefix=" + it.prefix_id,
        "数量=" + it.quantity,
        "进度=" + (it.min_tier_label || it.min_tier),
        "排序=" + it.sort_order,
      ];
      meta.textContent = parts.join("  ·  ");
    } else {
      const parts = [
        "目标=" + (it.target_server_label || "全部服务器"),
        "展示命令=" + (it.show_command ? "是" : "否"),
        "要求在线=" + (it.require_online ? "是" : "否"),
        "排序=" + it.sort_order,
      ];
      meta.textContent = parts.join("  ·  ");
      const cmd = document.createElement("div");
      cmd.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, monospace";
      cmd.style.fontSize = "11px";
      cmd.style.background = "#f8fafc";
      cmd.style.padding = "4px 8px";
      cmd.style.borderRadius = "4px";
      cmd.style.marginTop = "4px";
      cmd.style.wordBreak = "break-all";
      cmd.textContent = it.command_template || "";
      left.appendChild(meta);
      left.appendChild(cmd);
    }
    if (it.kind === "item") left.appendChild(meta);
    row.appendChild(left);

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-ghost";
    editBtn.style.padding = "6px 12px";
    editBtn.style.fontSize = "12px";
    editBtn.textContent = "编辑";
    editBtn.addEventListener("click", () => openItemModal(it));
    row.appendChild(editBtn);

    return row;
  }

  // ---------- Shop modal ----------

  function openShopModal(shop) {
    state.editingShopId = shop ? shop.id : null;
    hideAlert(els.shopModalAlert);
    els.shopModalTitle.textContent = shop ? "编辑商店" : "新建商店";
    els.shopFieldName.value = shop ? shop.name : "";
    els.shopFieldDescription.value = shop ? (shop.description || "") : "";
    els.shopFieldSortOrder.value = shop ? shop.sort_order : 0;
    els.shopFieldEnabled.checked = shop ? !!shop.enabled : true;
    els.shopModalDelete.style.display = shop ? "inline-block" : "none";
    els.shopModal.style.display = "flex";
  }

  function closeShopModal() {
    els.shopModal.style.display = "none";
    state.editingShopId = null;
  }

  async function submitShopModal(ev) {
    ev.preventDefault();
    hideAlert(els.shopModalAlert);
    const payload = {
      name: els.shopFieldName.value.trim(),
      description: els.shopFieldDescription.value.trim(),
      sort_order: Number(els.shopFieldSortOrder.value || 0),
      enabled: els.shopFieldEnabled.checked,
    };
    try {
      if (state.editingShopId === null) {
        await callApi("/webui/api/shops", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          action: "新建商店",
        });
      } else {
        await callApi("/webui/api/shops/" + state.editingShopId, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          action: "保存商店",
        });
      }
      closeShopModal();
      await loadShops();
    } catch (err) {
      showAlert(els.shopModalAlert, err.message || "保存失败", "error");
    }
  }

  async function deleteShop() {
    if (state.editingShopId === null) return;
    if (!window.confirm("确定要删除该商店吗？同时会删除该商店下所有商品。")) return;
    try {
      await callApi("/webui/api/shops/" + state.editingShopId, {
        method: "DELETE",
        action: "删除商店",
      });
      const wasSelected = state.selectedShopId === state.editingShopId;
      closeShopModal();
      if (wasSelected) {
        state.selectedShopId = null;
        state.selectedShopDetail = null;
      }
      await loadShops();
      renderShopDetail();
    } catch (err) {
      showAlert(els.shopModalAlert, err.message || "删除失败", "error");
    }
  }

  // ---------- Item modal ----------

  function fillTierOptions() {
    clearChildren(els.itemFieldMinTier);
    state.tiers.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.key;
      opt.textContent = t.label;
      els.itemFieldMinTier.appendChild(opt);
    });
  }

  function fillServerOptions() {
    clearChildren(els.itemFieldTargetServer);
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "全部服务器";
    els.itemFieldTargetServer.appendChild(all);
    state.servers.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = String(s.id);
      opt.textContent = s.id + ". " + s.name;
      els.itemFieldTargetServer.appendChild(opt);
    });
  }

  function applyKindVisibility() {
    const kind = els.itemFieldKind.value;
    if (kind === "item") {
      els.itemKindItemFields.style.display = "flex";
      els.itemKindCommandFields.style.display = "none";
    } else {
      els.itemKindItemFields.style.display = "none";
      els.itemKindCommandFields.style.display = "flex";
    }
  }

  function openItemModal(item) {
    if (state.selectedShopId === null) return;
    state.editingItemId = item ? item.id : null;
    hideAlert(els.itemModalAlert);
    els.itemModalTitle.textContent = item ? "编辑商品" : "新建商品";
    els.itemFieldName.value = item ? item.name : "";
    els.itemFieldDescription.value = item ? (item.description || "") : "";
    els.itemFieldKind.value = item ? item.kind : "item";
    els.itemFieldPrice.value = item ? item.price : 0;
    els.itemFieldSortOrder.value = item ? item.sort_order : 0;
    els.itemFieldEnabled.checked = item ? !!item.enabled : true;
    els.itemFieldItemId.value = item ? (item.item_id || 1) : 1;
    els.itemFieldPrefixId.value = item ? (item.prefix_id || 0) : 0;
    els.itemFieldQuantity.value = item ? (item.quantity || 1) : 1;
    els.itemFieldMinTier.value = item ? (item.min_tier || "none") : "none";
    els.itemFieldTargetServer.value = (item && item.target_server_id !== null && item.target_server_id !== undefined)
      ? String(item.target_server_id) : "";
    els.itemFieldCommandTemplate.value = item ? (item.command_template || "") : "";
    els.itemFieldShowCommand.checked = item ? !!item.show_command : false;
    els.itemFieldRequireOnline.checked = item ? !!item.require_online : false;
    els.itemModalDelete.style.display = item ? "inline-block" : "none";
    applyKindVisibility();
    els.itemModal.style.display = "flex";
  }

  function closeItemModal() {
    els.itemModal.style.display = "none";
    state.editingItemId = null;
  }

  async function submitItemModal(ev) {
    ev.preventDefault();
    hideAlert(els.itemModalAlert);
    if (state.selectedShopId === null) return;
    const kind = els.itemFieldKind.value;
    const payload = {
      name: els.itemFieldName.value.trim(),
      description: els.itemFieldDescription.value.trim(),
      kind: kind,
      price: Number(els.itemFieldPrice.value || 0),
      sort_order: Number(els.itemFieldSortOrder.value || 0),
      enabled: els.itemFieldEnabled.checked,
    };
    if (kind === "item") {
      payload.item_id = Number(els.itemFieldItemId.value || 0);
      payload.prefix_id = Number(els.itemFieldPrefixId.value || 0);
      payload.quantity = Number(els.itemFieldQuantity.value || 1);
      payload.min_tier = els.itemFieldMinTier.value || "none";
    } else {
      const raw = els.itemFieldTargetServer.value;
      payload.target_server_id = raw ? Number(raw) : null;
      payload.command_template = els.itemFieldCommandTemplate.value;
      payload.show_command = els.itemFieldShowCommand.checked;
      payload.require_online = els.itemFieldRequireOnline.checked;
    }
    try {
      if (state.editingItemId === null) {
        await callApi("/webui/api/shops/" + state.selectedShopId + "/items", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          action: "新建商品",
        });
      } else {
        await callApi(
          "/webui/api/shops/" + state.selectedShopId + "/items/" + state.editingItemId,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            action: "保存商品",
          },
        );
      }
      closeItemModal();
      await loadShopDetail(state.selectedShopId);
      await loadShops();
    } catch (err) {
      showAlert(els.itemModalAlert, err.message || "保存失败", "error");
    }
  }

  async function deleteItem() {
    if (state.selectedShopId === null || state.editingItemId === null) return;
    if (!window.confirm("确定要删除该商品吗？")) return;
    try {
      await callApi(
        "/webui/api/shops/" + state.selectedShopId + "/items/" + state.editingItemId,
        { method: "DELETE", action: "删除商品" },
      );
      closeItemModal();
      await loadShopDetail(state.selectedShopId);
      await loadShops();
    } catch (err) {
      showAlert(els.itemModalAlert, err.message || "删除失败", "error");
    }
  }

  function bindEls() {
    els.alert = $("shop-alert");
    els.shopList = $("shop-list");
    els.shopListEmpty = $("shop-list-empty");
    els.shopCreateBtn = $("shop-create-btn");
    els.detailHeader = $("shop-detail-header");
    els.detailName = $("shop-detail-name");
    els.detailMeta = $("shop-detail-meta");
    els.detailDesc = $("shop-detail-desc");
    els.detailPlaceholder = $("shop-detail-placeholder");
    els.itemCreateBtn = $("shop-item-create-btn");
    els.itemList = $("shop-item-list");
    els.itemEmpty = $("shop-item-empty");

    els.shopModal = $("shop-modal");
    els.shopModalTitle = $("shop-modal-title");
    els.shopModalAlert = $("shop-modal-alert");
    els.shopModalForm = $("shop-modal-form");
    els.shopModalClose = $("shop-modal-close");
    els.shopModalCancel = $("shop-modal-cancel");
    els.shopModalSave = $("shop-modal-save");
    els.shopModalDelete = $("shop-modal-delete");
    els.shopFieldName = $("shop-field-name");
    els.shopFieldDescription = $("shop-field-description");
    els.shopFieldSortOrder = $("shop-field-sort-order");
    els.shopFieldEnabled = $("shop-field-enabled");

    els.itemModal = $("item-modal");
    els.itemModalTitle = $("item-modal-title");
    els.itemModalAlert = $("item-modal-alert");
    els.itemModalForm = $("item-modal-form");
    els.itemModalClose = $("item-modal-close");
    els.itemModalCancel = $("item-modal-cancel");
    els.itemModalSave = $("item-modal-save");
    els.itemModalDelete = $("item-modal-delete");
    els.itemFieldName = $("item-field-name");
    els.itemFieldDescription = $("item-field-description");
    els.itemFieldKind = $("item-field-kind");
    els.itemFieldPrice = $("item-field-price");
    els.itemFieldSortOrder = $("item-field-sort-order");
    els.itemFieldEnabled = $("item-field-enabled");
    els.itemKindItemFields = $("item-kind-item-fields");
    els.itemKindCommandFields = $("item-kind-command-fields");
    els.itemFieldItemId = $("item-field-item-id");
    els.itemFieldPrefixId = $("item-field-prefix-id");
    els.itemFieldQuantity = $("item-field-quantity");
    els.itemFieldMinTier = $("item-field-min-tier");
    els.itemFieldTargetServer = $("item-field-target-server");
    els.itemFieldCommandTemplate = $("item-field-command-template");
    els.itemFieldShowCommand = $("item-field-show-command");
    els.itemFieldRequireOnline = $("item-field-require-online");
  }

  function bindEvents() {
    els.shopCreateBtn.addEventListener("click", () => openShopModal(null));
    els.shopModalClose.addEventListener("click", closeShopModal);
    els.shopModalCancel.addEventListener("click", closeShopModal);
    els.shopModalForm.addEventListener("submit", submitShopModal);
    els.shopModalDelete.addEventListener("click", deleteShop);
    els.shopModal.addEventListener("click", (e) => {
      if (e.target === els.shopModal) closeShopModal();
    });

    els.itemCreateBtn.addEventListener("click", () => openItemModal(null));
    els.itemModalClose.addEventListener("click", closeItemModal);
    els.itemModalCancel.addEventListener("click", closeItemModal);
    els.itemModalForm.addEventListener("submit", submitItemModal);
    els.itemModalDelete.addEventListener("click", deleteItem);
    els.itemFieldKind.addEventListener("change", applyKindVisibility);
    els.itemModal.addEventListener("click", (e) => {
      if (e.target === els.itemModal) closeItemModal();
    });
  }

  async function init() {
    bindEls();
    bindEvents();
    await loadMeta();
    fillTierOptions();
    fillServerOptions();
    await loadShops();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
