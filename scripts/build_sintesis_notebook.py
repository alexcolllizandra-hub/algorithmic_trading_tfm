"""Deterministically (re)build the synthesis notebook (08).

Run with: ``uv run python scripts/build_sintesis_notebook.py``

This notebook computes NOTHING. It chains the key figures of 01-07 into the
thesis argument in one reading. Its only code cell verifies that every figure
it embeds exists and records their hashes, so the chain breaks loudly if an
upstream notebook stops producing what this one shows.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import nbformat as nbf

CELLS: list = []


def md(text: str) -> None:
    CELLS.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(src: str) -> None:
    CELLS.append(nbf.v4.new_code_cell(src.strip("\n")))


FIGURES = [
    "eda/f03_price_evolution_drawdown",
    "features/g04_leakage_counterexample",
    "backtest/h05_walk_forward_geometry",
    "backtest/h02_cost_decomposition",
    "search/i02_selection_optimism",
    "search/i05_seed_instability",
    "closure/j02_multiple_testing",
    "closure/j03_deflated_sharpe_pbo",
    "ml/m01_economia_por_fold",
    "ml/m02_habilidad_predictiva",
    "montecarlo/k03_nula_con_la_estrategia_dentro",
    "montecarlo/k05_cuenta_fondeada",
]


def fig(name: str) -> str:
    return f"![{name}](../reports/figures/{name}.png)"


# --------------------------------------------------------------------------- #
md(
    r"""
# El argumento completo, de una lectura

**¿Qué pregunta responde este cuaderno?** Ninguna nueva: encadena lo que los
cuadernos 01-07 ya establecieron, en el orden en que el argumento se sostiene.
**¿Con qué datos?** Con sus figuras, tal cual quedaron guardadas — aquí no se
computa nada y no hay una sola celda de análisis. **¿Qué va a encontrar el
lector?** La tesis entera en doce imágenes: un mercado difícil, un aparato que
no se engaña, una búsqueda que encuentra ruido, y dos capas — aprendizaje
supervisado y Monte Carlo — que confirman el veredicto desde ángulos que no
tenían por qué coincidir.

Si solo se dispone de diez minutos para evaluar este trabajo, este es el
documento.
"""
)

code(
    r"""
# Contrato: este cuaderno solo embebe figuras. Verificamos que existen y
# registramos su hash, para que la cadena rompa en alto si un cuaderno
# anterior deja de producir lo que este muestra.
import hashlib
import os
import sys
from pathlib import Path

_root = Path.cwd()
while not (_root / "pyproject.toml").exists() and _root != _root.parent:
    _root = _root.parent
os.chdir(_root)

NB_CONTRACT = {
    "notebook": "08_sintesis",
    "inputs": [
        "reports/figures/eda/f03_price_evolution_drawdown.png",
        "reports/figures/features/g04_leakage_counterexample.png",
        "reports/figures/backtest/h05_walk_forward_geometry.png",
        "reports/figures/backtest/h02_cost_decomposition.png",
        "reports/figures/search/i02_selection_optimism.png",
        "reports/figures/search/i05_seed_instability.png",
        "reports/figures/closure/j02_multiple_testing.png",
        "reports/figures/closure/j03_deflated_sharpe_pbo.png",
        "reports/figures/ml/m01_economia_por_fold.png",
        "reports/figures/ml/m02_habilidad_predictiva.png",
        "reports/figures/montecarlo/k03_nula_con_la_estrategia_dentro.png",
        "reports/figures/montecarlo/k05_cuenta_fondeada.png",
    ],
    "outputs": {"figures": [], "tables": [], "dirs": []},
    "seed": None,
}

missing = [f for f in NB_CONTRACT["inputs"] if not Path(f).exists()]
if missing:
    raise FileNotFoundError(f"Un cuaderno anterior ya no produce: {missing}")
for f in NB_CONTRACT["inputs"]:
    digest = hashlib.sha256(Path(f).read_bytes()).hexdigest()
    print(f"{digest[:16]}  {f}")
"""
)

md(
    rf"""
## 1. El terreno: seis años que contienen de todo

{fig("eda/f03_price_evolution_drawdown")}

Dos activos líquidos, 2020-2025: una caída del 68% desde máximos, dos mercados
alcistas, meses laterales interminables. Quien afirme una ventaja en este
periodo no puede atribuirla a haber visto solo un régimen — y quien no la
encuentre, tampoco puede excusarse en que faltara variedad. *(Cuaderno 01.)*

## 2. El aparato se ganó la confianza antes de opinar

{fig("features/g04_leakage_counterexample")}

Antes de evaluar ninguna estrategia, plantamos una fuga de información a
propósito — una característica que lee el futuro — y comprobamos que los tests
de causalidad la detectan al instante. Un aparato que no es capaz de encontrar
la trampa que tú mismo le pones tampoco merece que le creas el resto.
*(Cuaderno 02.)*

## 3. El tiempo se respeta y los costes se pagan

{fig("backtest/h05_walk_forward_geometry")}

{fig("backtest/h02_cost_decomposition")}

Quince pliegues walk-forward con purga y embargo derivados — no elegidos a
ojo — y una contabilidad de ejecución que cobra comisión, deslizamiento y
funding en cada barra. La señal se decide con la vela cerrada y se ejecuta en
la apertura siguiente: el primer precio alcanzable sin clarividencia.
*(Cuaderno 03.)*

## 4. La búsqueda encuentra... lo que el ruido reparte

{fig("search/i02_selection_optimism")}

{fig("search/i05_seed_instability")}

El optimismo de selección medido: lo que el ganador de la validación promete y
lo que después entrega en test. Y la inestabilidad entre semillas: cambiar el
azar inicial de la búsqueda cambia al ganador — catorce parametrizaciones
distintas en quince pliegues en la ronda posterior. Una búsqueda que opera
sobre estructura converge; una que opera sobre ruido, baraja. *(Cuaderno 04.)*

## 5. El veredicto, contado honestamente

{fig("closure/j02_multiple_testing")}

{fig("closure/j03_deflated_sharpe_pbo")}

Trece familias, 496.500 configuraciones examinadas, y el p-valor bruto más
bajo del estudio queda en 0,345 — lejos del umbral *antes* de corregir nada, y
el panel (b) muestra que ninguna forma razonable de contar las pruebas cambia
eso. El Sharpe deflactado dice que el mejor resultado no supera lo que la
suerte prometía; el PBO, pegado a 0,5, dice que elegir al mejor in-sample es
una moneda al aire. Tres diagnósticos independientes, un solo mensaje.
*(Cuaderno 05.)*

## 6. ¿Y con aprendizaje supervisado? Mejora sin saber

{fig("ml/m01_economia_por_fold")}

{fig("ml/m02_habilidad_predictiva")}

El trío preregistrado — regresión logística, random forest, LightGBM — decide
cuándo actuar sobre las señales de una primaria. El brazo filtrado pierde menos
en todos los pliegues... con un AUC de moneda: toda la mejora viene de
abstenerse y recortar exposición, no de predecir. Una mejora económica no es
evidencia de conocimiento, y tenerlas separadas es lo que evita publicar la
primera como si fuera lo segundo. *(Cuaderno 06, contrato exploratorio.)*

## 7. La imagen que resume el trabajo

{fig("montecarlo/k03_nula_con_la_estrategia_dentro")}

La mejor familia del estudio — ya rechazada por la estadística — frente a mil
versiones de sí misma con las posiciones rotadas al azar sobre las mismas
barras: misma exposición, mismos costes, cero información. Las diez ejecuciones
reales caen repartidas dentro de la banda del azar, en percentiles de 0,22 a
0,97 — exactamente como se reparten diez sorteos. Todo el capítulo 5 de
estadística está en esta imagen. *(Cuaderno 07.)*

## 8. Y la advertencia con número propio

{fig("montecarlo/k05_cuenta_fondeada")}

Bajo reglas típicas de cuenta fondeada — declaradas y ajustables — esta
estrategia indistinguible del azar supera la fase 1 el 31% de las veces y las
dos fases el 11,5%. Una de cada tres personas que la operasen "pasaría la
prueba" y se creería con ventaja. Ese es el mecanismo por el que la industria
de señales y evaluaciones fabrica convencidos, y la razón de que el simulador
de la plataforma exista. *(Cuaderno 07.)*

---

## Lo que estas doce imágenes afirman, y lo que no

Afirman: que en este espacio acotado — reglas interpretables y su capa de
meta-etiquetado, dos perpetuos, velas de una hora, seis años, costes
realistas — una búsqueda rigurosa no encuentra nada que sobreviva a contar
cuántas veces se miró, y que el instrumento de medida quedó validado antes y
después con trampas plantadas, presupuestos verificados y nulas a medida.

No afirman: que los mercados sean eficientes, que el trading algorítmico no
funcione, ni que otro espacio — más frecuencia, más activos, otra información —
fuera a dar lo mismo. Cada límite del alcance es una extensión falsable, y las
tres primeras están preregistradas en el trabajo futuro.

Queda dicho también lo que más costó decir: la partición reservada se abrió
fuera de protocolo, la lectura está retenida, y la cadena de commits que lo
prueba se conservó intacta a propósito. Un estudio que publica su propia
discrepancia pide ser creído por sus registros, no por su palabra — y ese es,
al final, el estándar que este trabajo propone.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/08_sintesis.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    _write()
