import streamlit as st
import requests
import json

st.set_page_config(page_title="Dify Knowledge Base Tester", page_icon="🤖", layout="wide")

# Configuration
API_KEY = "dataset-S5L6smkj8ovnSz8rMl5DZUvj"
BASE_URL = "http://10.30.11.215:9879/v1/datasets/{dataset_id}"

DATASETS = {
    "车型知识库": "9e07fcf2-56cf-4f2c-b115-8727e721fbd3",
    "国际-大区知识库": "486476a8-15f6-4359-bcb5-6efd40d90373",
    "国际-国家知识库": "90560d64-db69-4c66-88ca-9c86a340dd5d",
    "国际问答对-V3": "ffa84ba6-4ec9-44a0-8f6d-594b27f7a829",
    "同环比-国际问答对-V2": "959f346f-f950-480c-a1d7-d792ad10be33"
}

st.title("Dify 知识库 API 测试工具 🛠️")
st.markdown("通过此工具，您可以测试配置文件中的多个知识库 API。")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ 配置")
    selected_kb_name = st.selectbox("选择知识库", list(DATASETS.keys()))
    dataset_id = DATASETS[selected_kb_name]
    
    st.text_input("Dataset ID", value=dataset_id, disabled=True)
    
    # Custom Headers
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

# Main Panel
tab1, tab2, tab3 = st.tabs(["📄 获取文档列表 (GET)", "📝 创建文本片段 (POST)", "🔍 检索片段 (POST)"])

# --- Tab 1: List Documents ---
with tab1:
    st.subheader("获取文档列表")
    st.markdown("此操作将调用 `GET /documents` 获取当前数据集下的文档。")
    page = st.number_input("页码 (Page)", min_value=1, value=1)
    limit = st.number_input("每页数量 (Limit)", min_value=1, max_value=100, value=20)
    
    if st.button("获取文档", key="get_docs"):
        url = f"{BASE_URL.format(dataset_id=dataset_id)}/documents"
        params = {"page": page, "limit": limit}
        
        with st.spinner("请求中..."):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                st.write(f"**Status Code:** {response.status_code}")
                st.json(response.json())
            except Exception as e:
                st.error(f"请求失败: {e}")

# --- Tab 2: Create Document ---
with tab2:
    st.subheader("创建文本片段")
    st.markdown("此操作将调用 `POST /document/create-by-text` 向知识库中添加文本内容。")
    
    doc_name = st.text_input("文档名称", value="测试文档")
    doc_text = st.text_area("文档内容", value="这是一段测试文本，用于验证 Dify 知识库 API。")
    idx_tech = st.selectbox("索引技术 (indexing_technique)", ["high_quality", "economy"])
    process_mode = st.selectbox("处理模式 (process_rule.mode)", ["automatic", "custom"])
    
    if st.button("创建文档", key="create_doc"):
        url = f"{BASE_URL.format(dataset_id=dataset_id)}/document/create-by-text"
        
        payload = {
            "name": doc_name,
            "text": doc_text,
            "indexing_technique": idx_tech,
            "process_rule": {
                "mode": process_mode
            }
        }
        
        with st.spinner("请求中..."):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                st.write(f"**Status Code:** {response.status_code}")
                st.json(response.json())
            except Exception as e:
                st.error(f"请求失败: {e}")

# --- Tab 3: Retrieve Chunks (Optional/Experimental) ---
with tab3:
    st.subheader("检索片段 (Retrieve)")
    st.markdown("调用 `POST /retrieve` 检索相关片段。注意：这要求知识库的检索 API 对外开放。")
    
    query_text = st.text_input("检索关键词", value="测试")
    
    st.markdown("##### 检索设置")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            retrieval_model = st.selectbox("检索策略 (Search Method)", ["hybrid_search", "semantic_search", "keyword_search"])
            top_k = st.slider("Top K", min_value=1, max_value=20, value=3)
            
            # Show weight slider only if hybrid search is selected
            if retrieval_model == "hybrid_search":
                semantic_weight = st.slider("语义权重 (Semantic Weight)", min_value=0.0, max_value=1.0, value=0.7, step=0.01)
                st.caption(f"关键词权重将自动设为: {1.0 - semantic_weight:.2f}")
            else:
                semantic_weight = 0.7 # fallback, not used
                
        with col2:
            reranking_enable = st.checkbox("开启 Rerank 模型 (Reranking Enable)", value=False)
            if reranking_enable:
                # Dify API requires explicit provider and model name if reranking is enabled
                st.info("注意：通过 API 调用 Rerank 时，必须指定对应的模型名称和提供商，否则可能会被降级为普通的权重计算。")
                rerank_provider = st.text_input("Rerank Provider (如: xinference, cohere)", value="")
                rerank_model = st.text_input("Rerank Model Name (如: bge-reranker-large)", value="")
            else:
                rerank_provider = ""
                rerank_model = ""
                
            score_threshold_enabled = st.checkbox("开启 Score 阈值", value=False)
            score_threshold = st.slider("Score 阈值 (Score Threshold)", min_value=0.0, max_value=1.0, value=0.5, step=0.01, disabled=not score_threshold_enabled)

    if st.button("检索", key="retrieve"):
        url = f"{BASE_URL.format(dataset_id=dataset_id)}/retrieve"
        
        payload = {
            "query": query_text,
            "retrieval_model": {
                "search_method": retrieval_model,
                "reranking_enable": reranking_enable,
                "top_k": top_k,
                "score_threshold_enabled": score_threshold_enabled
            }
        }
        
        if score_threshold_enabled:
            payload["retrieval_model"]["score_threshold"] = score_threshold
            
        if reranking_enable and rerank_provider and rerank_model:
            payload["retrieval_model"]["reranking_model"] = {
                "reranking_provider_name": rerank_provider,
                "reranking_model_name": rerank_model
            }
            
        if retrieval_model == "hybrid_search":
            payload["retrieval_model"]["weights"] = {
                "weight_type": "customized",
                "vector_setting": {
                    "vector_weight": semantic_weight,
                    "embedding_provider_name": "", # API often ignores this or uses dataset default
                    "embedding_model_name": ""
                },
                "keyword_setting": {
                    "keyword_weight": round(1.0 - semantic_weight, 2)
                }
            }

        with st.spinner("请求中..."):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                st.write(f"**Status Code:** {response.status_code}")
                
                data = response.json()
                if "records" in data:
                    records = data["records"]
                    st.markdown(f"#### {len(records)} 个召回段落")
                    
                    for i, record in enumerate(records):
                        segment = record.get("segment", {})
                        content = segment.get("content", "无内容")
                        
                        # Handle potential missing document data gracefully
                        doc_info = segment.get("document")
                        if isinstance(doc_info, dict):
                            doc_name = doc_info.get("name", "未知文档")
                        else:
                            doc_name = "未知文档"
                            
                        score = record.get("score", 0.0)
                        
                        # Safely escape content to avoid HTML rendering issues
                        content_safe = content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: #fafafa; position: relative;">
                            <div style="position: absolute; right: 16px; top: 16px; background-color: #eaf2ff; color: #1677ff; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; border: 1px solid #1677ff40;">
                                score: {score:.3f}
                            </div>
                            <div style="color: #999; font-size: 13px; margin-bottom: 8px;"># Chunk {i+1}</div>
                            <div style="font-size: 14px; margin-bottom: 16px; line-height: 1.6; color: #333;">{content_safe}</div>
                            <div style="color: #666; font-size: 13px; border-top: 1px dashed #ddd; padding-top: 8px; display: flex; align-items: center; gap: 6px;">
                                📄 {doc_name}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # 还可以提供一个可展开的原始 JSON 以备查错
                    with st.expander("查看原始 JSON"):
                        st.json(data)
                else:
                    st.warning("返回结果中没有 'records' 字段，可能未召回任何内容或 API 结构不一致。")
                    st.json(data)
            except Exception as e:
                st.error(f"请求失败: {e}")
