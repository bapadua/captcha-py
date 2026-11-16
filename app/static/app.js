// UI simples para alimentar POST /templates sem precisar montar curl à mão.
// Sem build step nem dependências externas, de propósito (ferramenta interna).

const dropzone = document.getElementById("dropzone");
const dropzoneHint = document.getElementById("dropzone-hint");
const pickBtn = document.getElementById("pick-btn");
const fileInput = document.getElementById("file-input");
const preview = document.getElementById("preview");
const form = document.getElementById("form");
const textInput = document.getElementById("text-input");
const cutsInput = document.getElementById("cuts-input");
const submitBtn = document.getElementById("submit-btn");
const resultBox = document.getElementById("result");
const successToast = document.getElementById("success-toast");
const successToastMessage = document.getElementById("success-toast-message");

const maskSection = document.getElementById("mask-section");
const maskImage = document.getElementById("mask-image");
const maskCanvas = document.getElementById("mask-canvas");
const maskError = document.getElementById("mask-error");
const cutsCounter = document.getElementById("cuts-counter");
const clearCutsBtn = document.getElementById("clear-cuts-btn");
const maskCtx = maskCanvas.getContext("2d");

let selectedFile = null;
let successToastTimer = null;
// Coordenadas x (em pixels da máscara, não da tela) dos cortes marcados.
let cuts = [];
// Tolerância em pixels da máscara para considerar um clique "em cima" de um
// corte existente (e removê-lo) em vez de criar um novo.
const CUT_CLICK_TOLERANCE_PX = 6;

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  dropzoneHint.textContent = file.name;
  updateSubmitState();
  loadMaskPreview(file);
}

function resetCuts() {
  cuts = [];
  syncCutsInput();
  drawCutLines();
}

async function loadMaskPreview(file) {
  maskSection.hidden = false;
  maskError.hidden = true;
  resetCuts();

  const body = new FormData();
  body.append("file", file);

  try {
    const res = await fetch("/mask-preview", { method: "POST", body });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Erro HTTP ${res.status}`);
    }
    const blob = await res.blob();
    // Revoga a URL anterior (se houver) só depois que a nova imagem carregar,
    // para não deixar o <img> momentaneamente sem src em recargas rápidas.
    const url = URL.createObjectURL(blob);
    const previousUrl = maskImage.dataset.objectUrl;
    maskImage.onload = () => {
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      // Canvas precisa ter o mesmo tamanho em pixels da imagem (resolução
      // natural) para que um clique vire diretamente uma coordenada de
      // pixel da máscara, sem conversão de escala adivinhada.
      maskCanvas.width = maskImage.naturalWidth;
      maskCanvas.height = maskImage.naturalHeight;
      drawCutLines();
    };
    maskImage.dataset.objectUrl = url;
    maskImage.src = url;
  } catch (err) {
    maskError.hidden = false;
    maskError.textContent = `Não foi possível carregar a máscara: ${err.message}`;
  }
}

// Converte a posição de um clique na tela para um x em pixels da máscara,
// considerando qualquer escala CSS (ex.: zoom do navegador) entre o tamanho
// natural da imagem e o tamanho realmente renderizado.
function clickToMaskX(ev) {
  const rect = maskCanvas.getBoundingClientRect();
  const scale = maskImage.naturalWidth / rect.width;
  const x = (ev.clientX - rect.left) * scale;
  return Math.round(Math.max(0, Math.min(x, maskImage.naturalWidth - 1)));
}

function drawCutLines() {
  maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
  maskCtx.strokeStyle = "#ef4444";
  maskCtx.lineWidth = 2;
  for (const x of cuts) {
    maskCtx.beginPath();
    maskCtx.moveTo(x + 0.5, 0);
    maskCtx.lineTo(x + 0.5, maskCanvas.height);
    maskCtx.stroke();
  }
  updateCutsCounter();
}

function updateCutsCounter() {
  const textLen = textInput.value.trim().length;
  const needed = Math.max(textLen - 1, 0);
  cutsCounter.textContent = `${cuts.length}/${needed} cortes marcados`;
}

function syncCutsInput() {
  cutsInput.value = cuts.slice().sort((a, b) => a - b).join(",");
}

maskCanvas.addEventListener("click", (ev) => {
  const x = clickToMaskX(ev);
  const existingIndex = cuts.findIndex((c) => Math.abs(c - x) <= CUT_CLICK_TOLERANCE_PX);
  if (existingIndex >= 0) {
    cuts.splice(existingIndex, 1);
  } else {
    cuts.push(x);
  }
  cuts.sort((a, b) => a - b);
  syncCutsInput();
  drawCutLines();
});

clearCutsBtn.addEventListener("click", () => resetCuts());

// Edição manual do campo continua funcionando (ex.: ajustar um número fino);
// refletimos de volta nas linhas desenhadas para os dois jeitos não ficarem
// fora de sincronia.
cutsInput.addEventListener("input", () => {
  const raw = cutsInput.value.trim();
  cuts = raw
    ? raw.split(",").map((c) => parseInt(c.trim(), 10)).filter((n) => !Number.isNaN(n))
    : [];
  drawCutLines();
});

function updateSubmitState() {
  submitBtn.disabled = !(selectedFile && textInput.value.trim());
}

// Botão abre o picker nativo; é só uma 3a forma de escolher o arquivo além de
// drag-and-drop e colar.
pickBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

dropzone.addEventListener("dragover", (ev) => {
  ev.preventDefault();
  dropzone.classList.add("drag-over");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", (ev) => {
  ev.preventDefault();
  dropzone.classList.remove("drag-over");
  const file = ev.dataTransfer.files[0];
  setFile(file);
});

// Colar um print (ex.: screenshot do captcha) direto na página, sem precisar
// salvar em arquivo primeiro.
document.addEventListener("paste", (ev) => {
  const items = ev.clipboardData && ev.clipboardData.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      setFile(file);
      break;
    }
  }
});

textInput.addEventListener("input", () => {
  updateSubmitState();
  updateCutsCounter();
});

function showResult(kind, message) {
  resultBox.hidden = false;
  resultBox.className = `result ${kind}`;
  resultBox.textContent = message;
}

function highlightCuts() {
  cutsInput.classList.add("highlight");
  cutsInput.focus();
}

function showSuccessToast(message) {
  successToastMessage.textContent = message;
  successToast.classList.add("show");
  // Reinicia o timer a cada sucesso, em vez de deixar um dismiss antigo
  // cortar a exibição de um toast mais recente.
  clearTimeout(successToastTimer);
  successToastTimer = setTimeout(() => {
    successToast.classList.remove("show");
  }, 3500);
}

// Volta o formulário ao estado exato do primeiro load, para o usuário poder
// soltar/colar/escolher a próxima imagem sem limpar nada manualmente.
function resetForm() {
  selectedFile = null;
  fileInput.value = "";

  preview.hidden = true;
  preview.removeAttribute("src");
  dropzoneHint.textContent = "Arraste uma imagem aqui, cole (Ctrl+V) ou";

  textInput.value = "";
  cutsInput.value = "";
  cutsInput.classList.remove("highlight");

  maskSection.hidden = true;
  maskError.hidden = true;
  const previousMaskUrl = maskImage.dataset.objectUrl;
  if (previousMaskUrl) URL.revokeObjectURL(previousMaskUrl);
  maskImage.removeAttribute("src");
  delete maskImage.dataset.objectUrl;

  resetCuts();

  resultBox.hidden = true;
  resultBox.textContent = "";

  updateSubmitState();
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (!selectedFile) return;

  cutsInput.classList.remove("highlight");
  submitBtn.disabled = true;
  showResult("ok", "Enviando...");

  const body = new FormData();
  body.append("file", selectedFile);
  body.append("text", textInput.value.trim());
  const cutsValue = cutsInput.value.trim();
  if (cutsValue) body.append("cuts", cutsValue);

  try {
    const res = await fetch("/templates", { method: "POST", body });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      showSuccessToast(`Template adicionado: ${JSON.stringify(data.added)}`);
      resetForm();
    } else {
      // O ponto principal da UI: o 422 manda a mensagem exata (geralmente
      // pedindo `cuts`) — tem que aparecer visível e acionável, não só "erro".
      const detail = data.detail || `Erro HTTP ${res.status}`;
      showResult("error", detail);
      if (res.status === 422) highlightCuts();
    }
  } catch (err) {
    showResult("error", `Falha ao conectar: ${err.message}`);
  } finally {
    updateSubmitState();
  }
});
