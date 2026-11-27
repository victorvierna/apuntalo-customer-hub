"""Dibuja la figura de la criba de SLM (SVG, solo librería estándar).

Uso (desde la raíz del repo, después de ``criba_slm``)::

    python -m modules.router.benchmark.grafico_criba

Lee ``resultados.jsonl`` y escribe ``criba.svg`` en la misma carpeta, con dos
gráficos para la memoria:

1. Cada modelo como un punto: cuánto responde de lo que está en las guías (x)
   frente a cuántas trampas no se inventa (y). Arriba a la derecha es lo ideal.
2. Segundos por respuesta, del más rápido al más lento.
"""

import argparse
import json
from collections import defaultdict
from html import escape
from pathlib import Path

from modules.router.benchmark.criba_slm import OUT_DIR

FINALISTS = ["qwen3.5:4b", "ministral-3:3b", "granite4:3b", "gemma4:e2b"]

# Paleta de referencia (skill dataviz): azul = finalista, gris = descartado.
BLUE, GRAY = "#257de0", "#a3a3a3"
TEXT, TEXT_2, GRID, SURFACE, IDEAL = "#191919", "#666666", "#e6e6e6", "#ffffff", "#eef5fd"
FONT = "font-family='Inter, Helvetica, Arial, sans-serif'"


def summarize(path: Path) -> list[dict]:
    by_model = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if "error" not in r:
                by_model[r["modelo"]].append(r)
    out = []
    for model, rs in by_model.items():
        faq = [r for r in rs if r["tipo"] == "faq"]
        trap = [r for r in rs if r["tipo"] == "trampa"]
        out.append({
            "modelo": model,
            "responde": 100 * sum(not r["se_abstiene"] for r in faq) / len(faq),
            "no_inventa": 100 * sum(r["se_abstiene"] for r in trap) / len(trap),
            "segundos": sum(r["segundos"] for r in rs) / len(rs),
            "finalista": model in FINALISTS,
        })
    return out


def text(x, y, s, size=12, color=TEXT, anchor="start", weight=400):
    return (f"<text x='{x:.1f}' y='{y:.1f}' {FONT} font-size='{size}' fill='{color}' "
            f"text-anchor='{anchor}' font-weight='{weight}'>{escape(s)}</text>")


def text_box(x, y, lines, anchor, size=12, bold=False):
    """Caja aproximada (x0, y0, x1, y1) de un bloque de texto, para evitar solapes."""
    w = max(len(s) for s in lines) * size * (0.64 if bold else 0.58)
    x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    return (x0, y - size, x0 + w, y + (len(lines) - 1) * (size + 4) + 4)


def overlaps(a, b, pad=3):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


Y_MIN = 50  # con 5 trampas, los valores posibles son 0, 20, ... 100; ningún modelo baja de 60 %


def scatter(data: list[dict], ox: float, oy: float, w: float, h: float) -> list[str]:
    """Gráfico 1. (ox, oy) es la esquina superior izquierda del área de datos."""
    sx = lambda v: ox + v / 100 * w
    sy = lambda v: oy + h - (v - Y_MIN) / (100 - Y_MIN) * h
    el = [
        text(ox - 56, oy - 92, "¿Responde lo que sabe y se calla lo que no?", 16, weight=600),
        text(ox - 56, oy - 70, "Cada punto es un modelo: 15 preguntas de las guías y 5 preguntas trampa.", 12, TEXT_2),
    ]
    # Zona ideal: responde ≥ 90 % y no se inventa ≥ 90 %. Va debajo de todo.
    pad = 12
    el.append(f"<rect x='{sx(90):.1f}' y='{sy(100) - pad:.1f}' width='{sx(100) - sx(90) + pad:.1f}' "
              f"height='{sy(90) - sy(100) + pad:.1f}' fill='{IDEAL}' stroke='{BLUE}' "
              f"stroke-opacity='0.35' stroke-dasharray='4 3' rx='6'/>")
    for v in range(0, 101, 25):
        el.append(f"<line y1='{sy(Y_MIN)}' y2='{sy(100)}' x1='{sx(v):.1f}' x2='{sx(v):.1f}' stroke='{GRID}'/>")
        el.append(text(sx(v), sy(Y_MIN) + 20, f"{v} %", 11, TEXT_2, "middle"))
    for v in range(60, 101, 20):
        el.append(f"<line x1='{sx(0)}' x2='{sx(100)}' y1='{sy(v):.1f}' y2='{sy(v):.1f}' stroke='{GRID}'/>")
        el.append(text(sx(0) - 10, sy(v) + 4, f"{v} %", 11, TEXT_2, "end"))
    el.append(f"<line x1='{sx(0)}' x2='{sx(100)}' y1='{sy(Y_MIN)}' y2='{sy(Y_MIN)}' stroke='{TEXT_2}'/>")
    el.append(text(sx(50), sy(Y_MIN) + 44, "Preguntas de las guías que responde (no dice «no lo sé») →", 12, TEXT_2, "middle"))
    el.append(f"<g transform='translate({sx(0) - 46:.1f},{sy(75):.1f}) rotate(-90)'>"
              + text(0, 0, "Trampas en las que no se inventa nada →", 12, TEXT_2, "middle") + "</g>")

    # Agrupa los modelos que caen en el mismo punto.
    points = defaultdict(list)
    for d in data:
        points[(round(d["responde"]), round(d["no_inventa"]))].append(d)
    taken = [(sx(x) - 8, sy(y) - 8, sx(x) + 8, sy(y) + 8) for x, y in points]  # los propios puntos
    labels = []
    # Primero los finalistas, para que su etiqueta quede en el mejor sitio.
    for (x, y), ds in sorted(points.items(), key=lambda p: not any(d["finalista"] for d in p[1])):
        fin = any(d["finalista"] for d in ds)
        el.append(f"<circle cx='{sx(x):.1f}' cy='{sy(y):.1f}' r='7' fill='{BLUE if fin else GRAY}' "
                  f"stroke='{SURFACE}' stroke-width='2'><title>{escape(', '.join(d['modelo'] for d in ds))}: "
                  f"responde {x} %, no se inventa {y} %</title></circle>")
        names = [d["modelo"] for d in ds]
        stack = (len(names) - 1) * 16
        cx, cy = sx(x), sy(y)
        # Sitios candidatos: derecha, izquierda, arriba, abajo. Se queda con el primero libre.
        for lx, ly, anchor in [(cx + 13, cy + 4 - stack / 2, "start"), (cx - 13, cy + 4 - stack / 2, "end"),
                               (cx, cy - 14 - stack, "middle"), (cx, cy + 24, "middle")]:
            box = text_box(lx, ly, names, anchor, bold=fin)
            if not any(overlaps(box, t) for t in taken + labels):
                break
        labels.append(box)
        for i, name in enumerate(names):
            el.append(text(lx, ly + i * 16, name, 12, TEXT, anchor, 600 if fin else 400))
    return el


def bars(data: list[dict], ox: float, oy: float, w: float, h: float) -> list[str]:
    data = sorted(data, key=lambda d: d["segundos"])
    top = max(d["segundos"] for d in data)
    row = h / len(data)
    el = [
        text(ox - 140, oy - 92, "¿Cuánto tarda?", 16, weight=600),
        text(ox - 140, oy - 70, "Segundos por respuesta, media de las 20 preguntas.", 12, TEXT_2),
    ]
    for i, d in enumerate(data):
        y = oy + i * row + row / 2  # centro de la fila
        bw = max(d["segundos"] / top * w, 4)
        color = BLUE if d["finalista"] else GRAY
        el.append(text(ox - 12, y + 4, d["modelo"], 12, TEXT, "end", 600 if d["finalista"] else 400))
        # Extremo de datos redondeado; la base (izquierda), recta.
        el.append(f"<path d='M{ox},{y - 9:.1f} h{bw - 4:.1f} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 h-{bw - 4:.1f} z' "
                  f"fill='{color}'><title>{escape(d['modelo'])}: {d['segundos']:.1f} s</title></path>")
        el.append(text(ox + bw + 8, y + 4, f"{d['segundos']:.1f} s".replace(".", ","), 12, TEXT_2))
    el.append(f"<line x1='{ox}' x2='{ox}' y1='{oy}' y2='{oy + h}' stroke='{TEXT_2}'/>")
    el.append(text(ox, oy + h + 20, "RTX 3060 Laptop (6 GB) · Ollama · temperatura 0", 11, TEXT_2))
    return el


def legend(x: float, y: float) -> list[str]:
    return [
        f"<circle cx='{x}' cy='{y}' r='6' fill='{BLUE}'/>", text(x + 12, y + 4, "Finalista", 12),
        f"<circle cx='{x + 96}' cy='{y}' r='6' fill='{GRAY}'/>", text(x + 108, y + 4, "Descartado", 12),
        f"<rect x='{x + 196}' y='{y - 7}' width='14' height='14' rx='3' fill='{IDEAL}' stroke='{BLUE}' "
        f"stroke-opacity='0.35' stroke-dasharray='3 2'/>",
        text(x + 218, y + 4, "Zona ideal (≥ 90 % en los dos ejes)", 12),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    data = summarize(args.dir / "resultados.jsonl")

    W, H = 1120, 560
    body = [f"<rect width='{W}' height='{H}' fill='{SURFACE}'/>"]
    body += scatter(data, ox=96, oy=130, w=470, h=340)
    body += bars(data, ox=830, oy=130, w=220, h=340)
    body += legend(46, 98)
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' "
           f"role='img' aria-label='Criba de SLM: respuestas, trampas y velocidad de cada modelo'>"
           + "".join(body) + "</svg>\n")
    out = args.dir / "criba.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
