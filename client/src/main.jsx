import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import {
  absoluteApiPath,
  deleteConversation,
  getConversation,
  listConversations,
  streamChat,
  pinConversation,
} from "./services/api";
import "./styles.css";

const samples = [
  "诊断中东公司 GS8 车型本月的库存异常并给出建议",
  "分析本月中东公司车型排产与实际到货差额",
  "GS8 当前库存是多少，是否超过安全线",
  "什么是库存周转天数，计算公式是什么",
];

const emptyCanvas = {
  title: "业务答案画布",
  subtitle: "结论、图表、明细与建议",
  intent: "chat",
  components: [],
};

const catalogDomains = [
  {
    name: "v_dm_sal_stock_dly",
    title: "库存场景：车型库存、锁定、可售、零售与周转日表",
    type: "库存域",
    search: "库存 场景 inventory stock 库存周转 v_dm_sal_stock_dly area_name country_name model_code model_name stock_qty dlr_onway_qty turnover_days",
    fields: [
      ["area_name / 区域名称", "大区或子公司名称，当前默认过滤为中东公司。", "维度"],
      ["country_name / 国家", "库存归属国家，可用于国家下钻。", "维度"],
      ["model_code / 车型编码", "车型编码，用于精确关联车型主数据。", "维度"],
      ["model_name / 车型名称", "车型名称，可用于车型级库存和动销分析。", "维度"],
      ["stock_qty / 在店库存", "经销商在店库存数量。", "指标"],
      ["dlr_onway_qty / 经销商在途", "已发运但尚未到店的在途库存。", "指标"],
      ["turnover_days / 库存周转天数", "用于判断库存健康度的派生指标。", "派生"],
    ],
  },
  {
    name: "v_dm_sal_scheduling_dly",
    title: "物流场景：排产、发运、到港、清关与到货日表",
    type: "物流域",
    search: "物流 排产 到货 剪刀差 scheduling plan arrival shipment gap",
    fields: [
      ["offline_qty / 下线量", "生产下线数量。", "指标"],
      ["delivery_qty / 交付量", "已交付或到货数量。", "指标"],
      ["plan_qty / 排产计划", "月度排产计划数量。", "指标"],
      ["gap_qty / 到货零售差异", "到货量 - 零售量，用于识别阶段性剪刀差。", "派生"],
    ],
  },
  {
    name: "v_dm_sal_sc_order_dly",
    title: "销售场景：SC 订单、新增订单与车型订单分析",
    type: "销售域",
    search: "销售 订单 SC order lead contract cancel",
    fields: [
      ["order_qty / 新增订单", "统计周期内新增 SC 订单数量。", "指标"],
      ["remain_order_qty / 剩余订单", "尚未完成交付的订单数量。", "指标"],
      ["model_name / 车型名称", "车型名称，可用于车型级订单分析。", "维度"],
      ["country_name / 国家", "订单所属国家。", "维度"],
    ],
  },
  {
    name: "v_dm_sal_wolesale_terminal_dly",
    title: "批发终端：批发量、终端量、区域/国家/车型分析",
    type: "经营域",
    search: "批发 终端 销量 wholesale terminal target achievement",
    fields: [
      ["wholesale_qty / 批发量", "批发给渠道或子公司的车辆数量。", "指标"],
      ["terminal_qty / 终端销量", "终端零售成交数量。", "指标"],
      ["target_qty / 目标", "当月销量目标。", "指标"],
      ["achievement_rate / 达成率", "终端销量 / 目标。", "派生"],
    ],
  },
];

function App() {
  const workspaceRef = useRef(null);
  const answerTimerRef = useRef(null);
  const dragRef = useRef({
    active: false,
    moved: false,
    startX: 0,
    startY: 0,
    originalLeft: 0,
    originalTop: 0,
    offsetX: 0,
    offsetY: 0,
  });
  const [open, setOpen] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sideDrawer, setSideDrawer] = useState(null);
  const [launcherPosition, setLauncherPosition] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [canvas, setCanvas] = useState(emptyCanvas);
  const [cardPool, setCardPool] = useState([]);
  const [sql, setSql] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [webSearch, setWebSearch] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const textareaRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);
  const [activeStep, setActiveStep] = useState(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const targetHeight = Math.min(textarea.scrollHeight, 100);
    textarea.style.height = `${targetHeight}px`;
  }, [input]);

  useEffect(() => {
    refreshHistory();
    return () => {
      if (answerTimerRef.current) window.clearInterval(answerTimerRef.current);
    };
  }, []);

  async function handlePinHistory(id, pinned) {
    try {
      await pinConversation(id, pinned);
      await refreshHistory();
    } catch (error) {
      console.error("Pin conversation failed:", error);
    }
  }

  async function refreshHistory() {
    setHistory(await listConversations());
  }

  function clampLauncherPosition(left, top) {
    const margin = 8;
    const launcherWidth = 68;
    const launcherHeight = 68;
    return {
      left: Math.max(margin, Math.min(window.innerWidth - launcherWidth - margin, left)),
      top: Math.max(margin, Math.min(window.innerHeight - launcherHeight - margin, top)),
    };
  }

  function snapLauncherToEdge(currentLeft, currentTop) {
    const margin = 8;
    const launcherWidth = 68;
    const snapLeft = currentLeft < (window.innerWidth - launcherWidth) / 2;
    const finalLeft = snapLeft ? margin : window.innerWidth - launcherWidth - margin;
    return { left: finalLeft, top: currentTop };
  }

  const updateWorkspaceCSSVariables = (rect) => {
    const root = document.documentElement;
    root.style.setProperty("--workspace-top", `${rect.top}px`);
    root.style.setProperty("--workspace-right", `${window.innerWidth - rect.right}px`);
    root.style.setProperty("--workspace-width", `${rect.width}px`);
    root.style.setProperty("--workspace-height", `${rect.height}px`);
  };

  const updateWorkspaceMetricsFromDOM = () => {
    if (!workspaceRef.current) return;
    const rect = workspaceRef.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    updateWorkspaceCSSVariables(rect);
  };

  const positionWorkspaceNearLauncher = (customLauncherRect = null) => {
    if (fullscreen || !workspaceRef.current) return;
    const launcherEl = document.getElementById("chat-launcher");
    if (!launcherEl) return;
    const launcherRect = customLauncherRect || launcherEl.getBoundingClientRect();
    const workspaceWidth = Math.min(920, window.innerWidth - 40);
    const workspaceHeight = Math.min(740, window.innerHeight - 120);
    const margin = 20;
    const gap = 14;
    const anchorX = launcherRect.left + launcherRect.width / 2;
    const anchorY = launcherRect.top + launcherRect.height / 2;

    let left = anchorX < window.innerWidth / 2 ? launcherRect.left : launcherRect.right - workspaceWidth;
    let top = launcherRect.top - workspaceHeight - gap;
    if (top < margin) top = launcherRect.bottom + gap;
    if (top + workspaceHeight > window.innerHeight - margin) top = anchorY - workspaceHeight / 2;

    left = Math.max(margin, Math.min(window.innerWidth - workspaceWidth - margin, left));
    top = Math.max(margin, Math.min(window.innerHeight - workspaceHeight - margin, top));

    workspaceRef.current.style.left = `${left}px`;
    workspaceRef.current.style.top = `${top}px`;
    workspaceRef.current.style.right = "auto";
    workspaceRef.current.style.bottom = "auto";
    const originX = Math.max(0, Math.min(workspaceWidth, anchorX - left));
    const originY = Math.max(0, Math.min(workspaceHeight, anchorY - top));
    workspaceRef.current.style.transformOrigin = `${originX}px ${originY}px`;

    updateWorkspaceCSSVariables({ left, top, width: workspaceWidth, height: workspaceHeight, right: left + workspaceWidth });
  };

  useEffect(() => {
    if (open) {
      if (fullscreen) {
        if (workspaceRef.current) {
          workspaceRef.current.style.transition = 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
          workspaceRef.current.style.left = '20px';
          workspaceRef.current.style.top = '20px';
          workspaceRef.current.style.right = '20px';
          workspaceRef.current.style.bottom = '20px';
          workspaceRef.current.style.width = 'auto';
          workspaceRef.current.style.height = 'auto';
          workspaceRef.current.style.transformOrigin = 'center center';
        }
        updateWorkspaceMetricsFromDOM();
        const t1 = setTimeout(updateWorkspaceMetricsFromDOM, 50);
        const t2 = setTimeout(updateWorkspaceMetricsFromDOM, 360);
        const t3 = setTimeout(updateWorkspaceMetricsFromDOM, 520);
        return () => {
          clearTimeout(t1);
          clearTimeout(t2);
          clearTimeout(t3);
        };
      } else {
        if (workspaceRef.current) {
          workspaceRef.current.style.transition = '';
          workspaceRef.current.style.width = '';
          workspaceRef.current.style.height = '';
        }
        positionWorkspaceNearLauncher();
        const t1 = setTimeout(() => positionWorkspaceNearLauncher(), 50);
        const t2 = setTimeout(() => positionWorkspaceNearLauncher(), 360);
        return () => {
          clearTimeout(t1);
          clearTimeout(t2);
        };
      }
    }
  }, [open, fullscreen]);

  useEffect(() => {
    const handleResize = () => {
      if (open) {
        if (fullscreen) {
          updateWorkspaceMetricsFromDOM();
        } else {
          positionWorkspaceNearLauncher();
        }
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [open, fullscreen]);

  function handleLauncherPointerDown(event) {
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    dragRef.current = {
      active: true,
      moved: false,
      startX: event.clientX,
      startY: event.clientY,
      originalLeft: rect.left,
      originalTop: rect.top,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    event.currentTarget.style.transition = "none";
    event.currentTarget.setPointerCapture?.(event.pointerId);
    window.addEventListener("pointermove", handleLauncherPointerMove);
    window.addEventListener("pointerup", handleLauncherPointerUp, { once: true });
  }

  function handleLauncherPointerMove(event) {
    if (!dragRef.current.active) return;
    const dx = event.clientX - dragRef.current.startX;
    const dy = event.clientY - dragRef.current.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      dragRef.current.moved = true;
    }
    const targetLeft = dragRef.current.originalLeft + dx;
    const targetTop = dragRef.current.originalTop + dy;
    const clamped = clampLauncherPosition(targetLeft, targetTop);

    setLauncherPosition(clamped);

    if (open && !fullscreen) {
      const launcherWidth = 68;
      const launcherHeight = 68;
      const launcherRect = {
        left: clamped.left,
        top: clamped.top,
        width: launcherWidth,
        height: launcherHeight,
        right: clamped.left + launcherWidth,
        bottom: clamped.top + launcherHeight,
      };
      positionWorkspaceNearLauncher(launcherRect);
    }
  }

  function handleLauncherPointerUp(event) {
    if (!dragRef.current.active) return;
    dragRef.current.active = false;
    window.removeEventListener("pointermove", handleLauncherPointerMove);

    const launcherEl = document.getElementById("chat-launcher");
    if (launcherEl) {
      launcherEl.style.transition =
        "left 0.28s cubic-bezier(0.16, 1, 0.3, 1), top 0.28s cubic-bezier(0.16, 1, 0.3, 1), transform 0.28s ease, border-radius 0.28s ease";
    }

    const rect = launcherEl
      ? launcherEl.getBoundingClientRect()
      : { left: event.clientX - dragRef.current.offsetX, top: event.clientY - dragRef.current.offsetY };
    const clamped = clampLauncherPosition(rect.left, rect.top);
    const snapped = snapLauncherToEdge(clamped.left, clamped.top);

    setLauncherPosition(snapped);

    if (open && !fullscreen) {
      const launcherWidth = 68;
      const launcherHeight = 68;
      const launcherRect = {
        left: snapped.left,
        top: snapped.top,
        width: launcherWidth,
        height: launcherHeight,
        right: snapped.left + launcherWidth,
        bottom: snapped.top + launcherHeight,
      };
      positionWorkspaceNearLauncher(launcherRect);
    }
  }

  function handleLauncherClick() {
    if (dragRef.current.moved) {
      dragRef.current.moved = false;
      return;
    }
    setOpen((value) => !value);
  }

  function revealAnswer(text, apply) {
    if (answerTimerRef.current) window.clearInterval(answerTimerRef.current);
    let index = 0;
    setIsTyping(true);
    apply("");
    answerTimerRef.current = window.setInterval(() => {
      index += 2;
      apply(text.slice(0, index));
      if (index >= text.length) {
        window.clearInterval(answerTimerRef.current);
        answerTimerRef.current = null;
        setIsTyping(false);
      }
    }, 28);
  }

  function updateFinalAnswer(content) {
    setCanvas((current) => ({
      ...current,
      components: current.components.map((component) => (
        component.type === "answer"
          ? { ...component, props: { ...component.props, content } }
          : component
      )),
    }));
  }

  function getAutoActiveStep(items) {
    const index = items.findIndex((step) => step.status === "warning" || step.status === "error");
    return index >= 0 ? index : null;
  }

  function makeCanvasCard(canvasPayload, timestamp = new Date().toISOString()) {
    if (!canvasPayload?.components?.length) return null;
    return {
      id: `${timestamp}-${canvasPayload.title}`,
      title: canvasPayload.title,
      time: new Date(timestamp).toLocaleTimeString(),
      canvas: canvasPayload,
    };
  }

  async function ask(text = input) {
    const content = text.trim();
    if (!content || loading) return;

    setInput("");
    setLoading(true);
    setSql("");
    setCanvas({ ...emptyCanvas, title: "正在生成答案...", subtitle: "左侧执行链动态推进，右侧卡片会逐步生成" });
    setSteps([]);
    setActiveStep(null);
    setMessages((items) => [...items, { role: "user", content }]);

    try {
      await streamChat(
        {
          content,
          conversation_id: conversationId,
          user_id: "demo_user",
          mode: "quick",
          web_search: webSearch,
        },
        (event) => {
          if (event.type === "conversation_id") {
            setConversationId(event.data);
          }
          if (event.type === "step") {
            setSteps((items) => {
              const newItems = [...items, event.data];
              if (event.data.status === "warning" || event.data.status === "error") {
                setActiveStep(newItems.length - 1);
              }
              return newItems;
            });
          }
          if (event.type === "sql") {
            setSql(event.data);
          }
          if (event.type === "answer") {
            revealAnswer(event.data, (content) => {
              setCanvas((current) => ({
                ...current,
                title: "正在装配业务答案...",
                subtitle: content,
              }));
            });
          }
          if (event.type === "canvas") {
            const finalAnswer = event.data.components?.find((component) => component.type === "answer")?.props?.content || "";
            const payload = {
              ...event.data,
              components: event.data.components?.map((component) => (
                component.type === "answer"
                  ? { ...component, props: { ...component.props, content: "" } }
                  : component
              )) || [],
            };
            setCanvas(payload);
            if (finalAnswer) revealAnswer(finalAnswer, updateFinalAnswer);
            if (event.data.components?.length) {
              const card = makeCanvasCard(event.data);
              setCardPool((items) => [
                card,
                ...items.slice(0, 9),
              ].filter(Boolean));
            }
          }
        },
      );
      await refreshHistory();
    } catch (error) {
      setCanvas({
        title: "请求失败",
        subtitle: "mock 流式服务暂时不可用",
        intent: "chat",
        components: [{ id: "error-answer", type: "answer", title: "错误提示", props: { content: "请确认 FastAPI 已启动后重试。" } }],
      });
      setSteps([{ name: "请求失败", status: "error", detail: error.message }]);
    } finally {
      setLoading(false);
    }
  }

  function newChat() {
    setConversationId(null);
    setMessages([]);
    setSteps([]);
    setCanvas(emptyCanvas);
    setSql("");
    setDrawerOpen(false);
    setActiveStep(null);
  }

  async function loadHistory(id) {
    const data = await getConversation(id);
    const restoredMessages = [];
    const restoredCards = [];
    let latestAssistant = null;

    if (answerTimerRef.current) {
      window.clearInterval(answerTimerRef.current);
      answerTimerRef.current = null;
    }
    setIsTyping(false);

    data.messages.forEach((message) => {
      if (message.role === "user") {
        restoredMessages.push({ role: "user", content: message.content });
      } else {
        latestAssistant = message.content;
        const card = makeCanvasCard(message.content.canvas, message.created_at);
        if (card) restoredCards.unshift(card);
      }
    });

    const restoredSteps = latestAssistant?.visible_steps || [];
    setConversationId(id);
    setMessages(restoredMessages);
    setSteps(restoredSteps);
    setSql(latestAssistant?.sql || "");
    setCanvas(latestAssistant?.canvas || emptyCanvas);
    setCardPool(restoredCards.slice(0, 10));
    setActiveStep(getAutoActiveStep(restoredSteps));
    setLoading(false);
    setDrawerOpen(false);
    setSideDrawer(null);
  }

  async function removeHistory(id, event) {
    event.stopPropagation();
    const item = history.find((record) => record.id === id);
    setPendingDelete(item || { id, title: "这条历史会话" });
  }

  async function confirmDeleteHistory() {
    if (!pendingDelete) return;
    const id = pendingDelete.id;
    await deleteConversation(id);
    if (id === conversationId) newChat();
    setPendingDelete(null);
    await refreshHistory();
  }

  return (
    <>
      <button
        id="chat-launcher"
        className="launcher"
        onClick={handleLauncherClick}
        onPointerDown={handleLauncherPointerDown}
        style={launcherPosition ? { left: launcherPosition.left, top: launcherPosition.top, right: "auto", bottom: "auto" } : undefined}
        aria-label="打开 ChatBI"
      >
        <div className="launcher-avatar-wrapper">
          <img src="/assets/assistant-avatar.png" alt="AI 助手" />
        </div>
        <div className="badge-dot" />
      </button>

      <WorkspaceSideDrawer
        type={sideDrawer}
        items={cardPool}
        onClose={() => setSideDrawer(null)}
        onLoadCard={(item) => {
          setCanvas(item.canvas);
          setSideDrawer(null);
        }}
      />
      <ConfirmModal
        open={!!pendingDelete}
        title="删除历史会话"
        message={`确认删除「${pendingDelete?.title || ""}」吗？删除后将无法恢复。`}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDeleteHistory}
      />

      {open && (
        <main id="workspace-container" className={`workspace ${fullscreen ? "fullscreen fullscreen-state" : ""}`} ref={workspaceRef}>
          <section className="chatPane chat-pane">
            <HistoryDrawer
              active={drawerOpen}
              history={history}
              currentId={conversationId}
              onClose={() => setDrawerOpen(false)}
              onNew={newChat}
              onLoad={loadHistory}
              onDelete={removeHistory}
              onPin={handlePinHistory}
            />

            <header className="topbar panel-header">
              <div className="brand header-title-area">
                <div className="avatar panel-avatar"><img src="/assets/assistant-avatar.png" alt="AI 助手" /></div>
                <div>
                  <strong className="panel-title">问数审计工作台</strong>
                  <span className="panel-subtitle">Ask → Trace → Answer</span>
                </div>
              </div>
              <div className="toolbar header-controls">
                <button className="header-btn" onClick={() => setDrawerOpen(true)} title="历史会话记录"><i className="fa-solid fa-clock-rotate-left" /></button>
                <button className="header-btn" onClick={newChat} title="新建对话"><i className="fa-solid fa-plus" /></button>
                <button className="header-btn" onClick={() => setFullscreen((value) => !value)} title="切换全屏/精简态">
                  <i className={`fa-solid ${fullscreen ? "fa-compress" : "fa-expand"}`} />
                </button>
                <button className="header-btn close-btn" onClick={() => setOpen(false)} title="折叠关闭工作区"><i className="fa-solid fa-xmark" /></button>
              </div>
            </header>

            <div className="messages">
              {messages.length === 0 && <WelcomeCard onAsk={ask} />}
              {messages.map((message, index) => (
                <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
                  {message.content || "正在组织答案..."}
                </div>
              ))}
            </div>

            <ExecutionPanel steps={steps} loading={loading} activeStep={activeStep} setActiveStep={setActiveStep} />

            <footer className="composer chat-input-bar">
              <div className="input-toolbar">
                <button className={`searchPill web-search-pill ${webSearch ? "active" : ""}`} onClick={() => setWebSearch((value) => !value)}>
                  <i className="fa-solid fa-globe" />
                  <span>联网搜索</span>
                </button>
              </div>
              <div className="input-wrapper">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      ask();
                    }
                  }}
                  placeholder="向智能体提问（如：查询中东各车型库存）..."
                />
                <button className={`sendBtn send-btn ${input.trim() ? "active" : ""}`} onClick={() => ask()} disabled={loading}>
                  <i className="fa-solid fa-paper-plane" />
                </button>
              </div>
              <div className="shortcut-tip">
                <span>点击左侧节点查看 I/O 参数 | 右侧只看业务答案</span>
              </div>
            </footer>
          </section>

          <Canvas
            payload={canvas}
            isTyping={isTyping}
            onToggleCollapse={() => setFullscreen((value) => !value)}
            onOpenCatalog={() => setSideDrawer(sideDrawer === "catalog" ? null : "catalog")}
            onOpenPool={() => setSideDrawer(sideDrawer === "pool" ? null : "pool")}
          />
        </main>
      )}
    </>
  );
}

function WelcomeCard({ onAsk }) {
  return (
    <div className="welcome audit-welcome">
      <h3><i className="fa-solid fa-route" /> 从这里开始问数</h3>
      <p>左侧记录每次问数的执行链路，点击任一节点即可查看输入参数、输出参数、SQL、工具调用、耗时与修复记录；右侧只保留业务用户需要消费的答案和图表。</p>
      <div className="auditPrinciples">
        <div><strong>可追溯</strong><span>每个指标都能回到口径、字段、SQL 与数据源。</span></div>
        <div><strong>可复核</strong><span>节点输入输出结构化展示，便于数据团队审查。</span></div>
        <div><strong>结果清爽</strong><span>右侧只呈现结论、图表、明细和行动建议。</span></div>
      </div>
      <div className="sampleGrid">
        {samples.map((sample, index) => (
          <button key={sample} onClick={() => onAsk(sample)}>
            <span><i className={`fa-solid ${["fa-magnifying-glass-chart", "fa-chart-line", "fa-gauge-high", "fa-book"][index]}`} />{sample}</span>
            <b><i className="fa-solid fa-chevron-right" /></b>
          </button>
        ))}
      </div>
    </div>
  );
}

function HistoryDrawer({ active, history, currentId, onClose, onNew, onLoad, onDelete, onPin }) {
  return (
    <>
      <div className={`drawerOverlay ${active ? "active" : ""}`} onClick={onClose} />
      <aside className={`historyDrawer ${active ? "active" : ""}`}>
        <header>
          <strong>历史会话</strong>
          <button onClick={onClose}>×</button>
        </header>
        <div className="drawerNew">
          <button className="newChatBtn" onClick={onNew}>
            <i className="fa-solid fa-plus" />
            <span>新建对话</span>
          </button>
        </div>
        <div className="drawerList">
          {history.length === 0 && <p className="muted">暂无历史会话</p>}
          {history.map((item) => (
            <div
              className={`drawerItem ${item.id === currentId ? "active" : ""} ${item.pinned ? "pinned" : ""}`}
              key={item.id}
              onClick={() => onLoad(item.id)}
            >
              <div className="drawerItemContent">
                <b>
                  {item.pinned && <i className="fa-solid fa-thumbtack pin-badge" title="已置顶" />}
                  <span className="drawerItemTitle">{item.title}</span>
                </b>
                <small>{new Date(item.updated_at).toLocaleString()}</small>
              </div>
              <div className="drawerItemActions">
                <button
                  className={`pin-btn ${item.pinned ? "active" : ""}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onPin(item.id, !item.pinned);
                  }}
                  title={item.pinned ? "取消置顶" : "置顶会话"}
                >
                  <i className="fa-solid fa-thumbtack" />
                </button>
                <button
                  className="delete-btn"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDelete(item.id, event);
                  }}
                  title="删除会话"
                >
                  <i className="fa-solid fa-trash-can" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

function ConfirmModal({ open, title, message, onCancel, onConfirm }) {
  if (!open) return null;
  return (
    <div className="modalBackdrop">
      <section className="confirmModal">
        <div className="modalHeaderRow">
          <div className="modalWarningIcon">!</div>
          <h3>{title}</h3>
        </div>
        <p>{message}</p>
        <div className="modalActions">
          <button className="modalBtn cancel" onClick={onCancel}>取消</button>
          <button className="modalBtn confirm" onClick={onConfirm}>确认删除</button>
        </div>
      </section>
    </div>
  );
}

function ExecutionPanel({ steps, loading, activeStep, setActiveStep }) {
  const selectedSkill = useMemo(() => {
    const skillStep = steps.find((step) => step.name === "Skill 选择");
    return skillStep?.detail || (loading ? "Agent 正在选择 Skill" : "等待提问");
  }, [loading, steps]);

  return (
    <aside className="execution">
      <div className="executionHead">
        <strong>Agent 执行链</strong>
        <span>{selectedSkill}</span>
      </div>
      <div className="stepList">
        {steps.length === 0 && <p className="muted">提问后展示用户可理解的思维链条与工具调用过程。</p>}
        {steps.map((step, index) => (
          <ExecutionStep
            active={activeStep === index}
            index={index}
            key={`${step.name}-${index}`}
            onToggle={() => setActiveStep(activeStep === index ? null : index)}
            step={step}
          />
        ))}
      </div>
    </aside>
  );
}

function ExecutionStep({ active, index, onToggle, step }) {
  const hasDetail = step.tool || step.duration || step.input || step.output;
  const ref = useRef(null);

  useEffect(() => {
    if (active && ref.current) {
      ref.current.scrollIntoView({ block: "end", behavior: "smooth" });
    }
  }, [active]);

  return (
    <button className={`step ${step.status} ${active ? "open" : ""}`} onClick={onToggle} ref={ref} type="button">
      <span className="stepIndex">{String(index + 1).padStart(2, "0")}</span>
      <span className="stepBody">
        <span className="stepTop">
          <b>{step.name}</b>
          {step.duration && <em>{step.duration}</em>}
        </span>
        <span className="stepDesc">{step.detail}</span>
        {active && hasDetail && (
          <span className="stepDetail">
            {step.tool && <span><strong>工具</strong>{step.tool}</span>}
            {step.input && <span><strong>Input</strong><code dangerouslySetInnerHTML={{ __html: highlightJson(step.input) }} /></span>}
            {step.output && <span><strong>Output</strong><code dangerouslySetInnerHTML={{ __html: highlightJson(step.output) }} /></span>}
          </span>
        )}
      </span>
    </button>
  );
}

function highlightJson(value) {
  if (value === undefined || value === null) return "";
  const str = typeof value === "string" ? value : JSON.stringify(
    value,
    (key, item) => {
      if (typeof item === "string" && item.length > 140) {
        return `${item.slice(0, 140)}...`;
      }
      return item;
    },
    2
  );
  
  // 转义 HTML 符号以防注入
  const escaped = str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, function (match) {
    let cls = "json-number";
    if (/^"/.test(match)) {
      if (/:$/.test(match)) {
        cls = "json-key";
      } else {
        cls = "json-string";
      }
    } else if (/true|false/.test(match)) {
      cls = "json-boolean";
    } else if (/null/.test(match)) {
      cls = "json-null";
    }
    return `<span class="${cls}">${match}</span>`;
  });
}

function Canvas({ payload, isTyping, onOpenCatalog, onOpenPool, onToggleCollapse }) {
  return (
    <section className="canvasPane bi-canvas">
      <header className="canvasHead canvas-header">
        <div className="canvas-header-left">
          <h2>{payload.title}</h2>
          <span className={`canvas-subtitle ${isTyping ? "typing-caret" : ""}`}>{payload.subtitle}</span>
        </div>
        <div className="canvasActions canvas-controls">
          <button className="canvas-btn" onClick={onToggleCollapse} title="切换全屏/精简态" aria-label="切换全屏/精简态"><i className="fa-solid fa-angle-left" /><span>收起</span></button>
          <button className="canvas-btn" onClick={onOpenPool} title="卡片历史" aria-label="卡片历史"><i className="fa-solid fa-layer-group" /><span>卡片历史</span></button>
          <button className="canvas-btn" onClick={onOpenCatalog} title="可访问数据" aria-label="可访问数据"><i className="fa-solid fa-database" /><span>可访问数据</span></button>
          <a className="canvas-btn primary download-excel-btn" href={absoluteApiPath("/api/downloads/mock-detail.csv")} title="下载明细 Excel">
            <i className="fa-solid fa-file-excel" /><span>下载明细</span>
          </a>
        </div>
      </header>
      {payload.components.length === 0 ? (
        <div className="emptyCanvas">
          <div>⌘</div>
          <p>业务答案将在这里生成</p>
        </div>
      ) : (
        <div className="canvasGrid">
          {payload.components.map((component, index) => (
            <CanvasComponent component={component} index={index} key={component.id} />
          ))}
        </div>
      )}
    </section>
  );
}

function CanvasComponent({ component, index }) {
  const style = { animationDelay: `${index * 70}ms` };
  if (component.type === "answer") {
    return (
      <article className="dynamicCard wide answerCard" style={style}>
        <h3>{component.title}</h3>
        <p>{component.props.content}</p>
      </article>
    );
  }
  if (component.type === "kpi_grid") {
    return (
      <article className="dynamicCard wide" style={style}>
        <h3>▦ {component.title}</h3>
        <div className="kpis">
          {component.props.items.map((item) => (
            <div className="kpi" key={item.label}>
              <span>{item.label}</span>
              <b>{item.value}<small>{item.unit}</small></b>
              <em>{item.trend}</em>
            </div>
          ))}
        </div>
      </article>
    );
  }
  if (component.type === "chart") {
    return (
      <article className="dynamicCard wide" style={style}>
        <h3>⌁ {component.title}</h3>
        <Chart option={component.props.option} />
      </article>
    );
  }
  if (component.type === "table") {
    return (
      <article className="dynamicCard wide" style={style}>
        <div className="cardTitle">
          <h3>▤ {component.title}</h3>
          <a href={absoluteApiPath(component.props.download)}>下载明细 Excel</a>
        </div>
        <table>
          <thead><tr>{component.props.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>{component.props.rows.map((row, idx) => <tr key={idx}>{row.map((cell, cidx) => <td key={`${cell}-${cidx}`}>{cell}</td>)}</tr>)}</tbody>
        </table>
      </article>
    );
  }
  if (component.type === "risk") {
    return (
      <article className="dynamicCard alertCard" style={style}>
        <div className="alertHeader"><span>{component.props.level}</span><b>{component.props.value}</b></div>
        <p>{component.props.summary}</p>
        <small>健康线：{component.props.threshold}</small>
      </article>
    );
  }
  if (component.type === "definition") {
    return (
      <article className="dynamicCard wide definitionCard" style={style}>
        <h3>指标定义</h3>
        <b>{component.title}</b>
        <p>{component.props.definition}</p>
        <code>{component.props.formula}</code>
        <p className="muted">{component.props.note}</p>
      </article>
    );
  }
  if (component.type === "search_results") {
    return (
      <article className="dynamicCard wide" style={style}>
        <h3>联网搜索结果</h3>
        {component.props.items.map((item) => (
          <div className="searchItem" key={item.title}>
            <b>{item.title}</b>
            <span>{item.source}</span>
            <p>{item.summary}</p>
          </div>
        ))}
      </article>
    );
  }
  return (
    <article className="dynamicCard wide conclusionCard" style={style}>
      <h3>{component.title}</h3>
      {(component.props.items || []).map((item) => <p key={item}>{item}</p>)}
    </article>
  );
}

function Chart({ option }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div className="chart" ref={ref} />;
}

function WorkspaceSideDrawer({ type, items, onClose, onLoadCard }) {
  const [query, setQuery] = useState("");
  const normalized = query.trim().toLowerCase();
  const visibleDomains = catalogDomains.filter((domain) => {
    const text = `${domain.name} ${domain.title} ${domain.type} ${domain.search} ${domain.fields.flat().join(" ")}`.toLowerCase();
    return !normalized || text.includes(normalized);
  });

  return (
    <>
      <aside className={`card-pool-drawer ${type === "pool" ? "active" : ""}`}>
        <header className="card-pool-header">
          <span><i className="fa-solid fa-layer-group" /> 卡片历史</span>
          <button className="header-btn" onClick={onClose}><i className="fa-solid fa-xmark" /></button>
        </header>
        <div className="card-pool-list">
          {items.length === 0 && <p className="muted">暂无卡片历史</p>}
          {items.map((item, index) => (
            <button className={`card-pool-item ${index === 0 ? "active" : ""}`} key={item.id} onClick={() => onLoadCard(item)}>
              <b className="card-pool-item-title">{item.title}</b>
              <span className="card-pool-item-preview">{item.time} · 结构化业务画布</span>
            </button>
          ))}
        </div>
      </aside>
      <aside className={`catalog-drawer ${type === "catalog" ? "active" : ""}`}>
        <header className="catalog-header">
          <h3><i className="fa-solid fa-database" /> 可访问数据</h3>
          <button className="header-btn" onClick={onClose}><i className="fa-solid fa-xmark" /></button>
        </header>
        <div className="catalog-summary">当前账号：中东公司总经理。这里展示已授权的数据资产，支持按英文表名、英文字段、中文名、业务别名和场景快速检索。</div>
        <div className="catalog-filter">
          <i className="fa-solid fa-magnifying-glass" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索表、字段、维度、指标..." />
        </div>
        <div className="catalog-list">
          <div className="catalog-section-title"><i className="fa-solid fa-table" /> 按业务场景分组的可访问表字段</div>
          {visibleDomains.map((domain) => (
            <details className="data-domain-card" open key={domain.name}>
              <summary>
                <div className="data-domain-title">
                  <strong>{domain.name}</strong>
                  <span>{domain.title}</span>
                </div>
                <div className="data-domain-meta">
                  <span className="catalog-item-type">{domain.type}</span>
                  <i className="fa-solid fa-chevron-down" />
                </div>
              </summary>
              <div className="field-list">
                {domain.fields.map(([name, desc, type]) => (
                  <div className="field-row" key={name}>
                    <div>
                      <div className="field-name">{name}</div>
                      <div className="field-desc">{desc}</div>
                    </div>
                    <span className="catalog-item-type">{type}</span>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      </aside>
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
