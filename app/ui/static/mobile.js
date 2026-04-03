async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderList(container, items, renderItem, emptyText) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    container.innerHTML = `<div class="list-item empty-state">${emptyText}</div>`;
    return;
  }
  items.forEach((item) => {
    const wrapper = document.createElement("article");
    wrapper.className = "list-item";
    wrapper.innerHTML = renderItem(item);
    container.appendChild(wrapper);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadFeed() {
  const feed = await fetchJson("/api/v1/mobile/feed");
  document.getElementById("generatedAt").textContent = `更新于 ${feed.generated_at}`;

  const latestReport = document.getElementById("latestReport");
  if (feed.latest_report) {
    latestReport.classList.remove("empty-state");
    latestReport.textContent = feed.latest_report.summary_markdown;
  } else {
    latestReport.classList.add("empty-state");
    latestReport.textContent = "还没有可显示的摘要。";
  }

  renderList(
    document.getElementById("alertsList"),
    feed.recent_alerts,
    (item) => `
      <div class="item-meta">${item.sent_at}</div>
      <div class="alert-item">${escapeHtml(item.payload)}</div>
    `,
    "暂无高优先级告警",
  );

  const todos = document.getElementById("todosList");
  todos.innerHTML = "";
  if (feed.today_todos.length === 0) {
    todos.innerHTML = `<li class="empty-state">暂无待办</li>`;
  } else {
    feed.today_todos.forEach((todo) => {
      const item = document.createElement("li");
      item.textContent = todo;
      todos.appendChild(item);
    });
  }

  renderList(
    document.getElementById("devicesList"),
    feed.devices,
    (item) => `
      <div><strong>${escapeHtml(item.device_name)}</strong> <span class="${item.status === "online" ? "device-online" : "device-offline"}">${item.status}</span></div>
      <div class="item-meta">${escapeHtml(item.platform)} · ${escapeHtml(item.app_version || "unknown")}</div>
      <div class="item-meta">last seen: ${escapeHtml(item.last_seen_at || "-")}</div>
    `,
    "暂无设备数据",
  );

  renderList(
    document.getElementById("groupsList"),
    feed.group_overview,
    (item) => `
      <div><strong>${escapeHtml(item.group_name)}</strong></div>
      <div>${escapeHtml(item.brief)}</div>
      <div class="item-meta">noise: ${escapeHtml(item.noise_level)}</div>
    `,
    "暂无群动态",
  );
}

async function searchMessages(query) {
  const container = document.getElementById("searchResults");
  if (!query.trim()) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = `<div class="list-item empty-state">搜索中...</div>`;
  const results = await fetchJson(`/api/v1/mobile/search?q=${encodeURIComponent(query.trim())}`);
  renderList(
    container,
    results,
    (item) => `
      <div><strong>${escapeHtml(item.message.group_name)}</strong> · ${escapeHtml(item.message.sender_name)}</div>
      <div>${escapeHtml(item.message.content)}</div>
      <div class="item-meta">${escapeHtml(item.message.timestamp)} · ${escapeHtml(item.analysis.priority)} / ${escapeHtml(item.analysis.category)}</div>
    `,
    "没有找到匹配消息",
  );
}

document.getElementById("refreshButton").addEventListener("click", () => {
  loadFeed().catch((error) => {
    console.error(error);
  });
});

document.getElementById("searchForm").addEventListener("submit", (event) => {
  event.preventDefault();
  searchMessages(document.getElementById("searchInput").value).catch((error) => {
    console.error(error);
  });
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/mobile/sw.js").catch((error) => {
    console.error("service worker registration failed", error);
  });
}

loadFeed().catch((error) => {
  console.error(error);
  document.getElementById("latestReport").textContent = `加载失败：${error.message}`;
});
