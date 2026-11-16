from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.classifier import classify_word
from app.preprocessing import isolate_glyph_mask
from app.training import SegmentationError, add_sample

# As 3 amostras conhecidas têm todas 4 caracteres; ajuste via parâmetro `length`
# se o captcha real usar outro tamanho.
_DEFAULT_LENGTH = 4

app = FastAPI(title="captcha-am")


def _decode_image(raw_bytes: bytes) -> np.ndarray:
    buffer = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida")
    return image


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/solve")
async def solve(file: UploadFile, length: int = Form(_DEFAULT_LENGTH)) -> dict:
    image = _decode_image(await file.read())
    mask = isolate_glyph_mask(image)
    text = classify_word(mask, length)
    return {"text": text}


@app.post("/mask-preview")
async def mask_preview(file: UploadFile) -> Response:
    """Devolve a máscara isolada (mesma usada por /solve e /templates) como PNG.

    Existe só para a UI: `cuts` precisa estar nas coordenadas dessa máscara
    recortada/ampliada, não da imagem original, e não há como o usuário adivinhar
    esses pixels sem ver a própria máscara — então expomos ela para a página
    desenhar por cima em vez de pedir números às cegas.
    """
    image = _decode_image(await file.read())
    mask = isolate_glyph_mask(image)
    ok, buffer = cv2.imencode(".png", mask)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao gerar PNG da máscara")
    return Response(content=buffer.tobytes(), media_type="image/png")


@app.post("/templates")
async def add_template_sample(
    file: UploadFile,
    text: str = Form(...),
    cuts: str | None = Form(None),
) -> dict:
    """Rotula um captcha (a resposta certa já é conhecida) e adiciona seus
    caracteres aos templates do classificador, para ele acertar casos parecidos
    no futuro. `cuts` é opcional: pontos de corte entre caracteres separados por
    vírgula, só necessário se a segmentação automática errar (comum quando a
    palavra tem letra cursiva nunca vista antes — ver app/training.py).

    Cuidado: esse endpoint muda o estado do classificador para todo mundo que
    usa essa API. Não deixe exposto publicamente sem alguma proteção.
    """
    image = _decode_image(await file.read())
    mask = isolate_glyph_mask(image)
    parsed_cuts = [int(c) for c in cuts.split(",")] if cuts else None

    try:
        labels = add_sample(mask, text, cuts=parsed_cuts)
    except SegmentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"added": labels}


# Montado por último, depois das rotas acima, para não sombrear /health,
# /solve e /templates — StaticFiles(html=True) serve index.html em "/".
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
