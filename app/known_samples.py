"""Texto correto das 3 imagens de amostra do repositório, usado tanto para
construir os templates do classificador quanto para os testes automatizados.
"""

EXPECTED = {
    "a.png": "ndam",
    "b.png": "xo2e",
    "c.png": "dnf5",
}

# Pontos de corte (coordenada x, na máscara ampliada por isolate_glyph_mask) entre
# cada par de caracteres, determinados visualmente. Necessário porque, nessas 3
# amostras, a tinta entre letras vizinhas nem sempre é o ponto mais "fino" da
# palavra — às vezes um vão dentro da própria letra (ex.: entre as duas pernas do
# "m") é mais estreito que a emenda real entre duas letras, o que confunde a
# segmentação automática por perfil de tinta. Usado só para construir os
# templates (scripts/build_templates.py); o reconhecimento de captchas novos não
# depende disso.
MANUAL_CUTS = {
    "a.png": [105, 215, 310],
    "b.png": [100, 176, 264],
    "c.png": [89, 187, 259],
}
