import logging
import os
from typing import List

import gradio as gr
from opensearchpy import OpenSearch
from opensearchpy.exceptions import AuthenticationException
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ===== 1. Connect to OpenSearch =====
OPENSEARCH_USER = os.getenv("OPENSEARCH_USERNAME", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

if not OPENSEARCH_PASSWORD:
    raise RuntimeError(
        "OPENSEARCH_INITIAL_ADMIN_PASSWORD is not set. "
        "Please export it in your shell or define it in the .env file before running gradio_app.py."
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
        "Check that OPENSEARCH_INITIAL_ADMIN_PASSWORD (and OPENSEARCH_USERNAME if used) "
        "match the credentials configured in the cluster."
    ) from e

INDEX_NAME = "amazon_qa_software_vec"

# ===== 2. Load embedding model =====
logging.info("Loading SentenceTransformer model: sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
logging.info("Model loaded")


def search_qa(query: str, top_k: int = 10) -> List[list]:
    if not query.strip():
        return []

    q_vec = model.encode(query)
    body = {
        "size": top_k,
        "query": {
            "knn": {
                "question_vector": {
                    "vector": q_vec.tolist(),
                    "k": top_k,
                }
            }
        },
    }

    res = client.search(index=INDEX_NAME, body=body)
    rows: List[list] = []
    for hit in res["hits"]["hits"]:
        score = float(hit.get("_score", 0.0))
        source = hit.get("_source", {})
        q = source.get("question", "")
        a = source.get("answer", "")
        rows.append([
            round(score, 4),
            q,
            a,
        ])

    return rows


with gr.Blocks(title="Amazon QA Semantic Search (OpenSearch)") as demo:
    gr.Markdown("""# Amazon QA Semantic Search

Type a question and retrieve the most semantically similar Q&A pairs from OpenSearch.
""")

    with gr.Row():
        with gr.Column(scale=3):
            query_input = gr.Textbox(
                label="Your question",
                placeholder="Is that windows 8 good for gaming?",
            )
            topk_input = gr.Slider(
                minimum=1,
                maximum=50,
                value=20,
                step=1,
                label="Top K",
            )
            search_button = gr.Button("Search")

        with gr.Column(scale=4):
            results_output = gr.Dataframe(
                headers=["score", "question", "answer"],
                datatype=["number", "str", "str"],
                label="Results (Q&A)",
                wrap=True,
                interactive=False,
            )

    search_button.click(search_qa, inputs=[query_input, topk_input], outputs=results_output)

if __name__ == "__main__":
    demo.launch()
