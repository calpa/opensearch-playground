from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer
import logging

# ===== 1. 連線到 OpenSearch =====
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "CHANGE_ME"

logging.info("Connecting to OpenSearch at localhost:9200 as user '%s'", OPENSEARCH_USER)
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "https"}],
    http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
    http_compress=True,
    use_ssl=True,
    verify_certs=False,  # OK for self-signed local dev
)
INDEX_NAME = "amazon_qa_software_vec"  # 替換成你實際的索引名稱

# ===== 2. 載入 embedding 模型 =====
# 注意：dimension 要跟你建立 knn_vector 時的 dimension 一致
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ===== 3. 準備查詢文字，轉成向量 =====
query_text = "Is that windows 8 good for gaming?"
q_vec = model.encode(query_text)  # numpy array

# ===== 4. 組 kNN 查詢 body =====
body = {
    "size": 20,
    "query": {
        "knn": {
            "question_vector": {
                "vector": q_vec.tolist(),
                "k": 20
            }
        }
    }
}

# ===== 5. 呼叫 OpenSearch 搜尋並打印結果 =====
res = client.search(index=INDEX_NAME, body=body)

print(f"Query: {query_text}")
print("=" * 80)
for hit in res["hits"]["hits"]:
    score = hit["_score"]
    source = hit["_source"]
    q = source.get("question", "")
    a = source.get("answer", "")
    print(f"score={score:.4f}")
    print(f"Q: {q}")
    print(f"A: {a}")
    print("-" * 80)
