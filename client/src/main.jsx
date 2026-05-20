import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import {
  absoluteApiPath,
  deleteConversation,
  getConversation,
  getSkills,
  listConversations,
  streamChat,
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
  const dragRef = useRef({ active: false, moved: false, offsetX: 0, offsetY: 0 });
  const [open, setOpen] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sideDrawer, setSideDrawer] = useState(null);
  const [sideDrawerStyle, setSideDrawerStyle] = useState({});
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
  const [skills, setSkills] = useState([]);
  const [webSearch, setWebSearch] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  useEffect(() => {
    refreshHistory();
    getSkills().then(setSkills);
  }, []);

  useEffect(() => {
    const update = () => updateSideDrawerPosition();
    update();
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("resize", update);
      if (answerTimerRef.current) window.clearInterval(answerTimerRef.current);
    };
  }, [open, fullscreen, sideDrawer]);

  async function refreshHistory() {
    setHistory(await listConversations());
  }

  function updateSideDrawerPosition() {
    if (!workspaceRef.current) return;
    const rect = workspaceRef.current.getBoundingClientRect();
    const top = Math.max(0, rect.top);
    setSideDrawerStyle({
      top: `${top}px`,
      right: `${Math.max(12, window.innerWidth - rect.right)}px`,
      width: `${Math.min(360, rect.width * 0.42)}px`,
      height: `${Math.min(rect.height, window.innerHeight - top - 16)}px`,
      maxHeight: `${window.innerHeight - top - 16}px`,
    });
  }

  function revealAnswer(text, apply) {
    if (answerTimerRef.current) window.clearInterval(answerTimerRef.current);
    let index = 0;
    apply("");
    answerTimerRef.current = window.setInterval(() => {
      index += 2;
      apply(text.slice(0, index));
      if (index >= text.length) {
        window.clearInterval(answerTimerRef.current);
        answerTimerRef.current = null;
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

  function handleLauncherPointerDown(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    dragRef.current = {
      active: true,
      moved: false,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    window.addEventListener("pointermove", handleLauncherPointerMove);
    window.addEventListener("pointerup", handleLauncherPointerUp, { once: true });
  }

  function handleLauncherPointerMove(event) {
    if (!dragRef.current.active) return;
    const nextLeft = Math.min(Math.max(8, event.clientX - dragRef.current.offsetX), window.innerWidth - 76);
    const nextTop = Math.min(Math.max(8, event.clientY - dragRef.current.offsetY), window.innerHeight - 76);
    dragRef.current.moved = true;
    setLauncherPosition({ left: nextLeft, top: nextTop });
  }

  function handleLauncherPointerUp() {
    dragRef.current.active = false;
    window.removeEventListener("pointermove", handleLauncherPointerMove);
  }

  function handleLauncherClick() {
    if (dragRef.current.moved) {
      dragRef.current.moved = false;
      return;
    }
    setOpen((value) => !value);
  }

  async function ask(text = input) {
    const content = text.trim();
    if (!content || loading) return;

    setInput("");
    setLoading(true);
    setSql("");
    setCanvas({ ...emptyCanvas, title: "正在生成答案...", subtitle: "左侧执行链动态推进，右侧卡片会逐步生成" });
    setSteps([]);
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
            setSteps((items) => [...items, event.data]);
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
              setCardPool((items) => [
                { id: `${Date.now()}`, title: event.data.title, time: new Date().toLocaleTimeString(), canvas: event.data },
                ...items.slice(0, 9),
              ]);
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
  }

  async function loadHistory(id) {
    const data = await getConversation(id);
    const restoredMessages = [];
    data.messages.forEach((message) => {
      if (message.role === "user") {
        restoredMessages.push({ role: "user", content: message.content });
      } else {
        setSteps(message.content.visible_steps || []);
        setSql(message.content.sql || "");
        setCanvas(message.content.canvas || emptyCanvas);
      }
    });
    setConversationId(id);
    setMessages(restoredMessages);
    setDrawerOpen(false);
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
        drawerStyle={sideDrawerStyle}
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

            <ExecutionPanel steps={steps} sql={sql} skills={skills} loading={loading} />

            <footer className="composer chat-input-bar">
              <div className="input-toolbar">
                <button className={`searchPill web-search-pill ${webSearch ? "active" : ""}`} onClick={() => setWebSearch((value) => !value)}>
                  <i className="fa-solid fa-globe" />
                  <span>联网搜索</span>
                </button>
              </div>
              <div className="input-wrapper">
                <textarea
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

function HistoryDrawer({ active, history, currentId, onClose, onNew, onLoad, onDelete }) {
  return (
    <>
      <div className={`drawerOverlay ${active ? "active" : ""}`} onClick={onClose} />
      <aside className={`historyDrawer ${active ? "active" : ""}`}>
        <header>
          <strong>历史会话</strong>
          <button onClick={onClose}>×</button>
        </header>
        <div className="drawerNew">
          <button onClick={onNew}>＋ 新建对话</button>
        </div>
        <div className="drawerList">
          {history.length === 0 && <p className="muted">暂无历史会话</p>}
          {history.map((item) => (
            <button className={`drawerItem ${item.id === currentId ? "active" : ""}`} key={item.id} onClick={() => onLoad(item.id)}>
              <span>
                <b>{item.title}</b>
                <small>{new Date(item.updated_at).toLocaleString()}</small>
              </span>
              <i onClick={(event) => onDelete(item.id, event)}>🗑</i>
            </button>
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

function ExecutionPanel({ steps, sql, skills, loading }) {
  const [showSql, setShowSql] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
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
      {sql && (
        <div className="sqlBox">
          <button onClick={() => setShowSql((value) => !value)}>{showSql ? "折叠 SQL" : "查看 SQL"}</button>
          {showSql && <pre>{sql}</pre>}
        </div>
      )}
      <details className="skills">
        <summary>可用 Skill 注册表</summary>
        {skills.map((skill) => (
          <p key={skill.id}><b>{skill.name}</b> · {skill.tools.join(" / ")}</p>
        ))}
      </details>
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
            {step.input && <span><strong>Input</strong><code>{formatJson(step.input)}</code></span>}
            {step.output && <span><strong>Output</strong><code>{formatJson(step.output)}</code></span>}
          </span>
        )}
      </span>
    </button>
  );
}

function formatJson(value) {
  if (typeof value === "string") return value;
  return JSON.stringify(
    value,
    (key, item) => {
      if (typeof item === "string" && item.length > 140) {
        return `${item.slice(0, 140)}...`;
      }
      return item;
    },
    2,
  );
}

function Canvas({ payload, onOpenCatalog, onOpenPool, onToggleCollapse }) {
  return (
    <section className="canvasPane bi-canvas">
      <header className="canvasHead canvas-header">
        <div className="canvas-header-left">
          <h2>{payload.title}</h2>
          <span className="canvas-subtitle">{payload.subtitle}</span>
        </div>
        <div className="canvasActions canvas-controls">
          <button className="canvas-btn" onClick={onToggleCollapse} title="切换全屏/精简态" aria-label="切换全屏/精简态"><i className="fa-solid fa-angle-left" /><span>收起</span></button>
          <button className="canvas-btn" onClick={onOpenPool} title="卡片历史" aria-label="卡片历史"><i className="fa-solid fa-layer-group" /><span>卡片历史</span></button>
          <button className="canvas-btn" onClick={onOpenCatalog} title="可访问数据" aria-label="可访问数据"><i className="fa-solid fa-database" /><span>可访问数据</span></button>
          <a className="canvas-btn primary" href={absoluteApiPath("/api/downloads/mock-detail.csv")} title="下载明细 Excel">
            <img src="/assets/icons/file-excel.svg" alt="" /><span>明细Excel</span>
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

function WorkspaceSideDrawer({ drawerStyle, type, items, onClose, onLoadCard }) {
  const active = !!type;
  const [query, setQuery] = useState("");
  if (type === "pool") {
    return (
      <aside className={`card-pool-drawer ${active ? "active" : ""}`} style={drawerStyle}>
        <header className="card-pool-header"><span><i className="fa-solid fa-layer-group" /> 卡片历史</span><button className="header-btn" onClick={onClose}><i className="fa-solid fa-xmark" /></button></header>
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
    );
  }
  if (type !== "catalog") return null;
  const normalized = query.trim().toLowerCase();
  const visibleDomains = catalogDomains.filter((domain) => {
    const text = `${domain.name} ${domain.title} ${domain.type} ${domain.search} ${domain.fields.flat().join(" ")}`.toLowerCase();
    return !normalized || text.includes(normalized);
  });
  return (
    <aside className="catalog-drawer active" style={drawerStyle}>
      <header className="catalog-header"><h3><i className="fa-solid fa-database" /> 可访问数据</h3><button className="header-btn" onClick={onClose}><i className="fa-solid fa-xmark" /></button></header>
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
  );
}

createRoot(document.getElementById("root")).render(<App />);
