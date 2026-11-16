"""Normalização de recortes de caracteres para comparação com templates.

A divisão da palavra em caracteres não é feita aqui: em fontes cursivas como essa,
o ponto de menos tinta entre duas letras às vezes nem existe (elas se conectam sem
afinar), então segmentar antes de reconhecer não é confiável. Ver `app.classifier`,
que decide onde cortar e o que cada pedaço é ao mesmo tempo.
"""
from __future__ import annotations

import cv2
import numpy as np

_GLYPH_SIZE = 48


def _tight_crop(glyph: np.ndarray) -> np.ndarray:
    ys, xs = np.where(glyph > 0)
    if len(xs) == 0:
        return glyph
    return glyph[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def normalize_glyph(glyph: np.ndarray, size: int = _GLYPH_SIZE) -> np.ndarray:
    """Centraliza o caractere num canvas quadrado de tamanho fixo, preservando a
    proporção original — necessário para comparar caracteres de larguras diferentes.
    """
    glyph = _tight_crop(glyph)
    h, w = glyph.shape
    if h == 0 or w == 0:
        return np.zeros((size, size), dtype=np.uint8)

    margin = 4
    scale = (size - margin) / max(h, w)
    new_w, new_h = max(int(round(w * scale)), 1), max(int(round(h * scale)), 1)
    resized = cv2.resize(glyph, (new_w, new_h), interpolation=cv2.INTER_AREA)
    _, resized = cv2.threshold(resized, 60, 255, cv2.THRESH_BINARY)

    canvas = np.zeros((size, size), dtype=np.uint8)
    y0, x0 = (size - new_h) // 2, (size - new_w) // 2
    canvas[y0 : y0 + new_h, x0 : x0 + new_w] = resized
    return canvas
