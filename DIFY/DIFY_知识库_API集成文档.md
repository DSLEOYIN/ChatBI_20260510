# Dify 知识库 API 深度集成与开发指南

本文档经过多次测试与严格校验，专为后续在应用中全面集成 Dify 知识库检索能力而编写。文档详细拆解了检索策略（纯语义、纯关键词、混合检索）、检索参数（TopK、权重比例、分数阈值）以及 Rerank 重排机制，确保您的应用能够 1:1 还原 Dify 官方界面的检索能力。

> [!IMPORTANT]
> **API 端口与鉴权关键提示**
> 1. **端口必填**：服务器 API 通信端口必须使用 `9879`（`http://10.30.11.215:9879`），切勿使用默认的 `80` 端口，否则会导致 Timeout。
> 2. **全局 Header**：所有请求必须携带 `Authorization: Bearer dataset-S5L6smkj8ovnSz8rMl5DZUvj` 以及 `Content-Type: application/json`。

---

## 1. 知识库映射字典 (Dataset IDs)

在集成应用时，请将用户选择的知识库映射为以下系统 ID：

| 知识库名称 | Dataset ID | 说明 |
| :--- | :--- | :--- |
| **车型知识库** | `9e07fcf2-56cf-4f2c-b115-8727e721fbd3` | 包含车型相关文档 |
| **国际-大区知识库** | `486476a8-15f6-4359-bcb5-6efd40d90373` | 国际大区数据 |
| **国际-国家知识库** | `90560d64-db69-4c66-88ca-9c86a340dd5d` | 国家级数据 |
| **国际问答对-V3** | `ffa84ba6-4ec9-44a0-8f6d-594b27f7a829` | 当前默认测试的高质量问答库 |
| **同环比-国际问答对-V2** | `959f346f-f950-480c-a1d7-d792ad10be33` | 历史版本数据 |

---

## 2. 核心功能：检索片段 (Retrieve API)

要在您的应用中集成类似 Dify 的召回测试器，此 API 是绝对的核心。

- **Endpoint**: `/v1/datasets/{dataset_id}/retrieve`
- **Method**: `POST`

### 2.1 检索参数全量字典 (`retrieval_model` 对象)

在构造 Payload 时，`retrieval_model` 是控制所有检索特性的对象。以下是您在应用中需要绑定的全部字段：

| 字段名 | 类型 | 说明 | 应用集成建议 |
| :--- | :--- | :--- | :--- |
| `search_method` | String | 检索策略。可选值：`semantic_search` (语义), `keyword_search` (全文), `hybrid_search` (混合)。 | 对应应用 UI 的下拉单选框。 |
| `top_k` | Integer | 召回结果的最大数量（如 1~20）。 | 对应应用 UI 的数字滑块。 |
| `score_threshold_enabled` | Boolean | **必填！** 是否开启分数过滤。即使不开启，也必须显式传 `false`，否则 API 会报 HTTP 500 错。 | 对应应用 UI 的开关 (Switch)。 |
| `score_threshold` | Float | 阈值分数（如 0.5）。仅在 `score_threshold_enabled` 为 `true` 时有效并需要传入。 | 对应阈值滑块，开启开关后显示。 |
| `reranking_enable` | Boolean | 是否开启外接 Rerank 大模型重排。 | 对应应用 UI 的开关 (Switch)。 |
| `reranking_model` | Object | 当 `reranking_enable=true` 时**必须传入**的 Rerank 模型配置。 | 详见下方 [场景三]。 |
| `weights` | Object | 当 `search_method="hybrid_search"` 且未开启 Rerank 时，用于配置语义和关键词的权重。 | 详见下方 [场景二]。 |

---

### 2.2 应用集成实战：三大核心场景 Payload

#### 场景一：纯语义 / 纯关键词检索
最基础的检索方式，只需设置策略名称和基础参数。

```json
{
    "query": "用户输入的检索词",
    "retrieval_model": {
        "search_method": "semantic_search",  // 或者 "keyword_search"
        "top_k": 3,
        "score_threshold_enabled": true,     // 开启阈值过滤
        "score_threshold": 0.5,              // 过滤掉低于 0.5 分的片段
        "reranking_enable": false
    }
}
```

#### 场景二：混合检索 + 权重分配 (Weight Settings)
用户在应用中拖动比例滑块（如 70% 语义，30% 关键词）时，触发此 Payload。

```json
{
    "query": "用户输入的检索词",
    "retrieval_model": {
        "search_method": "hybrid_search",
        "top_k": 3,
        "score_threshold_enabled": false,
        "reranking_enable": false,
        "weights": {
            "weight_type": "customized",  // 必须固定为 customized
            "vector_setting": {
                "vector_weight": 0.7,     // 语义权重（浮点数）
                "embedding_provider_name": "langgenius/siliconflow/siliconflow", 
                "embedding_model_name": "BAAI/bge-large-zh-v1.5"
            },
            "keyword_setting": {
                "keyword_weight": 0.3     // 关键词权重（必须与语义权重相加为 1.0）
            }
        }
    }
}
```

> [!WARNING]
> **API 原始分与 UI 混合分的视觉差异（必读）**
> 在上述权重模式下，您的应用如果直接读取 API 返回的 `score`，会发现它（如 `0.555`）与 Dify 官方后台显示的混合分（如 `0.46`）不一致。
> - **原因**：Dify 对外开放的 `/v1/` API 采用的是“排序生效，但返回原始向量分”的逻辑。虽然底层确实用 0.7/0.3 排序了，但吐出来的 JSON 中 `score` 字段依然是向量库里的原始相似度。
> - **应用侧处理**：在您的应用前端，如果您不需要向用户展示精准的重排分数，直接展示排名结果即可；如果您想让分数完全等于 `0.46`，请务必使用下方的 **Rerank 模式**。

#### 场景三：混合检索 + Rerank 大模型重排 (强烈推荐)
这是效果最好、分数最精确的模式。系统先分别召回，再交由神经大模型进行语义级别的重新打分。

```json
{
    "query": "用户输入的检索词",
    "retrieval_model": {
        "search_method": "hybrid_search",
        "top_k": 3,
        "score_threshold_enabled": false,
        "reranking_enable": true,            // 必须为 true
        "reranking_model": {                 // 必须提供模型确切的提供商和名字
            "reranking_provider_name": "langgenius/siliconflow/siliconflow",
            "reranking_model_name": "netease-youdao/bce-reranker-base_v1"
        }
    }
}
```

> [!CAUTION]
> **静默降级陷阱**
> 在应用代码中，如果您的 `reranking_enable` 传了 `true`，但却漏传了 `reranking_model` 对象（或者里面的名字写错了），Dify 的 API **绝不会报错**，而是会默默将你的检索**降级为默认的加权机制**。这就导致开发中常出现“我明明开了 Rerank，怎么分数还是老样子”的错觉。

---

## 3. 文档管理 API 附录

在应用中如果需要集成文档列表和文本快速上传功能，请参考以下 Endpoint。

### 3.1 获取文档列表
- **Endpoint**: `GET /v1/datasets/{dataset_id}/documents`
- **Params**:
  - `page`: 默认 1
  - `limit`: 默认 20

### 3.2 纯文本快速入库
- **Endpoint**: `POST /v1/datasets/{dataset_id}/document/create-by-text`
- **Payload**:
```json
{
  "name": "这里传给文档起的标题",
  "text": "这里传需要在应用里切分入库的完整长文本内容",
  "indexing_technique": "high_quality", 
  "process_rule": {
    "mode": "automatic"
  }
}
```
*注：此接口非常适合在应用中做“快速备忘录入库”或“聊天记录归档到知识库”的功能。*
