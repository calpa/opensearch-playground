# Amazon QA + OpenSearch + Embeddings (Local RAG Skeleton)

This repo is a small end‑to‑end playground that shows how to:

- Ingest the **Amazon Question/Answer dataset (Software category)** into OpenSearch
- Build a **vector index** with sentence embeddings
- Run **semantic kNN search** over questions and answers

It is based on the public dataset from UCSD:

> https://cseweb.ucsd.edu/~jmcauley/datasets/amazon/qa/

The goal is that a future reader (or AI assistant) can understand, from this README alone, how data flows through the project and how to reproduce the pipeline.

---

## 1. Dataset

- **Source:** Amazon QA dataset, Software category
  - File used here: `qa_Software.json`
  - Download page: https://cseweb.ucsd.edu/~jmcauley/datasets/amazon/qa/
- **Format:**
  - The original file is **one Python dict per line**, using single quotes.
  - This is **not valid JSON** and cannot be ingested directly into OpenSearch.

Typical raw fields per item include:

- `asin`
- `question`
- `answer`
- `questionType`
- `answerType`
- `answerTime`
- `unixTime`

We first convert it to valid **NDJSON** (one JSON object per line), then to **OpenSearch bulk format**.

Project files related to the dataset:

- `qa_Software.json` – raw file from UCSD
- `qa_software.ndjson` – cleaned NDJSON
- `qa_software_bulk.ndjson` – NDJSON in OpenSearch bulk format

---

## 2. Data Preparation

### 2.1 Convert raw file → NDJSON

- **Script:** `convert_to_ndjson.py`
- **Input:** `qa_Software.json` (Python dict per line, single quotes)
- **Output:** `qa_software.ndjson` (valid JSON object per line)

High‑level behavior:

- Reads each line from `qa_Software.json`
- Safely parses it and rewrites it as a proper JSON object
- Writes one JSON object per line to `qa_software.ndjson`

### 2.2 NDJSON → OpenSearch bulk NDJSON

- **Script:** `convert_to_bulk.py`
- **Input:** `qa_software.ndjson`
- **Output:** `qa_software_bulk.ndjson` (OpenSearch bulk format)

The bulk file alternates action lines and document lines, e.g.:

```text
{ "index": { "_index": "amazon_qa_software" } }
{ ... document 1 ... }
{ "index": { "_index": "amazon_qa_software" } }
{ ... document 2 ... }
...
```

This is the format consumed by the `_bulk` API.

---

## 3. Local OpenSearch Setup

This project assumes a **local OpenSearch cluster** (with security enabled) and OpenSearch Dashboards, typically via Docker Compose.

- **Config file:** `docker-compose.yml`
- **Services (typical):**
  - `opensearch-node1`, `opensearch-node2`
  - `opensearch-dashboards` (UI on port 5601)
- **Cluster access:**
  - OpenSearch: `https://localhost:9200`
  - Dashboards: `https://localhost:5601` (depending on compose settings)
- **Auth (local dev):**
  - Username: `admin`
  - Password: configured via environment variables.

### 3.1 Admin password via `.env`

The Docker demo expects the **initial admin password** to be provided via a `.env` file that is loaded by `docker-compose.yml`.

- **Location:** create a `.env` file in the **same directory** as `docker-compose.yml`.
- **Content:** add at least the following line:

  ```bash
  OPENSEARCH_INITIAL_ADMIN_PASSWORD=YourStrongPassw0rd!
  ```

The value of `OPENSEARCH_INITIAL_ADMIN_PASSWORD` must follow OpenSearch's password policy, e.g. **at least 8 characters**, including **uppercase**, **lowercase**, **digits**, and **special characters**.

> Note: The Python client in this repo connects to `https://localhost:9200` with `verify_certs=False` for local, self‑signed TLS. This is fine for a playground but should not be used in production.

---

## 4. Create Index and Ingest Documents

### 4.1 Create the base index `amazon_qa_software`

Use OpenSearch Dashboards → **Dev Tools** (or via `curl`) to create the base index for raw QA documents:

```json
PUT amazon_qa_software
{
  "settings": {
    "index": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    }
  },
  "mappings": {
    "properties": {
      "asin":         { "type": "keyword" },
      "question":     { "type": "text"    },
      "answer":       { "type": "text"    },
      "questionType": { "type": "keyword" },
      "answerType":   { "type": "keyword" },
      "answerTime":   { "type": "keyword" },
      "unixTime":     { "type": "date", "format": "epoch_second" }
    }
  }
}
```

### 4.2 Bulk ingest the QA documents

From the project root, after `qa_software_bulk.ndjson` has been generated:

```bash
# If security + HTTPS is enabled (typical for this repo)
curl -k -u admin:'YOUR_PASSWORD' \
  -H "Content-Type: application/x-ndjson" \
  -X POST "https://localhost:9200/_bulk?pretty" \
  --data-binary "@qa_software_bulk.ndjson"
```

Verify that documents exist:

```json
GET amazon_qa_software/_search
{
  "size": 3,
  "query": { "match_all": {} }
}
```

Response:

```json
{
  "took": 287,
  "timed_out": false,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 10000,
      "relation": "gte"
    },
    "max_score": 1,
    "hits": [
      {
        "_index": "amazon_qa_software",
        "_id": "YEm6AJsB1kJWL1OHtx9w",
        "_score": 1,
        "_source": {
          "asin": "0439381673",
          "question": "I have Windows 8, Will this work on my computer?",
          "answer": "Yes",
          "questionType": "yes/no",
          "answerType": "Y",
          "answerTime": "Aug 11, 2013",
          "unixTime": 1376204400
        }
      },
      {
        "_index": "amazon_qa_software",
        "_id": "YUm6AJsB1kJWL1OHtx9w",
        "_score": 1,
        "_source": {
          "asin": "0439381673",
          "question": "what is it about?",
          "answer": "Kinda like the way they did with the Wagon trains going west..you have to buy food and choose your people etc..it's a fun game and has been around for years. My grown kids played the first games, then newer came along with grandkids playing...It's a fun game for the whole family to enjoy..so saddle up and try it out..if you like the Old West. Look out for the rivers and such...........Good Luck",
          "questionType": "open-ended",
          "answerType": null,
          "answerTime": "Oct 19, 2014",
          "unixTime": 1413702000
        }
      },
      {
        "_index": "amazon_qa_software",
        "_id": "Ykm6AJsB1kJWL1OHtx9w",
        "_score": 1,
        "_source": {
          "asin": "0439381673",
          "question": "It says above platform Mac, but I see in the questions that it does not for Mac Book Pro. What about regular Mac desktop??",
          "answer": "I used it with a pc. So, I have no idea. I hope it works for you. I really liked this as did the children in my class. We made it all the way to Ft. Vancouver.",
          "questionType": "open-ended",
          "answerType": null,
          "answerTime": "Aug 11, 2014",
          "unixTime": 1407740400
        }
      }
    ]
  }
}
```

---

## 5. Vector Index and Embeddings

To enable **semantic search**, we create a **separate index** that stores a text copy plus a `knn_vector` embedding.

- **Source index:** `amazon_qa_software`
- **Vector index:** `amazon_qa_software_vec`
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`
  - Output dimension: **384**

### 5.1 Create the vector index

In Dev Tools:

```json
PUT amazon_qa_software_vec
{
  "settings": {
    "index": {
      "knn": true
    }
  },
  "mappings": {
    "properties": {
      "asin":     { "type": "keyword" },
      "question": { "type": "text"    },
      "answer":   { "type": "text"    },
      "question_vector": {
        "type": "knn_vector",
        "dimension": 384
      }
    }
  }
}
```

In this project, the `question_vector` embedding is computed from the **concatenation of the question and answer text**:

- `text_for_embedding = question + " " + answer`

This means each vector captures both the **user question** and the corresponding **answer content** when performing semantic search.

### 5.2 Populate the vector index (Python)

- **Script:** `build_index.py`
- **Behavior (high level):**

  1. Connects to OpenSearch (`https://localhost:9200`, basic auth as `admin`).
  2. Loads the `all-MiniLM-L6-v2` SentenceTransformer model.
  3. Scrolls through all docs in `amazon_qa_software`.
  4. For each doc:
     - Takes the `question` field.
     - Encodes it to a 384‑dim vector.
     - Writes a new document into `amazon_qa_software_vec` with:
       - `asin`
       - `question`
       - `answer`
       - `question_vector` (embedding as list of floats)
  5. Uses `helpers.bulk` to index documents efficiently.
  6. Logs progress with the standard `logging` module.

- **Auth & SSL:**

  - Uses username/password for the local secured cluster.
  - Uses `scheme="https"`, `use_ssl=True`, `verify_certs=False` for local development.

- **How to run (with venv):**

  ```bash
  # From the project root (this repository)
  # Activate existing virtualenv (already created as .venv)
  source .venv/bin/activate

  # Load environment variables from .env (including OPENSEARCH_INITIAL_ADMIN_PASSWORD)
  export $(grep -v '^#' .env | xargs)

  # Or call the venv python directly
  ./.venv/bin/python build_index.py
  ```

You should see logs like:

- Connection to OpenSearch
- Model loading
- `Encoded N documents` every 100 items
- Bulk indexing summary at the end

---

## 6. Semantic kNN Query Example (`ask.py`)

Once `amazon_qa_software_vec` is populated, you can run semantic search queries from Python.

- **Script:** `ask.py`
- **What it does:**
  1. Connects to the same secured OpenSearch cluster.
  2. Loads `all-MiniLM-L6-v2` again.
  3. Encodes a natural language question into a vector.
  4. Runs a **kNN query** against `question_vector` in `amazon_qa_software_vec`.
  5. Prints the top‑K semantically similar questions and answers with their scores.

Core logic (conceptual):

```python
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "https"}],
    http_auth=("admin", "YOUR_PASSWORD"),
    http_compress=True,
    use_ssl=True,
    verify_certs=False,  # local, self-signed
)

INDEX_NAME = "amazon_qa_software_vec"
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

query_text = "Is that windows 8 good for gaming?"  # example
q_vec = model.encode(query_text)

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

res = client.search(index=INDEX_NAME, body=body)
```

The script then iterates over `res["hits"]["hits"]` and prints `score`, `question`, and `answer` for each hit. This is the basic **semantic search** behavior for later RAG.

Run it with:

```bash
# From the project root
./.venv/bin/python ask.py
```

---

## 7. Virtual Environment & Dependencies

This project expects Python packages to be installed in a local virtual environment (PEP 668‑friendly, not system Python):

```bash
# From the project root
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install opensearch-py sentence-transformers
```

Notes:

- Python client: `opensearch-py`
- Embeddings: `sentence-transformers` (which pulls in `torch`, `transformers`, `scikit-learn`, `scipy`, etc.)
- The repo’s `.gitignore` already excludes `.venv/` and other generated files.

---

## 8. Security Notes

- The demo code connects to `https://localhost:9200` with:
  - Basic auth: `admin` + password
  - `verify_certs=False` to ignore TLS verification (self‑signed certs).
- **Do not** copy this configuration directly into production.
- For a real deployment, you should:
  - Store credentials in environment variables or a secret manager.
  - Enable certificate verification (`verify_certs=True`) and provide CA certs.
  - Lock down network access to OpenSearch.

---

## 9. Next Steps (RAG / LLM Integration)

With the vector index and semantic search in place, this repo is ready for:

- **RAG API:** Wrap the kNN query logic from `ask.py` into an HTTP service (e.g., FastAPI or Flask).
- **LLM Integration:** Call an LLM (OpenAI, DeepSeek, local model, etc.) with retrieved Q&A as context.
- **Chat Frontend:** Build a simple chat UI that takes user questions, performs kNN search on `amazon_qa_software_vec`, and uses an LLM to generate natural language answers.

This README is written so that a future AI assistant (or you) can reconstruct the whole pipeline:

1. Start OpenSearch via `docker-compose.yml`.
2. Prepare data (`convert_to_ndjson.py`, `convert_to_bulk.py`).
3. Create and populate `amazon_qa_software`.
4. Build vector index with `build_index.py`.
5. Run semantic queries with `ask.py`.
6. Explore results interactively with the Gradio app `gradio_app.py`.

From there, you can extend the project into a full local RAG system on top of the Amazon QA dataset.

---

## 10. Gradio UI (`gradio_app.py`)

This repo includes a small Gradio app that lets you type questions and see the top‑K most similar Q&A pairs from OpenSearch.

- **Script:** `gradio_app.py`
- **What it does:**
  - Connects to the same secured OpenSearch cluster using env vars.
  - Loads the `all-MiniLM-L6-v2` SentenceTransformer model.
  - Encodes your question to a vector.
  - Runs a kNN query on `question_vector` in `amazon_qa_software_vec`.
  - Displays the retrieved Q&A pairs and scores in a simple web UI.

### 10.1 How to run the Gradio app

```bash
# From the project root
source .venv/bin/activate

# Load environment variables from .env (including OPENSEARCH_INITIAL_ADMIN_PASSWORD)
export $(grep -v '^#' .env | xargs)

python gradio_app.py
```

Gradio will print a `Local URL` (and possibly a `Public URL`). Open the local URL in your browser, type a question (for example `Is that windows 8 good for gaming?`), and you should see the matching Q&A pairs and scores coming back from OpenSearch.
