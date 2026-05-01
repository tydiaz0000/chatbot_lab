from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests, json, time, psycopg2

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://ollama:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:3b-instruct"

DB = {
    "host": "postgres",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}

with open("knowledge_base.json", "r", encoding="utf-8") as f:
    KB = json.load(f)


def conn():
    return psycopg2.connect(**DB)


def est_tokens(txt):
    return max(1, len(txt)//4)


def retrieve(query, top_k=2):
    q = query.lower()
    rows = []

    for c in KB:
        score = sum(1 for w in q.split() if w in c["content"].lower())
        rows.append((score, c))

    rows.sort(reverse=True, key=lambda x:x[0])
    rows = rows[:top_k]

    return "\n\n".join(
        f"{x[1]['title']}: {x[1]['content']}" for x in rows
    )


def save_log(data):
    cn = conn()
    cur = cn.cursor()

    cur.execute("""
    INSERT INTO benchmark_logs (
        message, reply, model, rag, top_k,
        time_taken, prompt_tokens, output_tokens,
        tokens_per_sec, context_chars, context_tokens
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["message"],
        data["reply"],
        data["model"],
        data["rag"],
        data["top_k"],
        data["time_taken"],
        data["prompt_tokens"],
        data["output_tokens"],
        data["tokens_per_sec"],
        data["context_chars"],
        data["context_tokens"]
    ))

    cn.commit()
    cur.close()
    cn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    body = request.json

    msg = body["message"]
    rag = body["rag"]
    top_k = int(body["top_k"])
    model = body["model"]

    context = ""

    if rag:
        context = retrieve(msg, top_k)
        prompt = f"""
Use only this context:

{context}

Question:
{msg}
"""
    else:
        prompt = msg

    start = time.time()

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m"
        },
        timeout=180
    )

    end = time.time()

    data = r.json()

    reply = data.get("response","")
    duration = round(end-start,3)

    prompt_tokens = data.get("prompt_eval_count", est_tokens(prompt))
    output_tokens = data.get("eval_count", est_tokens(reply))

    result = {
        "message": msg,
        "reply": reply,
        "model": model,
        "rag": rag,
        "top_k": top_k,
        "time_taken": duration,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "tokens_per_sec": round(output_tokens/duration,2),
        "context_chars": len(context),
        "context_tokens": est_tokens(context)
    }

    save_log(result)

    return jsonify(result)


@app.route("/history")
def history():
    cn = conn()
    cur = cn.cursor()

    cur.execute("""
    SELECT id, created_at, model, rag, top_k,
           time_taken, prompt_tokens,
           output_tokens, tokens_per_sec
    FROM benchmark_logs
    ORDER BY id DESC
    LIMIT 50
    """)

    rows = cur.fetchall()

    cur.close()
    cn.close()

    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)