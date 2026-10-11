const dialog = document.querySelector("[data-ticket-dialog]");
const form = document.querySelector("[data-ticket-form]");
const toast = document.querySelector("[data-admin-toast]");
const sidebar = document.querySelector(".admin-sidebar");
const menuToggle = document.querySelector("[data-admin-menu-toggle]");
const searchForm = document.querySelector(".admin-search");
const currentView = document.body.dataset.adminView || "overview";
let toastTimer;

const viewCopy = {
  overview: {
    eyebrow: "Administração",
    title: "Centro de controlo",
    description:
      "Gere operações, conteúdo e configurações do site num único local, com atalhos para responder rapidamente a incidentes.",
    ticketAction: true,
  },
  utilizadores: {
    eyebrow: "Operações",
    title: "Utilizadores",
    description:
      "Consulta contas, verifica o acesso e resolve rapidamente problemas dos participantes.",
  },
  bilhetes: {
    eyebrow: "Operações",
    title: "Bilhetes",
    description:
      "Gere modalidades, disponibilidade e emissões manuais com registo de auditoria.",
    ticketAction: true,
    panelTitle: "Bilhetes e modalidades",
    panelDescription:
      "Disponibilidade, condições, preços e ferramentas de emissão.",
  },
  transacoes: {
    eyebrow: "Operações",
    title: "Transações",
    description:
      "Acompanha pagamentos e identifica inscrições pendentes ou com falhas.",
  },
  apoio: {
    eyebrow: "Operações",
    title: "Apoio",
    description:
      "Centraliza pedidos, ocorrências e problemas reportados pelos participantes.",
  },
  paginas: {
    eyebrow: "Site e conteúdo",
    title: "Páginas e menus",
    description:
      "Atualiza a navegação, os conteúdos públicos e a informação legal do site.",
    panelTitle: "Conteúdo público",
    panelDescription:
      "Homepage, menus, rodapé, textos, chamadas para ação e páginas legais.",
  },
  programa: {
    eyebrow: "Site e conteúdo",
    title: "Programa",
    description:
      "Organiza dias, horários, atividades, espaços e alterações de última hora.",
    panelTitle: "Programa e agenda",
    panelDescription:
      "Edita a informação do programa sem interferir com outras áreas do site.",
  },
  "equipa-parcerias": {
    eyebrow: "Site e conteúdo",
    title: "Equipa e parcerias",
    description:
      "Gere pessoas, cargos, fotografias, entidades parceiras e logótipos.",
    panelTitle: "Equipa e parceiros",
    panelDescription:
      "Mantém a apresentação da organização e das entidades atualizada.",
  },
  comunicacao: {
    eyebrow: "Site e conteúdo",
    title: "Comunicação",
    description:
      "Prepara avisos no site, emails e mensagens dirigidas aos participantes.",
    panelTitle: "Canais de comunicação",
    panelDescription:
      "Publica mensagens claras sem alterar as restantes áreas do site.",
  },
  "estado-erros": {
    eyebrow: "Sistema",
    title: "Estado e erros",
    description:
      "Verifica serviços essenciais e acede às ações rápidas para resolver incidentes.",
  },
  auditoria: {
    eyebrow: "Sistema",
    title: "Auditoria",
    description:
      "Consulta alterações, ações manuais e alertas para investigar erros com rapidez.",
  },
  definicoes: {
    eyebrow: "Sistema",
    title: "Definições",
    description:
      "Controla permissões, integrações e opções gerais da plataforma.",
  },
};

function configureAdminPage() {
  const copy = viewCopy[currentView] || viewCopy.overview;
  const heading = document.querySelector(".admin-heading");
  const headingAction = heading?.querySelector("[data-open-ticket-modal]");

  if (heading) {
    heading.querySelector(".eyebrow").textContent = copy.eyebrow;
    heading.querySelector("h1").textContent = copy.title;
    heading.querySelector("div > p:last-child").textContent = copy.description;
  }
  if (headingAction) headingAction.hidden = !copy.ticketAction;

  if (copy.panelTitle) {
    const panelHead = document.querySelector(
      "#conteudo-site .admin-panel__head",
    );
    panelHead.querySelector(".eyebrow").textContent = copy.eyebrow;
    panelHead.querySelector("h2").textContent = copy.panelTitle;
    panelHead.querySelector("div > p:last-child").textContent =
      copy.panelDescription;
  }

  document
    .querySelectorAll(".admin-nav a[aria-current]")
    .forEach((item) => item.removeAttribute("aria-current"));
  document
    .querySelector(`[data-admin-link="${currentView}"]`)
    ?.setAttribute("aria-current", "page");
}

configureAdminPage();

function closeAdminSelect(select, restoreFocus = false) {
  const root = select.closest(".admin-select");
  const trigger = root?.querySelector(".admin-select__trigger");
  const menu = root?.querySelector(".admin-select__menu");
  if (!root || !trigger || !menu) return;
  root.classList.remove("is-open");
  trigger.setAttribute("aria-expanded", "false");
  menu.hidden = true;
  if (restoreFocus) trigger.focus();
}

function openAdminSelect(select, focusSelected = false) {
  document.querySelectorAll("[data-admin-select]").forEach((other) => {
    if (other !== select) closeAdminSelect(other);
  });
  const root = select.closest(".admin-select");
  const trigger = root?.querySelector(".admin-select__trigger");
  const menu = root?.querySelector(".admin-select__menu");
  if (!root || !trigger || !menu) return;
  root.classList.add("is-open");
  trigger.setAttribute("aria-expanded", "true");
  menu.hidden = false;
  if (focusSelected) {
    menu.querySelector('[aria-selected="true"]')?.focus();
  }
}

document.querySelectorAll("[data-admin-select]").forEach((select, index) => {
  const labelId = select.getAttribute("aria-labelledby");
  const listboxId = `admin-select-listbox-${index + 1}`;
  const root = document.createElement("div");
  root.className = "admin-select";
  select.parentNode.insertBefore(root, select);
  root.append(select);
  select.classList.add("admin-select__native");
  select.tabIndex = -1;

  const trigger = document.createElement("button");
  trigger.className = "admin-select__trigger";
  trigger.type = "button";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-controls", listboxId);
  if (labelId)
    trigger.setAttribute("aria-labelledby", `${labelId} ${listboxId}-value`);
  trigger.innerHTML = `<span id="${listboxId}-value"></span><span class="admin-select__chevron" aria-hidden="true"></span>`;

  const menu = document.createElement("ul");
  menu.className = "admin-select__menu";
  menu.id = listboxId;
  menu.role = "listbox";
  menu.hidden = true;

  [...select.options].forEach((option, optionIndex) => {
    const item = document.createElement("li");
    item.role = "presentation";
    const button = document.createElement("button");
    button.className = "admin-select__option";
    button.type = "button";
    button.role = "option";
    button.dataset.value = option.value;
    button.setAttribute(
      "aria-selected",
      String(optionIndex === select.selectedIndex),
    );
    button.textContent = option.textContent;
    item.append(button);
    menu.append(item);
  });

  root.append(trigger, menu);
  const value = trigger.querySelector("span");
  value.textContent = select.options[select.selectedIndex]?.textContent || "";

  function choose(optionButton) {
    select.value = optionButton.dataset.value;
    value.textContent = optionButton.textContent;
    menu.querySelectorAll(".admin-select__option").forEach((item) => {
      item.setAttribute("aria-selected", String(item === optionButton));
    });
    select.dispatchEvent(new Event("change", { bubbles: true }));
    closeAdminSelect(select, true);
  }

  trigger.addEventListener("click", () => {
    if (root.classList.contains("is-open")) closeAdminSelect(select);
    else openAdminSelect(select, true);
  });
  trigger.addEventListener("keydown", (event) => {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      openAdminSelect(select, true);
    }
  });
  menu.addEventListener("click", (event) => {
    const optionButton = event.target.closest(".admin-select__option");
    if (optionButton) choose(optionButton);
  });
  menu.addEventListener("keydown", (event) => {
    const options = [...menu.querySelectorAll(".admin-select__option")];
    const currentIndex = options.indexOf(document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      closeAdminSelect(select, true);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      options[(currentIndex + step + options.length) % options.length]?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      options[event.key === "Home" ? 0 : options.length - 1]?.focus();
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (document.activeElement.matches(".admin-select__option")) {
        choose(document.activeElement);
      }
    }
  });
});

document.addEventListener("click", (event) => {
  document.querySelectorAll("[data-admin-select]").forEach((select) => {
    if (!select.closest(".admin-select")?.contains(event.target)) {
      closeAdminSelect(select);
    }
  });
});

function showToast(message) {
  if (!toast) return;
  toast.textContent = `${message}. Nenhum dado foi alterado nesta demonstração.`;
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 5000);
}

function openDialog() {
  if (!dialog) return;
  dialog.showModal();
  requestAnimationFrame(() => dialog.querySelector("input")?.focus());
}

function closeDialog() {
  dialog?.close();
}

document.querySelectorAll("[data-open-ticket-modal]").forEach((button) => {
  button.addEventListener("click", openDialog);
});

document.querySelectorAll("[data-close-ticket-modal]").forEach((button) => {
  button.addEventListener("click", closeDialog);
});

dialog?.addEventListener("click", (event) => {
  if (event.target === dialog) closeDialog();
});

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  if (!form.reportValidity()) return;
  closeDialog();
  form.reset();
  showToast("Bilhete demonstrativo emitido");
});

document.querySelectorAll("[data-demo-action]").forEach((button) => {
  button.addEventListener("click", () => {
    showToast(button.dataset.demoAction || "Ação preparada");
  });
});

menuToggle?.addEventListener("click", () => {
  const open = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute(
    "aria-label",
    open ? "Fechar navegação do painel" : "Abrir navegação do painel",
  );
  sidebar?.classList.toggle("is-open", open);
});

document.querySelectorAll(".admin-nav a").forEach((link) => {
  link.addEventListener("click", () => {
    sidebar?.classList.remove("is-open");
    menuToggle?.setAttribute("aria-expanded", "false");
  });
});

searchForm?.addEventListener("submit", (event) => {
  event.preventDefault();
});

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    document.querySelector("#admin-search")?.focus();
  }
});
