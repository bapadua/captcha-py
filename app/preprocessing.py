"""Isola o texto do captcha, removendo o ruído de fundo e a linha diagonal.

O texto e o ruído de fundo têm a mesma cor (azul), mas o ruído aparece como
manchas pequenas e isoladas enquanto as letras formam componentes conectados
grandes. A linha diagonal é escura/pouco saturada, então já fica de fora do
filtro de cor usado para isolar o texto.
"""
from __future__ import annotations

import cv2
import numpy as np

# Faixa de matiz (H) do azul do texto no espaço HSV do OpenCV (0-179).
_HUE_RANGE = (95, 135)
_MIN_SATURATION = 60
_MIN_COMPONENT_AREA = 25
_PADDING = 15
_TARGET_HEIGHT = 300


def _text_color_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, _ = cv2.split(hsv)
    lo, hi = _HUE_RANGE
    mask = ((h >= lo) & (h <= hi) & (s > _MIN_SATURATION)).astype(np.uint8) * 255
    return mask


def _remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    for label in range(1, num_labels):
        if stats[label, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == label] = 255
    return cleaned


def _crop_to_content(mask: np.ndarray, padding: int) -> np.ndarray:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return mask
    x0, x1 = max(xs.min() - padding, 0), min(xs.max() + padding, mask.shape[1])
    y0, y1 = max(ys.min() - padding, 0), min(ys.max() + padding, mask.shape[0])
    return mask[y0:y1, x0:x1]


def isolate_glyph_mask(bgr: np.ndarray, target_height: int = 150) -> np.ndarray:
    """Recebe a imagem original (BGR) e devolve a máscara do texto (branco = tinta,
    preto = fundo), já recortada no bounding box e ampliada. Usada como entrada do
    classificador por caractere (app.segmentation / app.classifier).
    """
    mask = _text_color_mask(bgr)
    mask = _remove_small_components(mask, _MIN_COMPONENT_AREA)
    mask = _crop_to_content(mask, padding=4)

    scale = target_height / mask.shape[0]
    mask = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    return mask


def clean_captcha(bgr: np.ndarray) -> np.ndarray:
    """Recebe a imagem original (BGR) e devolve uma imagem binária pronta para OCR:
    texto preto sobre fundo branco, recortada e ampliada.
    """
    mask = isolate_glyph_mask(bgr, target_height=_TARGET_HEIGHT)

    # fecha pequenas falhas nos traços deixadas pelo upscale
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # texto preto sobre fundo branco (melhor para o Tesseract) + borda branca
    binary = cv2.bitwise_not(mask)
    binary = cv2.copyMakeBorder(
        binary, _PADDING, _PADDING, _PADDING, _PADDING,
        cv2.BORDER_CONSTANT, value=255,
    )
    return binary
