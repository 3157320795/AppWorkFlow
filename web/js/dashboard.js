/**
 * 工作流可视化：消费 /stream_run SSE（debug 模式）并展示节点耗时与输出。
 * 优化版本：适配新的交互式工作流事件格式
 */

const NODE_LABELS = {
  function_design: "功能设计",
  scheme_confirm: "方案确认（交互）",
  project_create: "项目创建 (Stitch MCP)",
  generate_screens_html: "生成 Screens / HTML",
  recover_stitch_assets: "恢复 Stitch 资源",
  file_download: "文件下载",
  git_branch_switch: "Git 分支切换",
  uniapp_page_generate: "UniApp 页面生成",
  result_format: "结果整理",
};

const NODE_ORDER = Object.keys(NODE_LABELS);

const state = {
  runId: null,
  aborted: false,
  controller: null,
  nodes: Object.fromEntries(
    NODE_ORDER.map((id) => [
      id,
      { id, status: "pending", startMs: null, endMs: null, durationMs: null, output: null, input: null },
    ])
  ),
  // 新增：恢复进度状态
  recoveryProgress: {
    active: false,
    phase: "", // "waiting" | "polling" | "success" | "failed"
    checkCount: 0,
    totalChecks: 10, // 5分钟/30秒 = 10次
    remainingSeconds: 0,
    totalWaitSeconds: 300, // 总等待时间（用于计算waiting阶段进度）
    message: "",
  },
  // 新增：运行日志
  logs: [],
};

const el = (id) => document.getElementById(id);

const VIEW = {
  GRAPH: "graph",
  TIMELINE: "timeline",
  LOGS: "logs",
};

let activeView = VIEW.GRAPH;
let selectedNode = null;

function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(0);
  return `${mins}分${secs}秒`;
}

function formatSeconds(s) {
  if (s < 60) return `${s}秒`;
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return secs > 0 ? `${mins}分${secs}秒` : `${mins}分钟`;
}

function nodeIcon(id) {
  const icons = {
    function_design: "FD",
    scheme_confirm: "SC",
    project_create: "PC",
    generate_screens_html: "GH",
    recover_stitch_assets: "RC",
    file_download: "DL",
    git_branch_switch: "GIT",
    uniapp_page_generate: "UA",
    result_format: "OK",
  };
  return icons[id] || id.slice(0, 2).toUpperCase();
}

function nodeStatusClass(status) {
  const map = {
    pending: "pending",
    running: "running",
    done: "done",
    error: "error",
    warning: "warning",
  };
  return map[status] || "pending";
}

function nodeStatusText(status) {
  const map = {
    pending: "待执行",
    running: "运行中",
    done: "完成",
    error: "异常",
    warning: "警告",
  };
  return map[status] || "待执行";
}

// ==================== Timeline 视图 ====================

function renderTimeline() {
  const root = el("timeline");
  if (!root) return;
  root.innerHTML = "";

  for (const id of NODE_ORDER) {
    const n = state.nodes[id];
    const card = document.createElement("div");
    card.className = `node-card ${nodeStatusClass(n.status)}`;
    card.dataset.node = id;

    const title = document.createElement("div");
    title.className = "node-title";
    title.textContent = NODE_LABELS[id] || id;

    const badge = document.createElement("span");
    badge.className = `badge ${n.status === "running" ? "run" : ""} ${n.durationMs ? "time" : ""}`;
    badge.textContent = n.status === "running" ? "运行中" : n.durationMs ? formatDuration(n.durationMs) : nodeStatusText(n.status);

    const sub = document.createElement("div");
    sub.className = "node-sub";
    sub.textContent = id;

    // 新增：进度条（用于恢复节点）
    if (id === "recover_stitch_assets" && state.recoveryProgress.active) {
      const progress = document.createElement("div");
      progress.className = "node-progress";
      const progressBar = document.createElement("div");
      progressBar.className = "node-progress-bar";
      const pct = Math.min(100, (state.recoveryProgress.checkCount / state.recoveryProgress.totalChecks) * 100);
      progressBar.style.width = `${pct}%`;
      progress.appendChild(progressBar);
      card.appendChild(progress);
    }

    card.appendChild(title);
    card.appendChild(badge);
    card.appendChild(sub);
    card.addEventListener("click", () => selectNode(id));
    root.appendChild(card);
  }
}

// ==================== Graph 视图 ====================

function createWfNode(id) {
  const n = state.nodes[id];
  const card = document.createElement("div");
  card.className = `wf-node ${nodeStatusClass(n.status)}`;
  card.dataset.node = id;

  const icon = document.createElement("div");
  icon.className = "wf-icon";
  icon.textContent = nodeIcon(id);

  const mid = document.createElement("div");
  const title = document.createElement("div");
  title.className = "wf-title";
  title.textContent = NODE_LABELS[id] || id;
  const sub = document.createElement("div");
  sub.className = "wf-sub";
  sub.textContent = id;
  mid.appendChild(title);
  mid.appendChild(sub);

  const badges = document.createElement("div");
  badges.className = "wf-badges";
  const pill = document.createElement("span");
  pill.className = `wf-pill ${n.status === "running" ? "run" : ""} ${n.durationMs ? "time" : ""}`;
  pill.textContent = n.status === "running" ? "运行中" : n.durationMs ? formatDuration(n.durationMs) : nodeStatusText(n.status);
  badges.appendChild(pill);

  // 新增：恢复节点进度条
  if (id === "recover_stitch_assets" && state.recoveryProgress.active) {
    const progressWrap = document.createElement("div");
    progressWrap.className = "wf-progress-wrap";
    const progressBar = document.createElement("div");
    progressBar.className = "wf-progress-bar";
    const pct = Math.min(100, (state.recoveryProgress.checkCount / state.recoveryProgress.totalChecks) * 100);
    progressBar.style.width = `${pct}%`;
    progressWrap.appendChild(progressBar);
    badges.appendChild(progressWrap);
  }

  card.appendChild(icon);
  card.appendChild(mid);
  card.appendChild(badges);
  card.addEventListener("click", () => selectNode(id));
  return card;
}

function createGhostNode(text) {
  const d = document.createElement("div");
  d.className = "wf-ghost";
  d.textContent = text;
  return d;
}

function createDiamond(text) {
  const d = document.createElement("div");
  d.className = "wf-diamond";
  const inner = document.createElement("span");
  inner.className = "wf-diamond-inner";
  inner.textContent = text;
  d.appendChild(inner);
  return d;
}

function createEdge() {
  const e = document.createElement("div");
  e.className = "wf-edge";
  return e;
}

function renderGraph() {
  const root = el("graphCanvas");
  if (!root) return;
  root.innerHTML = "";

  const wf = document.createElement("div");
  wf.className = "wf";

  // 开始
  wf.appendChild(createGhostNode("开始"));
  wf.appendChild(createEdge());

  // 主干节点
  const mainNodes = ["function_design", "scheme_confirm", "project_create", "generate_screens_html"];
  for (const id of mainNodes) {
    wf.appendChild(createWfNode(id));
    wf.appendChild(createEdge());
  }

  // 条件分支：是否需要恢复
  const recoveryNode = state.nodes["recover_stitch_assets"];
  const needRecovery = recoveryNode && (recoveryNode.status === "running" || recoveryNode.status === "done" || recoveryNode.status === "error");

  if (needRecovery) {
    // 显示恢复分支
    wf.appendChild(createDiamond("需要恢复资源？"));
    wf.appendChild(createEdge());

    const b = document.createElement("div");
    b.className = "wf-branch";

    // 左：直接下载（成功路径）
    const left = document.createElement("div");
    left.className = "wf-branch-col";
    const leftLabel = document.createElement("div");
    leftLabel.className = "wf-branch-label";
    leftLabel.textContent = "生成成功 → 下载";
    left.appendChild(leftLabel);
    left.appendChild(createWfNode("file_download"));

    // 右：恢复资源
    const right = document.createElement("div");
    right.className = "wf-branch-col";
    const rightLabel = document.createElement("div");
    rightLabel.className = "wf-branch-label";
    rightLabel.textContent = "需要恢复 → 轮询获取";
    right.appendChild(rightLabel);
    right.appendChild(createWfNode("recover_stitch_assets"));

    b.appendChild(left);
    b.appendChild(right);
    wf.appendChild(b);
    wf.appendChild(createEdge());
  }

  // 收敛：Git 分支切换
  wf.appendChild(createWfNode("git_branch_switch"));
  wf.appendChild(createEdge());

  // UniApp 页面生成
  wf.appendChild(createWfNode("uniapp_page_generate"));
  wf.appendChild(createEdge());

  // 结束
  wf.appendChild(createGhostNode("完成"));

  root.appendChild(wf);

  // 同步选中态
  if (selectedNode) {
    root.querySelectorAll(".wf-node").forEach((c) => {
      c.classList.toggle("selected", c.dataset.node === selectedNode);
    });
  }
}

// ==================== Logs 视图 ====================

function renderLogs() {
  const root = el("logs");
  if (!root) return;
  root.innerHTML = "";

  state.logs.forEach((log, index) => {
    const entry = document.createElement("div");
    entry.className = `log-entry log-${log.level}`;

    const time = document.createElement("span");
    time.className = "log-time";
    time.textContent = new Date(log.timestamp).toLocaleTimeString();

    const level = document.createElement("span");
    level.className = `log-level log-level-${log.level}`;
    level.textContent = log.level.toUpperCase();

    const message = document.createElement("span");
    message.className = "log-message";
    message.textContent = log.message;

    entry.appendChild(time);
    entry.appendChild(level);
    entry.appendChild(message);
    root.appendChild(entry);
  });

  // 自动滚动到底部
  root.scrollTop = root.scrollHeight;
}

function addLog(level, message, data = null) {
  const log = {
    timestamp: Date.now(),
    level,
    message: data ? `${message} ${JSON.stringify(data).slice(0, 200)}` : message,
    data,
  };
  state.logs.push(log);
  // 限制日志数量
  if (state.logs.length > 500) {
    state.logs = state.logs.slice(-500);
  }
  if (activeView === VIEW.LOGS) {
    renderLogs();
  }
}

// 更新当前节点状态显示
function updateCurrentNodeStatus(status) {
  const currentNodeRow = el("currentNodeRow");
  const currentNode = el("currentNode");

  if (currentNodeRow && currentNode) {
    currentNodeRow.style.display = "flex";
    currentNode.textContent = status;
    currentNode.className = "node-status running";

    // 5秒后移除 running 样式
    setTimeout(() => {
      currentNode.className = "node-status";
    }, 5000);
  }

  // 同时更新顶部状态栏
  const statusEl = el("workflowStatus");
  if (statusEl) {
    statusEl.textContent = status;
    statusEl.className = "status-item running";
  }
}

// ==================== 节点选择与详情 ====================

function selectNode(id) {
  selectedNode = id;

  // 高亮时间线中的节点
  document.querySelectorAll(".node-card").forEach((c) => {
    c.classList.toggle("selected", c.dataset.node === id);
  });

  // 更新详情面板
  const n = state.nodes[id];
  el("detailNode").textContent = `${NODE_LABELS[id] || id} (${id})`;

  // 构建详情内容
  let detailHtml = "";

  if (n.status !== "pending") {
    detailHtml += `<div class="detail-section">
      <div class="detail-label">状态</div>
      <div class="detail-value status-${n.status}">${nodeStatusText(n.status)}</div>
    </div>`;
  }

  if (n.durationMs) {
    detailHtml += `<div class="detail-section">
      <div class="detail-label">耗时</div>
      <div class="detail-value">${formatDuration(n.durationMs)}</div>
    </div>`;
  }

  if (n.input) {
    detailHtml += `<div class="detail-section">
      <div class="detail-label">输入</div>
      <pre class="detail-json">${JSON.stringify(n.input, null, 2)}</pre>
    </div>`;
  }

  if (n.output) {
    detailHtml += `<div class="detail-section">
      <div class="detail-label">输出</div>
      <pre class="detail-json">${JSON.stringify(n.output, null, 2)}</pre>
    </div>`;
  }

  // 恢复进度（如果是恢复节点）
  if (id === "recover_stitch_assets" && state.recoveryProgress.active) {
    detailHtml += `<div class="detail-section">
      <div class="detail-label">恢复进度</div>
      <div class="recovery-status">
        <div class="recovery-phase">${state.recoveryProgress.message}</div>
        <div class="recovery-progress-bar">
          <div class="recovery-progress-fill" style="width: ${(state.recoveryProgress.checkCount / state.recoveryProgress.totalChecks) * 100}%"></div>
        </div>
        <div class="recovery-stats">
          第 ${state.recoveryProgress.checkCount}/${state.recoveryProgress.totalChecks} 次检查
          ${state.recoveryProgress.remainingSeconds > 0 ? `· 剩余 ${formatSeconds(state.recoveryProgress.remainingSeconds)}` : ""}
        </div>
      </div>
    </div>`;
  }

  el("detailJson").innerHTML = detailHtml || "暂无数据";

  // 图预览同步高亮
  document.querySelectorAll(".wf-node").forEach((c) => {
    c.classList.toggle("selected", c.dataset.node === id);
  });
}

// ==================== 交互处理 ====================

function setInteractionHint(text) {
  const hint = el("interactionHint");
  if (hint) hint.textContent = text || "";
}

function hideInteraction() {
  const box = el("interactionBox");
  if (box) box.hidden = true;

  // 隐藏自动恢复面板
  const autoBox = el("autoRecoverBox");
  if (autoBox) autoBox.hidden = true;

  // 恢复方案确认相关元素
  const head = box?.querySelector(".interaction-head");
  if (head) head.hidden = false;
  const modifyBox = box?.querySelector(".modify-box");
  if (modifyBox) modifyBox.hidden = false;

  const list = el("schemeList");
  if (list) list.innerHTML = "";
  const ta = el("modifyText");
  if (ta) ta.value = "";
  setInteractionHint("");

  // 重置自动恢复进度
  state.recoveryProgress.active = false;
  state.recoveryProgress.checkCount = 0;
}

async function fetchPendingSchemes() {
  if (!state.runId) return null;
  try {
    const res = await fetch(`/interaction/schemes/${encodeURIComponent(state.runId)}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    addLog("error", "获取方案列表失败", e.message);
    return null;
  }
}

async function submitConfirm(index) {
  console.log(`[DEBUG] submitConfirm 被调用, index=${index}, runId=${state.runId}`);
  if (!state.runId) {
    setInteractionHint("错误：未找到 run_id，请重新启动工作流");
    console.error("[DEBUG] submitConfirm: state.runId 为空");
    return;
  }
  setInteractionHint("正在提交确认...");
  try {
    const payload = { run_id: state.runId, scheme_index: index };
    console.log(`[DEBUG] 发送确认请求:`, payload);
    const res = await fetch("/interaction/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log(`[DEBUG] 收到响应: status=${res.status}`);
    if (!res.ok) {
      const text = await res.text();
      setInteractionHint(`提交失败：HTTP ${res.status} - ${text}`);
      addLog("error", "提交方案确认失败", `HTTP ${res.status}: ${text}`);
      return;
    }
    const result = await res.json();
    setInteractionHint("已提交确认，工作流将继续运行。");
    addLog("info", `已确认方案 #${index + 1}`, result);
    console.log(`[DEBUG] 确认成功:`, result);
  } catch (e) {
    setInteractionHint(`提交失败：${e.message}`);
    addLog("error", "提交方案确认失败", e.message);
    console.error(`[DEBUG] 确认异常:`, e);
  }
}

async function submitProjectId(pid) {
  console.log(`[DEBUG] submitProjectId 被调用, runId=${state.runId}`);
  if (!state.runId) {
    setInteractionHint("错误：未找到 run_id");
    return;
  }
  const p = (pid || "").trim();
  if (!p) {
    setInteractionHint("请填写 project_id。");
    return;
  }
  setInteractionHint("正在提交 project_id...");
  try {
    const payload = { run_id: state.runId, project_id: p };
    console.log(`[DEBUG] 发送 project_id:`, payload);
    const res = await fetch("/interaction/project_id", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log(`[DEBUG] 收到响应: status=${res.status}`);
    if (!res.ok) {
      const errorText = await res.text();
      setInteractionHint(`提交失败：HTTP ${res.status} - ${errorText}`);
      addLog("error", "提交 project_id 失败", `HTTP ${res.status}: ${errorText}`);
      return;
    }
    const result = await res.json();
    setInteractionHint("已提交 project_id，正在尝试恢复资源...");
    addLog("info", "已提交 project_id", p.slice(0, 20));
    console.log(`[DEBUG] project_id 提交成功:`, result);
  } catch (e) {
    setInteractionHint(`提交失败：${e.message}`);
    addLog("error", "提交 project_id 失败", e.message);
    console.error(`[DEBUG] project_id 提交异常:`, e);
  }
}

async function submitModify(text) {
  console.log(`[DEBUG] submitModify 被调用, runId=${state.runId}`);
  if (!state.runId) {
    setInteractionHint("错误：未找到 run_id");
    return;
  }
  const t = (text || "").trim();
  if (!t) {
    setInteractionHint("请先填写修改要求。");
    return;
  }
  setInteractionHint("正在提交修改...");
  try {
    const payload = { run_id: state.runId, modification_request: t };
    console.log(`[DEBUG] 发送修改请求:`, payload);
    const res = await fetch("/interaction/modify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log(`[DEBUG] 收到响应: status=${res.status}`);
    if (!res.ok) {
      const errorText = await res.text();
      setInteractionHint(`提交失败：HTTP ${res.status} - ${errorText}`);
      addLog("error", "提交修改失败", `HTTP ${res.status}: ${errorText}`);
      return;
    }
    const result = await res.json();
    setInteractionHint("已提交修改，工作流将继续运行。");
    addLog("info", "已提交修改要求", t.slice(0, 50));
    console.log(`[DEBUG] 修改提交成功:`, result);
  } catch (e) {
    setInteractionHint(`提交失败：${e.message}`);
    addLog("error", "提交修改失败", e.message);
    console.error(`[DEBUG] 修改提交异常:`, e);
  }
}

// 直接显示方案列表（从 SSE 事件数据）
function showSchemesDirectly(schemes) {
  const box = el("interactionBox");
  const list = el("schemeList");
  const autoBox = el("autoRecoverBox");

  if (!box || !list) return;

  // 隐藏自动恢复面板，显示方案列表
  box.hidden = false;
  if (autoBox) autoBox.hidden = true;
  list.innerHTML = "";

  // 显示方案确认相关元素
  const head = box.querySelector(".interaction-head");
  if (head) head.hidden = false;

  // 显示修改要求区域
  const modifyBox = el("modifyText")?.closest(".modify-box");
  if (modifyBox) {
    modifyBox.hidden = false;
  } else {
    const modifyLabel = box.querySelector(".modify-label");
    const modifyText = el("modifyText");
    const modifyActions = box.querySelector(".modify-actions");
    if (modifyLabel) modifyLabel.style.display = "";
    if (modifyText) modifyText.style.display = "";
    if (modifyActions) modifyActions.style.display = "";
  }

  // 显示方案列表
  schemes.forEach((s, idx) => {
    const card = document.createElement("div");
    card.className = "scheme-card";

    const h3 = document.createElement("h3");
    h3.textContent = `方案 ${idx + 1}：${s.scheme_name || s.name || "未命名"}`;

    const desc = document.createElement("p");
    desc.className = "scheme-desc";
    desc.textContent = s.description || s.desc || "";

    // 页面列表
    const pages = document.createElement("div");
    pages.className = "scheme-pages";
    const pageList = s.pages || s.page_list || [];
    if (pageList.length > 0) {
      pageList.forEach((p) => {
        const pageTag = document.createElement("span");
        pageTag.className = "page-tag";
        pageTag.textContent = p.page_name || p.name || "页面";
        pages.appendChild(pageTag);
      });
    }

    const actions = document.createElement("div");
    actions.className = "scheme-actions";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "primary";
    btn.textContent = "选择此方案";

    // 调试日志 + 事件绑定
    console.log(`[DEBUG] 绑定方案按钮 #${idx}, runId=${state.runId}`);
    btn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      console.log(`[DEBUG] 点击方案按钮 #${idx}, runId=${state.runId}`);
      submitConfirm(idx);
      return false;
    };

    actions.appendChild(btn);
    card.appendChild(h3);
    card.appendChild(desc);
    if (pageList.length > 0) card.appendChild(pages);
    card.appendChild(actions);
    list.appendChild(card);
  });

  // 绑定修改提交按钮 - 每次都重新绑定以确保有效
  const submitBtn = el("btnSubmitModify");
  const modifyText = el("modifyText");
  if (submitBtn) {
    submitBtn.onclick = (e) => {
      e.preventDefault();
      const text = modifyText ? modifyText.value : "";
      console.log(`[DEBUG] 点击提交修改按钮, text=${text.slice(0, 50)}`);
      submitModify(text);
      return false;
    };
    console.log(`[DEBUG] 已绑定修改提交按钮`);
  }

  setInteractionHint("请选择方案，或填写修改要求并提交。");
  addLog("info", `显示 ${schemes.length} 个待确认方案`);
}

// 显示自动恢复状态（全自动模式，无需用户输入）
function showAutoRecoverStatus() {
  const box = el("interactionBox");
  const autoBox = el("autoRecoverBox");
  const list = el("schemeList");
  const modifyBox = el("modifyText")?.closest(".modify-box");
  const hint = el("interactionHint");

  if (!box || !autoBox) return;

  // 显示交互区域和自动恢复面板
  box.hidden = false;
  autoBox.hidden = false;

  // 清空方案列表
  if (list) list.innerHTML = "";

  // 隐藏方案确认相关元素
  const head = box.querySelector(".interaction-head");
  if (head) head.hidden = true;

  // 隐藏修改要求区域
  if (modifyBox) {
    modifyBox.hidden = true;
  } else {
    // 备选：直接隐藏各个元素
    const modifyLabel = box.querySelector(".modify-label");
    const modifyText = el("modifyText");
    const modifyActions = box.querySelector(".modify-actions");
    if (modifyLabel) modifyLabel.style.display = "none";
    if (modifyText) modifyText.style.display = "none";
    if (modifyActions) modifyActions.style.display = "none";
  }

  // 隐藏提示文字
  if (hint) hint.hidden = true;

  setInteractionHint("系统自动恢复 Stitch 资源中，无需操作...");
  addLog("info", "显示自动恢复状态面板");
}

// 更新自动恢复进度
function updateAutoRecoverProgress(phase, stats, logs) {
  const phaseEl = el("recoverPhase");
  const statsEl = el("recoverStats");
  const logsEl = el("recoverLogs");
  const progressBar = el("recoverProgressBar");

  if (phaseEl) phaseEl.textContent = phase || "处理中...";
  if (statsEl) statsEl.textContent = stats || "";

  // 更新进度条
  if (progressBar && state.recoveryProgress.active) {
    const pct = Math.min(100, (state.recoveryProgress.checkCount / state.recoveryProgress.totalChecks) * 100);
    progressBar.style.width = `${pct}%`;
  }

  // 添加日志
  if (logsEl && logs) {
    const logEntry = document.createElement("div");
    logEntry.className = "recover-log-entry";
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${logs}`;
    logsEl.appendChild(logEntry);
    logsEl.scrollTop = logsEl.scrollHeight;
  }
}

// 隐藏自动恢复面板
function hideAutoRecoverBox() {
  const autoBox = el("autoRecoverBox");
  const box = el("interactionBox");
  const hint = el("interactionHint");

  if (autoBox) autoBox.hidden = true;

  // 恢复显示方案确认相关元素
  if (box) {
    const head = box.querySelector(".interaction-head");
    if (head) head.hidden = false;

    // 恢复修改要求区域
    const modifyBox = el("modifyText")?.closest(".modify-box");
    if (modifyBox) {
      modifyBox.hidden = false;
    } else {
      // 备选：直接显示各个元素
      const modifyLabel = box.querySelector(".modify-label");
      const modifyText = el("modifyText");
      const modifyActions = box.querySelector(".modify-actions");
      if (modifyLabel) modifyLabel.style.display = "";
      if (modifyText) modifyText.style.display = "";
      if (modifyActions) modifyActions.style.display = "";
    }
  }

  // 恢复提示文字
  if (hint) hint.hidden = false;
}

async function showInteractionIfAvailable() {
  const data = await fetchPendingSchemes();
  if (!data || data.status !== "pending" || !Array.isArray(data.schemes) || data.schemes.length === 0) {
    hideInteraction();
    return;
  }

  // 使用通用显示函数
  showSchemesDirectly(data.schemes);
}

// ==================== SSE 事件处理 ====================

function applyEvent(ev) {
  // 适配新的 event_type 格式
  const eventType = ev.event_type || ev.type;
  const timestamp = ev.timestamp || Date.now();

  addLog("debug", `收到事件: ${eventType}`, ev);

  switch (eventType) {
    case "workflow_start":
      addLog("info", "工作流开始", { product: ev.product_name, group: ev.product_group });
      break;

    case "workflow_end":
      addLog("info", "工作流完成", { total_time: ev.total_time_seconds, pages: ev.generated_pages });
      el("totalMs").textContent = formatDuration((ev.total_time_seconds || 0) * 1000);
      state.recoveryProgress.active = false;

      // 更新状态栏为完成
      const statusEl = el("workflowStatus");
      if (statusEl) {
        statusEl.textContent = "✅ 已完成";
        statusEl.className = "status-item success";
      }

      // 隐藏当前节点状态
      const currentNodeRow = el("currentNodeRow");
      if (currentNodeRow) currentNodeRow.style.display = "none";

      renderTimeline();
      renderGraph();
      break;

    case "node_start":
      // 支持 node 或 node_name 字段
      const nodeId = ev.node || ev.node_name;
      if (nodeId && state.nodes[nodeId]) {
        state.nodes[nodeId].status = "running";
        state.nodes[nodeId].startMs = timestamp;
        state.nodes[nodeId].input = ev;
      }
      addLog("info", `节点开始: ${NODE_LABELS[nodeId] || nodeId}`, ev.message);
      renderTimeline();
      renderGraph();

      // 特殊节点处理 - 方案确认
      if (nodeId === "scheme_confirm" && (ev.requires_interaction || ev.schemes)) {
        addLog("info", "显示方案确认交互界面");
        // 如果有 schemes 直接显示，否则从 API 获取
        if (ev.schemes && Array.isArray(ev.schemes)) {
          showSchemesDirectly(ev.schemes);
        } else {
          showInteractionIfAvailable().catch((e) => addLog("error", "显示交互失败", e.message));
        }
      }
      // 特殊节点处理 - 资源恢复（全自动模式）
      if (nodeId === "recover_stitch_assets") {
        state.recoveryProgress.active = true;
        state.recoveryProgress.phase = "started";
        state.recoveryProgress.message = ev.message || "开始自动恢复资源...";
        state.recoveryProgress.checkCount = 0;
        // 显示自动恢复状态面板
        showAutoRecoverStatus();
        // 更新当前节点状态
        updateCurrentNodeStatus("自动恢复资源");
      }

      // 更新当前节点显示
      updateCurrentNodeStatus(NODE_LABELS[nodeId] || nodeId);
      break;

    case "node_end": {
      const endNodeId = ev.node || ev.node_name;
      if (endNodeId && state.nodes[endNodeId]) {
        state.nodes[endNodeId].status = ev.success !== false ? "done" : "error";
        state.nodes[endNodeId].endMs = timestamp;
        if (state.nodes[endNodeId].startMs) {
          state.nodes[endNodeId].durationMs = timestamp - state.nodes[endNodeId].startMs;
        }
        state.nodes[endNodeId].output = ev;
      }
      addLog("info", `节点完成: ${NODE_LABELS[endNodeId] || endNodeId}`, ev.message);
      renderTimeline();
      renderGraph();
      if (selectedNode === endNodeId) selectNode(endNodeId);

      // 隐藏交互
      if (endNodeId === "scheme_confirm" || endNodeId === "recover_stitch_assets") {
        hideInteraction();
        state.recoveryProgress.active = false;
      }
      break;
    }

    case "node_error": {
      const errNodeId = ev.node || ev.node_name;
      if (errNodeId && state.nodes[errNodeId]) {
        state.nodes[errNodeId].status = "error";
        state.nodes[errNodeId].endMs = timestamp;
        state.nodes[errNodeId].output = ev;
      }
      addLog("error", `节点异常: ${NODE_LABELS[errNodeId] || errNodeId}`, ev.error || ev.message);
      renderTimeline();
      renderGraph();
      if (selectedNode === errNodeId) selectNode(errNodeId);
      break;
    }

    case "node_warning": {
      const warnNodeId = ev.node || ev.node_name;
      addLog("warn", `节点警告: ${NODE_LABELS[warnNodeId] || warnNodeId}`, ev.warning || ev.message);
      break;
    }

    // 恢复进度事件
    case "recover_waiting":
      state.recoveryProgress.phase = "waiting";
      state.recoveryProgress.message = ev.message || "等待服务器完成生成...";
      addLog("info", "恢复等待", `等待 ${formatSeconds(ev.wait_seconds || 300)}`);
      updateAutoRecoverProgress(
        "⏳ 等待服务器完成生成...",
        `剩余 ${formatSeconds(ev.wait_seconds || 300)}`,
        "开始等待服务器完成资源生成..."
      );
      if (selectedNode === "recover_stitch_assets") selectNode("recover_stitch_assets");
      break;

    case "recover_polling":
      state.recoveryProgress.phase = "polling";
      state.recoveryProgress.checkCount = ev.check_count || state.recoveryProgress.checkCount + 1;
      state.recoveryProgress.remainingSeconds = ev.remaining_seconds || 0;
      state.recoveryProgress.message = ev.message || "正在轮询检查资源...";
      addLog("info", `恢复轮询 #${state.recoveryProgress.checkCount}`, ev.message);

      // 更新自动恢复面板
      const pct = Math.min(100, (state.recoveryProgress.checkCount / 10) * 100);
      updateAutoRecoverProgress(
        "🔄 轮询检查资源中...",
        `第 ${state.recoveryProgress.checkCount} 次检查 · 剩余 ${formatSeconds(state.recoveryProgress.remainingSeconds || 0)}`,
        ev.message
      );

      renderTimeline();
      if (selectedNode === "recover_stitch_assets") selectNode("recover_stitch_assets");
      break;

    case "recover_success":
      state.recoveryProgress.phase = "success";
      state.recoveryProgress.message = "资源恢复成功！";
      addLog("info", "恢复成功", `第 ${ev.check_count} 次检查获取到资源`);
      updateAutoRecoverProgress(
        "✅ 资源恢复成功！",
        `共检查 ${ev.check_count} 次`,
        "成功获取到 Screens 和 HTML 资源"
      );
      // 2秒后隐藏恢复面板
      setTimeout(() => hideAutoRecoverBox(), 2000);
      renderTimeline();
      break;

    case "recover_check_project":
      addLog("info", "检查项目状态", ev.message);
      updateAutoRecoverProgress(null, null, ev.message);
      break;

    case "error":
      addLog("error", ev.message || "未知错误", ev);
      el("totalMs").textContent = `错误: ${ev.message || "未知错误"}`;
      break;

    default:
      addLog("debug", `未处理事件: ${eventType}`, ev);
  }
}

function parseSSEBlocks(buffer) {
  const events = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";

  for (const block of parts) {
    let dataLine = null;
    let idLine = null;

    for (const line of block.split("\n")) {
      if (line.startsWith("data: ")) dataLine = line.slice(6);
      if (line.startsWith("id: ")) idLine = line.slice(4);
    }

    if (dataLine) {
      try {
        events.push(JSON.parse(dataLine));
      } catch (e) {
        events.push({ event_type: "parse_error", raw: dataLine, error: e.message });
      }
    }
  }

  return { events, rest };
}

// ==================== 运行控制 ====================

function resetState() {
  state.aborted = false;
  state.logs = [];
  state.recoveryProgress = {
    active: false,
    phase: "",
    checkCount: 0,
    totalChecks: 10,
    remainingSeconds: 0,
    message: "",
  };

  for (const id of NODE_ORDER) {
    state.nodes[id] = {
      id,
      status: "pending",
      startMs: null,
      endMs: null,
      durationMs: null,
      output: null,
      input: null,
    };
  }

  el("totalMs").textContent = "—";
  el("detailJson").innerHTML = "";

  // 重置当前节点状态
  const currentNodeRow = el("currentNodeRow");
  if (currentNodeRow) currentNodeRow.style.display = "none";
  const currentNode = el("currentNode");
  if (currentNode) {
    currentNode.textContent = "—";
    currentNode.className = "node-status";
  }

  // 重置状态栏
  const statusEl = el("workflowStatus");
  if (statusEl) {
    statusEl.textContent = "运行中...";
    statusEl.className = "status-item running";
  }
  el("detailNode").textContent = "点击节点查看详情";
  hideInteraction();
  selectedNode = null;

  renderTimeline();
  renderGraph();
  if (activeView === VIEW.LOGS) renderLogs();
}

async function startRun() {
  resetState();

  const product_name = el("productName").value.trim() || "未命名产品";
  const product_group = el("productGroup").value.trim() || "默认组";
  const runId = `ui-${Date.now()}`;
  state.runId = runId;
  el("runIdDisplay").textContent = runId;

  el("btnRun").disabled = true;
  el("btnCancel").disabled = false;

  addLog("info", "开始运行", { product_name, product_group, run_id: runId });

  state.controller = new AbortController();
  const { signal } = state.controller;

  try {
    const res = await fetch("/stream_run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-run-id": runId,
        "x-workflow-stream-mode": "debug",
      },
      body: JSON.stringify({ product_name, product_group }),
      signal,
    });

    if (!res.ok) {
      const text = await res.text();
      addLog("error", `HTTP ${res.status}`, text);
      el("totalMs").textContent = `HTTP ${res.status}`;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (!state.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const { events, rest } = parseSSEBlocks(buf);
      buf = rest;
      for (const ev of events) {
        applyEvent(ev);
      }
    }

    addLog("info", "SSE 连接已关闭");
  } catch (e) {
    if (e.name === "AbortError") {
      addLog("warn", "用户取消运行");
    } else {
      addLog("error", "运行异常", e.message);
      el("totalMs").textContent = "请求失败";
    }
  } finally {
    el("btnRun").disabled = false;
    el("btnCancel").disabled = true;
    state.controller = null;

    // 如果没有收到 workflow_end 事件，更新状态栏为错误
    const statusEl = el("workflowStatus");
    if (statusEl && statusEl.textContent === "运行中...") {
      statusEl.textContent = "❌ 异常结束";
      statusEl.className = "status-item error";
    }

    // 隐藏当前节点状态
    const currentNodeRow = el("currentNodeRow");
    if (currentNodeRow) currentNodeRow.style.display = "none";
  }
}

function cancelRun() {
  state.aborted = true;
  if (state.controller) {
    state.controller.abort();
    addLog("warn", "正在取消运行...");
  }

  // 更新状态栏
  const statusEl = el("workflowStatus");
  if (statusEl) {
    statusEl.textContent = "⏹ 已取消";
    statusEl.className = "status-item";
  }

  // 隐藏当前节点状态
  const currentNodeRow = el("currentNodeRow");
  if (currentNodeRow) currentNodeRow.style.display = "none";
}

// ==================== 视图切换 ====================

function setView(v) {
  activeView = v;

  // 更新 Tab 状态
  el("tabGraph").classList.toggle("active", v === VIEW.GRAPH);
  el("tabGraph").setAttribute("aria-selected", v === VIEW.GRAPH);
  el("tabTimeline").classList.toggle("active", v === VIEW.TIMELINE);
  el("tabTimeline").setAttribute("aria-selected", v === VIEW.TIMELINE);
  el("tabLogs").classList.toggle("active", v === VIEW.LOGS);
  el("tabLogs").setAttribute("aria-selected", v === VIEW.LOGS);

  // 显示/隐藏内容
  el("graphWrap").style.display = v === VIEW.GRAPH ? "block" : "none";
  el("timeline").classList.toggle("timeline-hidden", v !== VIEW.TIMELINE);
  el("timeline").setAttribute("aria-hidden", v !== VIEW.TIMELINE);
  el("logs")?.classList.toggle("logs-hidden", v !== VIEW.LOGS);

  // 渲染对应视图
  if (v === VIEW.TIMELINE) renderTimeline();
  if (v === VIEW.GRAPH) renderGraph();
  if (v === VIEW.LOGS) renderLogs();
}

// ==================== 初始化 ====================

el("btnRun").addEventListener("click", startRun);
el("btnCancel").addEventListener("click", cancelRun);
el("tabGraph").addEventListener("click", () => setView(VIEW.GRAPH));
el("tabTimeline").addEventListener("click", () => setView(VIEW.TIMELINE));
el("tabLogs")?.addEventListener("click", () => setView(VIEW.LOGS));

// 初始化
resetState();
setView(VIEW.GRAPH);
