# captcha-am

API que recebe um captcha de texto distorcido (imagem) e devolve o texto reconhecido.

**Manual completo:** https://bapadua.github.io/captcha-py/

O captcha alvo tem: letras azuis sobre um fundo com ruído na mesma cor, cortadas por
uma linha diagonal escura. O pipeline isola o texto por cor (a linha e o ruído de
fundo ficam de fora do filtro) e remove resíduos pequenos. A partir daí, em vez de
OCR genérico, usa um **classificador por caractere**: compara cada caractere a
templates extraídos à mão das 3 amostras conhecidas (`app/templates.npz`, gerado por
`scripts/build_templates.py`). Como as letras dessa fonte se tocam (às vezes sem
nenhum afinamento entre elas), a divisão em caracteres é feita junto com o
reconhecimento — por programação dinâmica, testando onde cortar e escolhendo a
divisão cujos pedaços mais se parecem com os templates, em vez de supor que sempre
há um "vale" de tinta entre duas letras (ver comentários em `app/classifier.py`).

Esse approach substitui a tentativa inicial com Tesseract OCR (que acertava só 1 das
3 amostras); o código do OCR genérico continua em `app/ocr.py`/`app/preprocessing.py`
(`clean_captcha`) como referência, mas não é mais usado pela API.

## Requisitos

- Python 3.9+ (testado com 3.11; também funciona em 3.14 — todas as dependências
  já publicam wheels para essa versão).
- Não precisa mais de Tesseract instalado no sistema para o pipeline padrão (só seria
  necessário para usar `app/ocr.py` diretamente).

## Setup (Linux)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Setup (Windows)

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Rodando a API

Linux:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Windows:

```powershell
.venv\Scripts\uvicorn app.main:app --reload
```

- `GET /health` — checagem de disponibilidade.
- `POST /solve` — recebe a imagem como `multipart/form-data` (campo `file`, mais um
  campo opcional `length` — quantidade de caracteres, padrão `4`, igual às 3
  amostras) e devolve `{"text": "..."}`.

Exemplo (Linux/curl):

```bash
curl -F "file=@a.png" http://localhost:8000/solve
curl -F "file=@a.png" -F "length=5" http://localhost:8000/solve  # captcha com 5 caracteres
```

Exemplo (Windows/PowerShell):

```powershell
Invoke-RestMethod -Uri http://localhost:8000/solve -Method Post -Form @{ file = Get-Item .\a.png }
```

Exemplo (Python, usando `requests` — não é dependência do servidor, só do script
cliente; instale com `pip install requests`):

```python
import requests

def solve_captcha(image_path: str, length: int = 4) -> str:
    with open(image_path, "rb") as f:
        response = requests.post(
            "http://localhost:8000/solve",
            files={"file": f},
            data={"length": length},
        )
    response.raise_for_status()
    return response.json()["text"]


if __name__ == "__main__":
    print(solve_captcha("a.png"))
```

- `POST /templates` — treinamento incremental: você já sabe o texto certo de um
  captcha (ex.: resolveu manualmente, ou tem o gabarito de algum outro jeito) e quer
  que o classificador aprenda com ele. Recebe `file` (a imagem) e `text` (a resposta
  certa) e devolve os caracteres adicionados. Ver "Treinando com novas amostras"
  abaixo — **esse endpoint muda o estado do classificador para todo mundo que usa a
  API; não deixe exposto publicamente sem alguma proteção.**

## Testes

Linux:

```bash
.venv/bin/pytest tests/ -v
```

Windows:

```powershell
.venv\Scripts\pytest tests/ -v
```

Os testes rodam o pipeline diretamente contra as 3 imagens de amostra (`a.png`,
`b.png`, `c.png`) e comparam com o texto esperado.

## Treinando com novas amostras

Duas formas de ensinar o classificador a partir de um captcha cuja resposta certa
você já sabe:

### Em tempo real, via API

```bash
curl -F "file=@novo.png" -F "text=ab3d" http://localhost:8000/templates
```

Por trás, isso tenta achar sozinho onde cada caractere começa e termina — mas só
funciona com segurança se **todo** caractere de `text` já tiver pelo menos 1
template cadastrado (a busca compara cada pedaço candidato contra os templates já
existentes daquele caractere especificamente; sem nenhum exemplo de referência não
há como achar a fronteira certa). Se algum caractere for totalmente novo, a API
recusa com HTTP 422 e pede os cortes manuais:

```bash
# "cuts" = pontos de corte (x), na máscara ampliada por isolate_glyph_mask,
# entre cada par de caracteres — um a menos que o tamanho do texto.
curl -F "file=@novo.png" -F "text=ab3d" -F "cuts=90,180,270" http://localhost:8000/templates
```

Assim como em "ndam", nas 3 amostras originais (ver `app/known_samples.py`), achar esses
cortes à mão costuma exigir olhar a máscara isolada (`isolate_glyph_mask`) com uma
grade de coordenadas sobreposta — não tem como adivinhar de olho na imagem original.
Depois do primeiro cadastro manual de um caractere nunca visto, os próximos captchas
com essa mesma letra já podem ser resolvidos automaticamente (contanto que as outras
letras do texto também já tenham template).

### Pela interface web

Com a API rodando, `http://localhost:8000/` serve uma página simples (HTML/CSS/JS
puro, sem framework nem build step) para fazer a mesma coisa sem montar curl à
mão: arraste a imagem do captcha para a zona de drop, cole um print (Ctrl+V) ou
use o botão de escolher arquivo, veja a pré-visualização, preencha o texto certo
e envie. Diferente do curl acima, não é preciso adivinhar os números de `cuts`:
assim que uma imagem é escolhida, a página busca `POST /mask-preview` e mostra a
própria máscara isolada (a mesma imagem recortada/ampliada que a API usa por
dentro) — basta clicar entre as letras nessa máscara para marcar cada corte
(clicar de novo perto de uma linha já marcada remove ela), e o campo `cuts` é
preenchido automaticamente com as coordenadas corretas, ordenadas; um contador
mostra quantos cortes já foram marcados vs. quantos o texto digitado precisa, e
um botão "limpar cortes" reseta tudo. O campo continua editável manualmente, se
quiser ajustar um número à mão. O resultado do envio aparece na própria página —
em caso de HTTP 422, a mensagem de erro exata da API é mostrada e o campo `cuts`
é destacado, já que normalmente é isso que falta informar. É só uma alternativa
mais amigável ao `curl -F ... /templates` acima; a API continua igual.

### Em lote, editando o código

Para reconstruir os templates do zero a partir de `app/known_samples.py` (ex.: depois
de ajustar `MANUAL_CUTS` de alguma amostra):

```bash
.venv/bin/python scripts/build_templates.py
```

Isso **substitui** `app/templates.npz` pelos templates gerados só a partir de
`EXPECTED`/`MANUAL_CUTS` — ao contrário do endpoint acima, que só adiciona.

## Limitações conhecidas

O classificador acerta as 3 amostras disponíveis (`ndam`, `xo2e`, `dnf5`), mas isso
testa contra as mesmas imagens de onde vieram os templates — não é uma validação
contra captchas nunca vistos, que exigiria mais amostras reais rotuladas. Dois pontos
a ter em mente:

- **Tamanho do captcha**: a API assume 4 caracteres por padrão (`length=4`), porque é
  o que as 3 amostras têm. Ajuste por requisição se o captcha real variar.
- **Letras com um só exemplo**: cada caractere das amostras aparece só 1 ou 2 vezes
  nos templates (`d` e `n` aparecem 2x; os demais, 1x). Letras parecidas entre si com
  pouca amostragem (ex.: `m` de 3 pernas vs. `n` de 2) tendem a ser confundidas até
  que existam mais exemplos rotulados de cada uma — é exatamente pra isso que serve
  o `POST /templates`: cada vez que uma resposta certa aparecer (de qualquer fonte),
  cadastrá-la deixa o classificador mais robusto sem precisar mexer em código.
