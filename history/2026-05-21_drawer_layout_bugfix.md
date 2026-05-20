# ChatBI 历史对话列表布局修复 & GitHub 同步纪要

**日期：** 2026-05-21  
**版本：** v2.0.1-bugfix  
**状态：** ✅ 完成，零 Error，零 Warning

---

## 1. 问题描述

用户反馈：**侧边栏历史对话列表中所有会话项挤在一堆**，无法正常分行展示，列表也无法滚动。

---

## 2. 根因分析

经过审查，发现了两个相互叠加的 CSS 布局 Bug：

### Bug 1：`.drawerList` 缺少 flex 约束（主因）

`.historyDrawer` 是 `display: flex; flex-direction: column; height: 100%` 的纵向 Flex 容器，但其子项 `.drawerList` 只有：

```css
/* 修复前 */
.drawerList { display: grid; gap: 8px; overflow-y: auto; padding: 0 12px 12px; }
```

没有 `flex: 1` 和 `min-height: 0`，导致：
- `.drawerList` 不受父容器高度约束，会尝试展开至内容完整高度
- `overflow-y: auto` 因此永远不会触发（内容高度 <= 容器高度 永远不成立）
- 所有卡片在没有分配高度的 `display: grid` 中**全部堆叠压缩**

### Bug 2：`b` 标签内标题文本 `text-overflow: ellipsis` 失效（次因）

`b` 标签是 `display: flex`，内部文本节点是匿名 flex 子项，匿名子项不支持 `overflow: hidden` + `text-overflow: ellipsis`，导致超长标题撑开卡片宽度，进一步加剧布局混乱。

---

## 3. 修复方案

### 修复 `styles.css`：

**① 修复 `.drawerList`**：
```css
/* 修复后 */
.drawerList {
  display: flex;
  flex-direction: column;
  flex: 1;          /* 填满父容器剩余高度 */
  min-height: 0;    /* flex 子项可以收缩至内容以下，允许 overflow 生效 */
  gap: 8px;
  overflow-y: auto;
  padding: 0 12px 12px;
}
```

**② 修复 `.drawerItemContent b` 和新增 `.drawerItemTitle`**：
```css
/* b 标签只负责 flex 布局，不再设 overflow/ellipsis（对 flex 容器无效） */
.drawerItemContent b {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 0;   /* 允许 flex 子项收缩 */
}

/* 在具名 span 上设置截断，这才能正确生效 */
.drawerItemTitle {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

### 修复 `main.jsx`：

将 `{item.title}` 用 `<span className="drawerItemTitle">` 包裹，使 CSS 截断规则能够命中具名元素：

```jsx
<b>
  {item.pinned && <i className="fa-solid fa-thumbtack pin-badge" title="已置顶" />}
  <span className="drawerItemTitle">{item.title}</span>
</b>
```

---

## 4. 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `client/src/styles.css` | `.drawerList` 新增 `flex: 1; min-height: 0; display: flex; flex-direction: column` |
| `client/src/styles.css` | `.drawerItemContent b` 移除无效 overflow 声明，新增 `.drawerItemTitle` 截断规则 |
| `client/src/main.jsx` | `{item.title}` 改为 `<span className="drawerItemTitle">{item.title}</span>` |

---

## 5. 验收方式

打开 [http://localhost:5173/](http://localhost:5173/)，点击侧边栏历史图标，检查：
1. ✅ 所有历史会话项**正常分行排列**，不再挤成一堆
2. ✅ 历史数量超过可视区域时，列表区域**正常出现滚动条**
3. ✅ 超长的会话标题以 `...` 省略号截断，不会撑开卡片宽度

---

**ChatBI 研发组 · Advanced Agentic Coding**
