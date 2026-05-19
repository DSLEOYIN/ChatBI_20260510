# ChatBI React Mock Handoff

日期：2026-05-20

## 用户最终确认的产品口径

1. `前端原型/index_v3_dynamic.html` 是最终原型基准。
2. React 项目必须复刻原型效果和交互，不允许重新设计一套 UI。
3. 原型中可见能力都要保留：
   - 悬浮球
   - 精简窗口 / 全屏工作区
   - 历史会话抽屉
   - 新建对话
   - 删除历史二次确认弹窗
   - 欢迎推荐卡
   - 联网搜索开关
   - 用户可理解执行链
   - SQL 默认折叠
   - 右侧动态业务画布
   - 卡片历史
   - 可访问数据
   - 明细 Excel 下载
4. 原型当前浅色商务风格就是上线标准。
5. 第一阶段后端全部 mock，后续逐个接口切换真实 API。
6. 流式返回采用 SSE，后端逐条推送执行链、SQL、答案和画布 payload。
7. 响应要快、不卡顿；动画由前端轻量渲染。
8. 画布第一版采用结构化 JSON 组件渲染，后续允许扩展为后端返回任意 HTML。
9. 用户可见的是“可理解的思维链条”，不是暴露完整内部推理。
10. SQL 默认折叠。
11. SQL 出错自愈演示第一版可以保留。
12. Demo 数据全部使用 mock 合理数。
13. 会话历史必须持久化。
14. 用户偏好记忆第一版 mock 即可。

## 重要纠偏记录

前面曾经偏离过用户原型，创建了一套较自创的 React UI。用户明确指出：

- 原型不是那个样子。
- 不应该出现“专注报告”等原型之外的按钮文案。
- 卡片历史和可访问数据点开有 bug。
- 左边的思维链应该放在上面。
- 所有回答都应该放在右边输出。

已经按这个方向修正：

- 左侧只保留用户提问、Agent 执行链、SQL 折叠、Skill 注册表。
- AI 最终回答不再显示在左侧聊天流。
- 右侧画布新增“最终回答”卡，业务回答、图表、表格、结论统一在右侧输出。
- “专注报告”可见文案已移除，保留原型式图标按钮。
- 卡片历史 / 可访问数据改为工作区右侧滑入式浮层。
- React 项目开始使用原型 assets，路径为 `client/public/assets/`。

## 当前新增/修改文件

- `.gitignore`
- `server/requirements.txt`
- `server/README.md`
- `server/app/main.py`
- `server/app/api/routes.py`
- `server/app/mock/catalog.py`
- `server/app/mock/engine.py`
- `server/app/models/schemas.py`
- `server/app/storage.py`
- `client/package.json`
- `client/index.html`
- `client/src/main.jsx`
- `client/src/styles.css`
- `client/src/services/api.js`
- `client/public/assets/`

注意：`docs/ChatBI_PRD_草案.md` 在本轮开始时已处于 modified 状态，不要误认为都是本轮修改。

## 当前服务与验证

后端：

```bash
cd server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：

```bash
cd client
npm run dev -- --port 5173
```

访问：

- 前端：http://localhost:5173/
- 后端：http://localhost:8000/
- API 文档：http://localhost:8000/docs

已验证：

- `npm run build` 通过。
- 后端 Python 编译通过。
- 点击“诊断中东公司 GS8 车型本月的库存异常并给出建议”可以生成执行链、SQL、最终回答、风险卡、KPI、图表、表格和建议。
- 浏览器检查确认：有“最终回答”，没有“专注报告”，左侧标题为“问数审计工作台”。

最新截图：

- `docs/chatbi_v3_layout_fix_check.png`

## 下一步建议

1. 继续对照 `前端原型/index_v3_dynamic.html` 做像素级还原，优先修：
   - 左侧执行链卡片高度、间距和滚动条。
   - 右侧按钮图标与原型 FontAwesome 风格。
   - 卡片历史 / 可访问数据浮层定位与尺寸。
   - 头像尺寸与裁切。
2. 把原型中的 SQL 自愈演示流程完整迁移到 SSE mock 事件中。
3. 增加历史会话恢复时的右侧画布还原验证。
4. 后续真实 API 替换顺序建议：
   - 会话接口
   - mock SSE Agent 接口
   - Dify 知识库检索
   - MySQL 查询
   - Tavily MCP 搜索

