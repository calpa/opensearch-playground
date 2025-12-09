import logging
import os
from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import AuthenticationException
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# 1. 連到 OpenSearch
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

if not OPENSEARCH_PASSWORD:
    raise RuntimeError(
        "OPENSEARCH_INITIAL_ADMIN_PASSWORD is not set. "
        "Please export it in your shell or define it in the .env file before running build_index.py."
    )

logging.info("Connecting to OpenSearch at localhost:9200 as user '%s'", OPENSEARCH_USER)
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "https"}],
    http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
    http_compress=True,
    use_ssl=True,
    verify_certs=False,  # OK for self-signed local dev
)

try:
    client.info()
    logging.info("Connected to OpenSearch and authentication succeeded")
except AuthenticationException as e:
    raise RuntimeError(
        "Failed to authenticate to OpenSearch. "
        "Check that OPENSEARCH_INITIAL_ADMIN_PASSWORD matches the admin password configured in the cluster."
    ) from e

# 2. 載入 embedding 模型
logging.info("Loading SentenceTransformer model: sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
logging.info("Model loaded")

src_index = "amazon_qa_software"
dst_index = "amazon_qa_software_vec"

# 3. scroll 讀舊索引
def gen_docs():
    logging.info("Starting scan on source index '%s'", src_index)
    page = helpers.scan(
        client,
        index=src_index,
        query={"query": {"match_all": {}}},
        size=500
    )
    count = 0
    for doc in page:
        source = doc["_source"]
        question = source.get("question", "") or ""
        answer = source.get("answer", "") or ""
        text = (question + " " + answer).strip()
        if not text:
            logging.debug("Document %s has empty question and answer fields, skipping embedding", doc.get("_id"))
            continue
        emb = model.encode(text, show_progress_bar=False)
        count += 1
        if count % 100 == 0:
            logging.info("Encoded %d documents", count)
        yield {
            "_index": dst_index,
            "_id": doc["_id"],
            "_source": {
                "asin": source.get("asin"),
                "question": question,
                "answer": answer,
                "question_vector": emb.tolist()
            }
        }
    logging.info("Finished generating documents, total: %d", count)

logging.info("Starting bulk indexing into '%s'", dst_index)
# 4. bulk 寫入新索引
success, errors = helpers.bulk(client, gen_docs(), stats_only=True)
logging.info("Bulk indexing finished: success=%s, errors=%s", success, errors)
