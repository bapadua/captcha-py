from pathlib import Path

import cv2
import pytest

from app.classifier import classify_word
from app.known_samples import EXPECTED
from app.preprocessing import isolate_glyph_mask

SAMPLES_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("filename,expected", EXPECTED.items())
def test_sample_recognition(filename: str, expected: str) -> None:
    image = cv2.imread(str(SAMPLES_DIR / filename))
    mask = isolate_glyph_mask(image)
    text = classify_word(mask, len(expected))
    assert text == expected
