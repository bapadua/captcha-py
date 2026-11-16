"""Classifica cada caractere comparando-o aos templates extraídos das amostras
rotuladas (ver scripts/build_templates.py e POST /templates em app/main.py), em
vez de usar OCR genérico.

A segmentação em caracteres é resolvida junto com o reconhecimento, em vez de
decidir os cortes antes e só depois classificar. Em fontes cursivas como essa,
o ponto com menos tinta entre duas letras às vezes nem existe (as letras se
conectam sem afinar) — então, em vez de procurar "vales", testamos por
programação dinâmica todo corte possível (a cada `_STEP` pixels) e escolhemos a
sequência de `n_chars` pedaços cuja soma de confiança contra os templates é a
maior, sem depender do perfil de tinta ter um mínimo exatamente onde as letras
se separam. `app.training` reaproveita essa mesma busca para encaixar amostras
novas de texto já conhecido.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.segmentation import normalize_glyph

TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.npz"
MIN_SEGMENT_WIDTH = 12
_STEP = 3


def _load_templates() -> tuple[np.ndarray, np.ndarray]:
    data = np.load(TEMPLATES_PATH)
    labels = data["labels"]
    glyphs = data["glyphs"] > 0  # já em bool, para IoU vetorizado
    return labels, glyphs


_LABELS, _TEMPLATES = _load_templates()


def reload_templates() -> None:
    """Recarrega `templates.npz` do disco (chamado depois de app.training.add_sample)."""
    global _LABELS, _TEMPLATES
    _LABELS, _TEMPLATES = _load_templates()


def label_templates(label: str) -> np.ndarray:
    """Templates (bool, shape (T, 48, 48)) já cadastrados para esse caractere."""
    return _TEMPLATES[_LABELS == label]


def _best_match(glyph: np.ndarray) -> tuple[str, float]:
    glyph_bin = glyph > 0
    intersection = np.logical_and(glyph_bin, _TEMPLATES).sum(axis=(1, 2))
    union = np.logical_or(glyph_bin, _TEMPLATES).sum(axis=(1, 2))
    scores = np.divide(intersection, union, out=np.zeros_like(intersection, dtype=float), where=union > 0)
    best_idx = int(np.argmax(scores))
    return str(_LABELS[best_idx]), float(scores[best_idx])


def classify_glyph(glyph: np.ndarray) -> str:
    label, _ = _best_match(glyph)
    return label


def segment_dp(
    width: int, n_chars: int, score_fn
) -> list[tuple[int, int]] | None:
    """Programação dinâmica genérica: acha os `n_chars` pedaços (cada um um par
    `(x0, x1)`) que maximizam a soma de `score_fn(k, x0, x1)`, `k` sendo o índice
    do caractere (0-based). `score_fn` deve devolver `None` para um pedaço
    inválido (ex.: estreito demais).
    """
    positions = list(range(0, width, _STEP)) + [width]
    cache: dict[tuple[int, int, int], float | None] = {}

    def scored(k: int, x0: int, x1: int) -> float | None:
        if x1 - x0 < MIN_SEGMENT_WIDTH:
            return None
        key = (k, x0, x1)
        if key not in cache:
            cache[key] = score_fn(k, x0, x1)
        return cache[key]

    dp: list[dict[int, tuple[float, int]]] = [dict() for _ in range(n_chars)]
    for pos in positions:
        s = scored(0, 0, pos)
        if s is not None:
            dp[0][pos] = (s, 0)

    for k in range(1, n_chars):
        for pos in positions:
            best: tuple[float, int] | None = None
            for prev, (prev_score, _) in dp[k - 1].items():
                if prev >= pos:
                    continue
                s = scored(k, prev, pos)
                if s is None:
                    continue
                total = prev_score + s
                if best is None or total > best[0]:
                    best = (total, prev)
            if best:
                dp[k][pos] = best

    if width not in dp[n_chars - 1]:
        return None

    bounds = []
    k, pos = n_chars - 1, width
    while k >= 0:
        _, prev = dp[k][pos]
        bounds.append((prev, pos))
        pos = prev
        k -= 1
    return list(reversed(bounds))


def classify_word(mask: np.ndarray, n_chars: int) -> str:
    """Reconhece uma palavra de `n_chars` caracteres na máscara de texto já
    isolada (ver `app.preprocessing.isolate_glyph_mask`).
    """
    if n_chars == 1:
        return classify_glyph(normalize_glyph(mask))

    match_cache: dict[tuple[int, int], tuple[str, float]] = {}

    def best_match_cached(x0: int, x1: int) -> tuple[str, float]:
        key = (x0, x1)
        if key not in match_cache:
            match_cache[key] = _best_match(normalize_glyph(mask[:, x0:x1]))
        return match_cache[key]

    bounds = segment_dp(mask.shape[1], n_chars, lambda k, x0, x1: best_match_cached(x0, x1)[1])
    if bounds is None:
        return "?" * n_chars
    return "".join(best_match_cached(x0, x1)[0] for x0, x1 in bounds)
