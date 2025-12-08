import json

src = "qa_software.ndjson"
dst = "qa_software_bulk.ndjson"
index_name = "amazon_qa_software"

with open(src, "r", encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        meta = {"index": {"_index": index_name}}
        fout.write(json.dumps(meta) + "\n")
        fout.write(line + "\n")

