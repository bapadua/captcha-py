"""Reconhecimento de texto na imagem já limpa (binária, texto preto sobre branco)."""
from __future__ import annotations

import os

import numpy as np
import pytesseract

# No Windows o instalador do Tesseract nem sempre adiciona o tesseract.exe ao PATH.
_tesseract_cmd = os.environ.get("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

_CHAR_WHITELIST = "abcdefghijklmnopqrstuvwxyz0123456789"
_TESSERACT_CONFIG = (
    "--oem 3 --psm 8 "
    f"-c tessedit_char_whitelist={_CHAR_WHITELIST} "
    # desliga os dicionários de linguagem: sem eles o Tesseract para de "corrigir"
    # os caracteres reconhecidos para se parecerem com palavras em inglês
    "-c load_system_dawg=0 -c load_freq_dawg=0 -c load_punc_dawg=0 "
    "-c load_number_dawg=0 -c load_unambig_dawg=0 -c load_bigram_dawg=0 "
    "-c load_fixed_length_dawgs=0"
)


def recognize_text(binary_image: np.ndarray) -> str:
    raw = pytesseract.image_to_string(binary_image, config=_TESSERACT_CONFIG)
    return raw.strip().lower()
