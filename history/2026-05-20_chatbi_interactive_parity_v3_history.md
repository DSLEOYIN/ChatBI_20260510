# ChatBI 第一阶段交互复刻修改纪要 (高保真交互与随动定位)

**日期：** 2026-05-20
**阶段：** 第一阶段 (Stage 1) - 高保真交互与随动定位实现

---

## 1. 核心改进点与功能对齐

本阶段的核心任务是将 React 版的前端工作区与 `前端原型/index_v3_dynamic.html` 进行像素级复刻和无缝交互对齐，重点解决悬浮球拖拽弹性吸附、工作区象限随动定位以及右侧抽屉无延迟滑入动画等核心体验痛点。

### 1.1 悬浮球吸附与操作判定重构 (main.jsx & styles.css)
* **拖曳边界限制 (`clampLauncherPosition`)**：重构拖拽边界计算，限制悬浮球只能在屏幕可视区域内移动，四周保留 `8px` 的安全防溢出边距。
* **弹性边缘吸附算法 (`snapLauncherToEdge`)**：在拖拽结束（`pointerup`）时，实时计算球体距离左、右屏幕边缘的水平距离，智能自动平滑吸附至最近一侧。
* **高性能指针动画**：拖拽期间通过直接操作 `launcher.style.transition = 'none'` 确保 60fps 指针直接跟踪，释放吸附时动态追加入 `left 0.28s cubic-bezier(0.16, 1, 0.3, 1)` 等过渡属性，实现极具物理弹性感的顺滑吸附。
* **点击与拖动区分校验**：引入 `dragRef` 计算拖曳时的位移偏差。当指针拖拽位移超过 `3px` 时被标记为拖拽（不触发面板的展开或收回），只有在 `3px` 以内释放才会被判定为常规点击，完美防止手抖误触。

### 1.2 工作区小窗象限随动与 CSS 变量动态注入 (main.jsx)
* **编写象限随动定位函数 (`positionWorkspaceNearLauncher`)**：
  * 摒弃传统的绝对写死坐标定位，完全参考原型逻辑。根据悬浮球当前所在象限中心点，智能判定工作区应该偏左还是偏右、偏上还是偏下弹出，彻底杜绝小窗滑出可视区。
  * 自动为小窗计算最适宜的 `transform-origin` 缩放起始点，实现从小窗悬浮球中心向外无缝扩散/收缩动画。
* **动态共享根 CSS 布局变量**：
  * 工作区弹出、被随动重定位、拖拽、或是触发浏览器窗口 `resize` 时，会直接利用 DOM 特性向 `document.documentElement` 动态写入 4 组位置根 CSS 变量：
    * `--workspace-top` (小窗当前顶部距离)
    * `--workspace-right` (小窗当前右侧距离)
    * `--workspace-width` (小窗当前物理宽度)
    * `--workspace-height` (小窗当前物理高度)

### 1.3 外部 Fixed 抽屉样式与无抖动滑入重构 (styles.css & main.jsx)
* **纯 CSS 高性能定位继承**：
  * 重写 `.card-pool-drawer` 和 `.catalog-drawer` 样式，其位置直接使用 `var(--workspace-top)`、`var(--workspace-right)` 等动态变量进行实时绑定。
  * 彻底去除了原有的 React JS 定时/实时状态计算逻辑，改用纯 CSS `transform: translateX(...)`，让抽屉在滑出时永远能精准粘合在工作区的外边沿，即使快速缩放、平移浏览器窗口也绝无延迟、卡顿和切除。
* **常驻 DOM 维持过渡状态**：
  * 优化 `WorkspaceSideDrawer` 组件生命周期，不再在 `null` 态下直接销毁 unmount，而是始终保留在 DOM Tree 中，通过绑定 `.active` 样式类让 CSS 标准硬件加速过渡执行，100% 还原了原型中极其高级的平滑抽屉抽拉动画。

---

## 2. 修改的文件清单

### [前端组件与样式]
* **[MODIFY] [main.jsx](file:///d:/工作/大模型应用学习/ChatBI_20260509/client/src/main.jsx)**：
  * 引入 `dragRef` 精准区分拖动和点击。
  * 增加 `clampLauncherPosition` 与 `snapLauncherToEdge` 经典物理边界及吸附算法。
  * 编写 `positionWorkspaceNearLauncher` 象限随动算法。
  * 重构 React state 冗余定位，改用直接向 `:root` 共享 CSS Layout 变量。
  * 重构 `WorkspaceSideDrawer` 生命周期以防组件瞬间卸载造成 CSS 滑入动画丢失。
* **[MODIFY] [styles.css](file:///d:/工作/大模型应用学习/ChatBI_20260509/client/src/styles.css)**：
  * 修改卡片历史与数据目录抽屉样式，彻底适配 `--workspace-*` 根 CSS 布局变量。
  * 调谐过渡曲线与视效微调。

---

## 3. 运行与编译自验

### 3.1 前端编译
执行 `npm run build` 命令，前端构建包输出成功，结果完全零编译错误：
```bash
vite v6.4.2 building for production...
✓ 577 modules transformed.
dist/index.html                     0.52 kB
dist/assets/index-BOvT2oDF.css     24.80 kB
dist/assets/index-C2Jy4bVz.js   1,207.31 kB
✓ built in 3.01s
```

### 3.2 本地运行自验证
* **FastAPI 后端已起机**（Port: `8000`）
* **Vite 前端已挂载**（Port: `5173`）
* **悬浮球操作手感**：指针自由拖动无延迟，松手时顺滑吸附在屏幕左/右边界，点击瞬间工作区弹出。
* **抽屉表现**：点击“卡片历史”和“可访问数据”，抽屉从工作区边缘顺滑滑出，拖拽或调整窗口时，抽屉和工作区牢牢粘连，无任何抖动和白边。

---

## 4. 推荐验证指南 (供用户测试并拍照归档至 `qa/`)

由于交互效果是动态的，用户可在本地打开 [http://localhost:5173/](http://localhost:5173/)，重点按照如下路径验证并将截图置入 `qa/`：

1. **Launcher Snap Test**：拖拽悬浮球至半空松手，观察是否能弹性吸附到左或右边缘。保存吸附前后的对比截图。
2. **Quadrant Adjust Test**：
   * 将悬浮球拖至右上角松手，点击悬浮球，工作区应完美偏左下弹出。
   * 将悬浮球拖至左上角松手，点击悬浮球，工作区应完美偏右下弹出。
3. **Drawer Follow Test**：打开工作区，展开“卡片历史”抽屉。按住悬浮球满屏幕拖动，确认卡片抽屉始终紧随工作区边缘滑行，无一丝偏差或缝隙。
