"""Ronda 1 del benchmark del enrutador: criba rápida de SLM locales con Ollama.

Uso (desde la raíz del repo, con ``ollama serve`` en marcha)::

    python -m modules.router.benchmark.criba_slm
    python -m modules.router.benchmark.criba_slm --models qwen3.5:4b gemma4:e2b

Pasa las mismas 20 preguntas a cada modelo (15 de las guías y 5 trampa que no
están en ellas), con los mismos fragmentos del RAG, y guarda en
``docs/benchmarks/enrutador/01-criba-slm/``:

- ``resultados.jsonl``: una fila por modelo y pregunta, con todo lo medido.
- ``respuestas.md``: las respuestas de todos los modelos, pregunta a pregunta,
  para leerlas y puntuarlas a mano.
- ``resumen.md``: tabla por modelo, la máquina y las versiones exactas.

Mide lo que se puede medir solo (español, formato, si se abstiene en las
trampas, velocidad, logprobs). Si una respuesta es correcta lo decide una
persona leyendo ``respuestas.md``. Solo usa la librería estándar.
"""

import argparse
import json
import math
import platform
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from modules.rag.search import REPO_ROOT, HelpIndex

OLLAMA = "http://localhost:11434"
OUT_DIR = REPO_ROOT / "docs" / "benchmarks" / "enrutador" / "01-criba-slm"
QUESTIONS = REPO_ROOT / "data" / "faqs" / "evaluacion-ayuda" / "preguntas.jsonl"

MODELS = [
    "qwen3.5:0.8b",
    "qwen3.5:2b",
    "qwen3.5:4b",
    "gemma4:e2b",
    "ministral-3:3b",
    "nemotron-3-nano:4b",
    "llama3.2:3b",
    "granite4:3b",
]

# 15 preguntas repartidas por temas (una pide aclarar: AYUDA-020).
FAQ_IDS = [
    "AYUDA-001", "AYUDA-010", "AYUDA-014", "AYUDA-020", "AYUDA-025",
    "AYUDA-031", "AYUDA-034", "AYUDA-040", "AYUDA-045", "AYUDA-048",
    "AYUDA-053", "AYUDA-058", "AYUDA-069", "AYUDA-080", "AYUDA-098",
]

# No aparecen en ninguna guía (comprobado con grep el 2026-11-26), pero el RAG
# devuelve fragmentos parecidos: lo correcto es abstenerse.
TRAPS = [
    ("TRAMPA-1", "¿Tenéis integración con Holded para facturar?"),
    ("TRAMPA-2", "¿Hay app de Apúntalo para Android TV?"),
    ("TRAMPA-3", "¿Apúntalo ya cumple con Verifactu?"),
    ("TRAMPA-4", "¿Mis clientes pueden pagar la señal con Bizum?"),
    ("TRAMPA-5", "¿Se puede conectar Apúntalo con Shopify?"),
]

ABSTAIN = "NO_LO_SE"

SYSTEM_PROMPT = f"""Eres el asistente de ayuda de Apúntalo, una aplicación de reservas y citas.
Responde en español de España, de forma breve y clara.
Usa SOLO la información de los fragmentos que te doy. No uses nada que no esté en ellos.
Si los fragmentos no responden a la pregunta, escribe solo {ABSTAIN}.
Si la pregunta es ambigua, haz una pregunta corta para aclararla.
En la última línea escribe siempre CONFIANZA: y un número de 0 a 1 que diga lo seguro que estás de que tu respuesta es correcta y está en los fragmentos."""

_CONF = re.compile(r"\**CONFIANZA\**\s*:\s*\**\s*([01](?:[.,]\d+)?)", re.IGNORECASE)
# Formas de abstenerse que usan los modelos además de NO_LO_SE. Solo cuentan al
# principio de la respuesta: "Sí, con Bizum… aunque no hay información" no es abstenerse.
_ABSTAIN_START = re.compile(
    r"^\W*(no_lo_se|no lo s[ée]|no tengo informaci[óo]n|no hay informaci[óo]n|"
    r"los fragmentos no|no se menciona|no aparece)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)
_ES = frozenset("el la los las de del que en y para con por una un es no se lo al como tu puedes si está".split())
_EN = frozenset("the and to of you can is in for with your this that are it on not".split())


def build_questions(k: int) -> list[dict]:
    """Las 20 preguntas con sus fragmentos del RAG (iguales para todos los modelos)."""
    gold = {}
    with open(QUESTIONS, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            gold[row["id"]] = row
    index = HelpIndex.load()
    questions = [
        {"id": i, "tipo": "faq", "pregunta": gold[i]["pregunta"],
         "conducta_esperada": gold[i]["conducta_esperada"],
         "respuesta_esperada": gold[i]["respuesta_esperada"]}
        for i in FAQ_IDS
    ] + [
        {"id": i, "tipo": "trampa", "pregunta": q,
         "conducta_esperada": "abstenerse", "respuesta_esperada": ABSTAIN}
        for i, q in TRAPS
    ]
    for q in questions:
        hits = index.search(q["pregunta"], k=k)
        q["fragmentos"] = [h.chunk.ref for h in hits]
        q["contexto"] = "\n\n".join(
            f"[{n}] {h.chunk.title}\n{h.chunk.text}" for n, h in enumerate(hits, 1)
        ) or "(no se ha encontrado ningún fragmento)"
    return questions


def ollama(path: str, body: dict | None = None, timeout: int = 600) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(OLLAMA + path, data, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def chat(model: str, question: dict, num_ctx: int) -> dict:
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "logprobs": True,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Fragmentos:\n{question['contexto']}\n\nPregunta: {question['pregunta']}"},
        ],
        "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx, "num_predict": 400},
    }
    try:
        return ollama("/api/chat", body)
    except urllib.error.HTTPError as e:
        # Los modelos sin modo "pensar" pueden rechazar el campo think.
        if "think" in e.read().decode(errors="ignore").lower():
            body.pop("think")
            return ollama("/api/chat", body)
        raise


def measure(answer: dict, question: dict, seconds: float, num_ctx: int) -> dict:
    text = answer["message"]["content"].strip()
    lp = answer.get("logprobs") or []
    probs = [math.exp(t["logprob"]) for t in lp]
    conf = _CONF.search(text)
    words = [w.lower() for w in _WORD.findall(text)]
    es, en = sum(w in _ES for w in words), sum(w in _EN for w in words)
    body = _CONF.sub("", text).strip()
    abstained = bool(_ABSTAIN_START.search(text))
    eval_s = answer.get("eval_duration", 0) / 1e9
    return {
        "respuesta": text,
        "segundos": round(seconds, 2),
        "tokens_salida": answer.get("eval_count"),
        "tokens_por_segundo": round(answer["eval_count"] / eval_s, 1) if eval_s else None,
        "tokens_entrada": answer.get("prompt_eval_count"),
        "contexto_lleno": (answer.get("prompt_eval_count") or 0) >= num_ctx - 50,
        "hay_logprobs": bool(probs),
        "prob_media_token": round(sum(probs) / len(probs), 3) if probs else None,
        "prob_min_token": round(min(probs), 3) if probs else None,
        "confianza_dicha": float(conf.group(1).replace(",", ".")) if conf else None,
        "formato_ok": bool(conf),
        "espanol": es >= en if words else None,
        "se_abstiene": abstained,
        "acierta_abstencion": abstained == (question["tipo"] == "trampa"),
        "vacia": not body,
    }


def model_info(model: str) -> dict:
    show = ollama("/api/show", {"model": model})
    details = show.get("details", {})
    tags = {m["name"]: m for m in ollama("/api/tags")["models"]}
    tag = tags.get(model) or tags.get(model + ":latest") or {}
    return {
        "familia": details.get("family"),
        "parametros": details.get("parameter_size"),
        "cuantizacion": details.get("quantization_level"),
        "digest": (tag.get("digest") or "")[:12],
        "tamano_gb": round(tag.get("size", 0) / 1e9, 2),
    }


def unload_all() -> None:
    """Saca de memoria los modelos cargados (Ollama los guarda 5 minutos)."""
    for m in ollama("/api/ps").get("models", []):
        ollama("/api/generate", {"model": m["name"], "keep_alive": 0})
    time.sleep(2)


def gpu_share(model: str) -> str:
    for m in ollama("/api/ps").get("models", []):
        if m["name"] == model or m["model"] == model:
            return f"{round(100 * m.get('size_vram', 0) / m['size'])} % GPU" if m.get("size") else "?"
    return "?"


def machine() -> dict:
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        gpu = ""
    cpu = next(
        (l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name")),
        platform.processor(),
    )
    return {"cpu": cpu, "gpu": gpu or "ninguna", "ollama": ollama("/api/version")["version"], "python": platform.python_version()}


def write_reports(rows: list[dict], questions: list[dict], infos: dict, env: dict, args) -> None:
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "resultados.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lines = [
        "# Criba de SLM: resumen", "",
        f"- Fecha: {env['fecha']}",
        f"- Máquina: {env['cpu']} · GPU: {env['gpu']} · Ollama {env['ollama']} · Python {env['python']}",
        f"- Preguntas: {len(FAQ_IDS)} de las guías + {len(TRAPS)} trampa · fragmentos del RAG: {args.k} · num_ctx: {args.num_ctx} · temperatura 0",
        "", "Columnas: **Trampas** = trampas en las que se abstiene (bien). **Abst. en guías** = preguntas de las guías en las que se abstiene (mal).",
        "", "| Modelo | Parám. | Cuant. | GPU | Español | Formato | Trampas | Abst. en guías | Vacías | s/resp. | tok/s | Logprobs |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model, info in infos.items():
        rs = [r for r in rows if r["modelo"] == model and "error" not in r]
        if not rs:
            lines.append(f"| {model} | – | – | – | error: {next((r['error'] for r in rows if r['modelo'] == model), '')[:60]} |||||||")
            continue
        faq = [r for r in rs if r["tipo"] == "faq"]
        trap = [r for r in rs if r["tipo"] == "trampa"]
        tps = [r["tokens_por_segundo"] for r in rs if r["tokens_por_segundo"]]
        lines.append(
            f"| {model} | {info.get('parametros')} | {info.get('cuantizacion')} | {info.get('gpu')} "
            f"| {sum(bool(r['espanol']) for r in rs)}/{len(rs)} | {sum(r['formato_ok'] for r in rs)}/{len(rs)} "
            f"| {sum(r['se_abstiene'] for r in trap)}/{len(trap)} | {sum(r['se_abstiene'] for r in faq)}/{len(faq)} "
            f"| {sum(r['vacia'] for r in rs)} | {sum(r['segundos'] for r in rs) / len(rs):.1f} "
            f"| {sum(tps) / len(tps):.0f} | {'sí' if all(r['hay_logprobs'] for r in rs) else 'no'} |"
            if tps else f"| {model} | … |"
        )
    lines += ["", "## Versiones exactas", "", "| Modelo | Familia | Tamaño | Digest |", "|---|---|---|---|"]
    lines += [f"| {m} | {i.get('familia')} | {i.get('tamano_gb')} GB | `{i.get('digest')}` |" for m, i in infos.items()]
    (out_dir / "resumen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = ["# Criba de SLM: respuestas", "",
           "Para puntuar a mano: 2 = correcta, 1 = parcial, 0 = incorrecta o inventada "
           "(rúbrica de `data/faqs/evaluacion-ayuda/README.md`).", ""]
    for q in questions:
        out += [f"## {q['id']} · {q['pregunta']}", "",
                f"**Esperado ({q['conducta_esperada']}):** {q['respuesta_esperada']}", "",
                f"Fragmentos: {', '.join(f'`{x}`' for x in q['fragmentos']) or 'ninguno'}", ""]
        for r in rows:
            if r["id"] != q["id"]:
                continue
            ans = r.get("respuesta", f"ERROR: {r.get('error')}").replace("\n", " ")
            out.append(f"- **{r['modelo']}** ({r.get('segundos', '–')} s): {ans}")
        out.append("")
    (out_dir / "respuestas.md").write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--k", type=int, default=3, help="fragmentos del RAG por pregunta")
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="carpeta de resultados")
    args = parser.parse_args()

    env = machine() | {"fecha": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}
    questions = build_questions(args.k)
    rows, infos = [], {}
    for model in args.models:
        print(f"\n== {model}")
        unload_all()  # que no haya otro modelo ocupando la GPU
        try:
            infos[model] = model_info(model)
            chat(model, questions[0], args.num_ctx)  # calentamiento: carga el modelo, no cuenta
            infos[model]["gpu"] = gpu_share(model)
        except Exception as e:  # modelo sin descargar, Ollama parado…
            print(f"   ERROR: {e}")
            infos.setdefault(model, {})
            rows.append({"modelo": model, "id": None, "error": str(e)})
            continue
        for q in questions:
            base = {"modelo": model, "id": q["id"], "tipo": q["tipo"], "maquina": env["gpu"]}
            try:
                t = time.perf_counter()
                answer = chat(model, q, args.num_ctx)
                r = base | measure(answer, q, time.perf_counter() - t, args.num_ctx)
                print(f"   {q['id']}: {r['segundos']:5.1f}s abst={r['se_abstiene']!s:5} conf={r['confianza_dicha']}")
            except Exception as e:
                r = base | {"error": str(e)}
                print(f"   {q['id']}: ERROR {e}")
            rows.append(r)
    unload_all()
    write_reports(rows, questions, infos, env, args)
    print(f"\nListo: {args.out}/resumen.md y respuestas.md")


if __name__ == "__main__":
    main()
