"""Gera app/templates.npz a partir das 3 imagens de amostra rotuladas em
app/known_samples.py. Rodar de novo sempre que novas amostras forem rotuladas:

    .venv/bin/python scripts/build_templates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.known_samples import EXPECTED, MANUAL_CUTS  # noqa: E402
from app.preprocessing import isolate_glyph_mask  # noqa: E402
from app.segmentation import normalize_glyph  # noqa: E402


def main() -> None:
    labels: list[str] = []
    glyphs: list[np.ndarray] = []

    for filename, text in EXPECTED.items():
        image = cv2.imread(str(ROOT / filename))
        mask = isolate_glyph_mask(image)
        bounds = [0, *MANUAL_CUTS[filename], mask.shape[1]]
        for char, x0, x1 in zip(text, bounds[:-1], bounds[1:]):
            labels.append(char)
            glyphs.append(normalize_glyph(mask[:, x0:x1]))

    out_path = ROOT / "app" / "templates.npz"
    np.savez(out_path, labels=np.array(labels), glyphs=np.array(glyphs))
    print(f"{len(labels)} templates salvos em {out_path}: {''.join(labels)}")


if __name__ == "__main__":
    main()
