"""Adiciona amostras rotuladas (imagem + texto correto) aos templates do
classificador, sem precisar rodar scripts/build_templates.py manualmente.

A segmentação automática aqui reaproveita a busca por programação dinâmica de
`app.classifier.segment_dp`, mas em vez de deixar qualquer caractere competir
(como em `classify_word`), cada posição já tem o rótulo certo (vem do texto
informado) — o que falta descobrir são só os cortes, comparando cada pedaço
candidato contra os templates já cadastrados *daquele* caractere específico.

Isso só funciona se todo caractere de `text` já tiver pelo menos 1 template: sem
nenhum exemplo de referência não há como saber onde aquela letra começa e
termina (mesmo problema de fundo do app/classifier.py — numa fonte cursiva,
"menos tinta" não é garantia de fronteira entre letras). Pra cadastrar um
caractere totalmente novo, informe `cuts` manualmente a primeira vez; dali em
diante a segmentação automática já pode reconhecê-lo.
"""
from __future__ import annotations

import numpy as np

from app import classifier
from app.segmentation import normalize_glyph


class SegmentationError(Exception):
    pass


def _score_against_label(glyph: np.ndarray, label: str) -> float:
    templates = classifier.label_templates(label)
    glyph_bin = glyph > 0
    intersection = np.logical_and(glyph_bin, templates).sum(axis=(1, 2))
    union = np.logical_or(glyph_bin, templates).sum(axis=(1, 2))
    scores = np.divide(intersection, union, out=np.zeros_like(intersection, dtype=float), where=union > 0)
    return float(scores.max())


def segment_for_text(mask: np.ndarray, text: str) -> list[np.ndarray] | None:
    """Tenta achar automaticamente onde cada caractere de `text` começa e termina
    em `mask`. Devolve `None` se não encontrar nenhuma divisão válida.

    Recusa (devolve `None`) se algum caractere de `text` ainda não tiver nenhum
    template cadastrado — nesse caso não há com que comparar o pedaço candidato,
    então qualquer corte seria só palpite. Use `cuts` manuais nesse caso.
    """
    missing = sorted({c for c in text if len(classifier.label_templates(c)) == 0})
    if missing:
        return None

    width = mask.shape[1]
    glyph_cache: dict[tuple[int, int], np.ndarray] = {}

    def glyph_at(x0: int, x1: int) -> np.ndarray:
        key = (x0, x1)
        if key not in glyph_cache:
            glyph_cache[key] = normalize_glyph(mask[:, x0:x1])
        return glyph_cache[key]

    def score_fn(k: int, x0: int, x1: int) -> float:
        return _score_against_label(glyph_at(x0, x1), text[k])

    bounds = classifier.segment_dp(width, len(text), score_fn)
    if bounds is None:
        return None
    return [glyph_at(x0, x1) for x0, x1 in bounds]


def add_sample(mask: np.ndarray, text: str, cuts: list[int] | None = None) -> list[str]:
    """Extrai um glyph por caractere de `text` e adiciona aos templates.

    `cuts` (opcional) são os `len(text) - 1` pontos de corte, nas mesmas
    coordenadas de `app.preprocessing.isolate_glyph_mask` — use quando a
    segmentação automática falhar ou acertar no lugar errado (foi necessário
    para "ndam" nas 3 amostras originais; ver app/known_samples.py).
    """
    if cuts is not None:
        if len(cuts) != len(text) - 1:
            raise SegmentationError(f"esperava {len(text) - 1} cortes para {len(text)} caracteres, recebi {len(cuts)}")
        bounds = [0, *cuts, mask.shape[1]]
        glyphs = [normalize_glyph(mask[:, x0:x1]) for x0, x1 in zip(bounds[:-1], bounds[1:])]
    else:
        missing = sorted({c for c in text if len(classifier.label_templates(c)) == 0})
        if missing:
            raise SegmentationError(
                f"caracteres sem template ainda: {missing!r}; informe `cuts` manualmente "
                "para cadastrá-los pela primeira vez"
            )
        glyphs = segment_for_text(mask, text)
        if glyphs is None:
            raise SegmentationError("não foi possível segmentar automaticamente; informe `cuts` manualmente")

    new_labels = np.array(list(text))
    new_glyphs = (np.stack(glyphs) > 0).astype(np.uint8) * 255

    data = np.load(classifier.TEMPLATES_PATH)
    all_labels = np.concatenate([data["labels"], new_labels])
    all_glyphs = np.concatenate([data["glyphs"], new_glyphs])
    np.savez(classifier.TEMPLATES_PATH, labels=all_labels, glyphs=all_glyphs)

    classifier.reload_templates()
    return list(text)
