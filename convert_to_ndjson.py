import ast
import json

src = "qa_Software.json"          # 原始檔
dst = "qa_software.ndjson"       # 轉成 NDJSON

with open(src, "r", encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        # 把單引號 dict 轉成真正的 Python dict
        obj = ast.literal_eval(line)
        # 只保留你要的欄位，也可以在這裡改欄位名稱
        doc = {
            "asin": obj.get("asin"),
            "question": obj.get("question"),
            "answer": obj.get("answer"),
            "questionType": obj.get("questionType"),
            "answerType": obj.get("answerType"),
            "answerTime": obj.get("answerTime"),
            "unixTime": obj.get("unixTime"),
        }
        fout.write(json.dumps(doc, ensure_ascii=False) + "\n")

