// Manual estático do captcha-am (GitHub Pages). Puro HTML/CSS/JS, sem build
// step, pelos mesmos motivos do resto do projeto: é só uma página de doc.

const navToggle = document.getElementById("nav-toggle");
const navLinks = document.getElementById("nav-links");

navToggle.addEventListener("click", () => {
  const open = navLinks.classList.toggle("open");
  navToggle.setAttribute("aria-expanded", String(open));
});

// Fecha o menu mobile ao navegar, senão ele fica aberto cobrindo a seção
// pra qual o usuário acabou de clicar.
navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
  });
});

// Destaca o link da seção visível no momento, pra dar noção de "onde eu
// estou" numa página longa de single-page.
const sections = document.querySelectorAll("main > section[id]");
const linkBySection = new Map(
  Array.from(navLinks.querySelectorAll("a")).map((a) => [a.getAttribute("href").slice(1), a])
);

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      const link = linkBySection.get(entry.target.id);
      if (!link) continue;
      if (entry.isIntersecting) {
        linkBySection.forEach((l) => l.classList.remove("active"));
        link.classList.add("active");
      }
    }
  },
  { rootMargin: "-40% 0px -55% 0px" }
);
sections.forEach((s) => observer.observe(s));

// Botão de copiar em cada bloco de código, pra não precisar selecionar o
// texto à mão (os comandos de curl/setup são o ponto principal da página).
document.querySelectorAll("pre").forEach((pre) => {
  const btn = document.createElement("button");
  btn.className = "copy-btn";
  btn.type = "button";
  btn.textContent = "Copiar";
  btn.addEventListener("click", async () => {
    const text = pre.querySelector("code")?.textContent ?? pre.textContent;
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copiado!";
    } catch {
      btn.textContent = "Erro ao copiar";
    }
    setTimeout(() => {
      btn.textContent = "Copiar";
    }, 1800);
  });
  pre.appendChild(btn);
});
