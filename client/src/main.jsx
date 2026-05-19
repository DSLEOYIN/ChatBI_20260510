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

function App() {
  const [open, setOpen] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sideDrawer, setSideDrawer] = useState(null);
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

  async function refreshHistory() {
    setHistory(await listConversations());
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
            setCanvas((current) => ({
              ...current,
              title: "正在装配业务答案...",
              subtitle: event.data,
            }));
          }
          if (event.type === "canvas") {
            setCanvas(event.data);
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
      <button className="launcher" onClick={() => setOpen((value) => !value)} aria-label="打开 ChatBI">
        <span>AI</span>
        <i />
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
        <main className={`workspace ${fullscreen ? "fullscreen" : ""}`}>
          <section className="chatPane">
            <HistoryDrawer
              active={drawerOpen}
              history={history}
              currentId={conversationId}
              onClose={() => setDrawerOpen(false)}
              onNew={newChat}
              onLoad={loadHistory}
              onDelete={removeHistory}
            />

            <header className="topbar">
              <div className="brand">
                <div className="avatar"><img src="/assets/assistant-avatar.png" alt="AI 助手" /></div>
                <div>
                  <strong>问数审计工作台</strong>
                  <span>Ask → Trace → Answer</span>
                </div>
              </div>
              <div className="toolbar">
                <button onClick={() => setDrawerOpen(true)} title="历史会话记录">☰</button>
                <button onClick={newChat} title="新建对话">＋</button>
                <button onClick={() => setFullscreen((value) => !value)} title="展开/收起">{fullscreen ? "↙" : "↗"}</button>
                <button onClick={() => setOpen(false)} title="关闭">×</button>
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

            <footer className="composer">
              <button className={`searchPill ${webSearch ? "active" : ""}`} onClick={() => setWebSearch((value) => !value)}>
                联网搜索
              </button>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    ask();
                  }
                }}
                placeholder="输入销量、库存、订单、排产、指标口径问题..."
              />
              <button className="sendBtn" onClick={() => ask()} disabled={loading}>发送</button>
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
    <div className="welcome">
      <h3>从这里开始问数</h3>
      <p>左侧记录每次问数的执行链路，点击任一节点即可查看输入参数、输出参数、SQL、工具调用、耗时与修复记录；右侧只保留业务用户需要消费的答案和图表。</p>
      <div className="auditPrinciples">
        <div><strong>可追溯</strong><span>每个指标都能回到口径、字段、SQL 与数据源。</span></div>
        <div><strong>可复核</strong><span>节点输入输出结构化展示，便于数据团队审查。</span></div>
        <div><strong>结果清爽</strong><span>右侧只呈现结论、图表、明细和行动建议。</span></div>
      </div>
      <div className="sampleGrid">
        {samples.map((sample) => (
          <button key={sample} onClick={() => onAsk(sample)}>
            <span>{sample}</span>
            <b>›</b>
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
          <div className={`step ${step.status}`} key={`${step.name}-${index}`}>
            <b>{step.name}</b>
            <span>{step.detail}</span>
          </div>
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

function Canvas({ payload, onOpenCatalog, onOpenPool, onToggleCollapse }) {
  return (
    <section className="canvasPane">
      <header className="canvasHead">
        <div>
          <strong>{payload.title}</strong>
          <span>{payload.subtitle}</span>
        </div>
        <div className="canvasActions">
          <button className="iconOnly" onClick={onToggleCollapse} title="切换全屏/精简态">‹</button>
          <button onClick={onOpenPool}>卡片历史</button>
          <button onClick={onOpenCatalog}>可访问数据</button>
          <a href={absoluteApiPath("/api/downloads/mock-detail.csv")}>明细Excel</a>
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
  const active = !!type;
  if (type === "pool") {
    return (
      <aside className={`workspaceSideDrawer ${active ? "active" : ""}`}>
        <header><strong>卡片历史</strong><button onClick={onClose}>×</button></header>
        <div className="drawerBody">
          {items.length === 0 && <p className="muted">暂无卡片历史</p>}
          {items.map((item, index) => (
            <button className={`poolItem ${index === 0 ? "active" : ""}`} key={item.id} onClick={() => onLoadCard(item)}>
              <b>{item.title}</b>
              <span>{item.time}</span>
            </button>
          ))}
        </div>
      </aside>
    );
  }
  if (type !== "catalog") return <aside className="workspaceSideDrawer" />;
  const domains = [
    ["库存场景", "v_dm_sal_stock_dly", "库存周转、在途、在店、库龄、安全线"],
    ["物流排产", "v_dm_sal_scheduling_dly", "计划、到货、下线、船期剪刀差"],
    ["销售订单", "v_dm_sal_sc_order_dly", "订单、线索、成交、取消"],
    ["批发终端", "v_dm_sal_wolesale_terminal_dly", "批发量、终端量、国家、车型"],
  ];
  return (
    <aside className={`workspaceSideDrawer catalog active`}>
      <header><strong>可访问数据</strong><button onClick={onClose}>×</button></header>
      <div className="drawerBody">
        {domains.map(([name, table, desc]) => (
          <details open key={table}>
            <summary>{name}</summary>
            <b>{table}</b>
            <p>{desc}</p>
          </details>
        ))}
      </div>
    </aside>
  );
}

createRoot(document.getElementById("root")).render(<App />);
