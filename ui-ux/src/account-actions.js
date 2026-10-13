const exportButton = document.querySelector("[data-export-account]");

if (exportButton) {
  exportButton.addEventListener("click", () => {
    const accountData = {
      exportedAt: new Date().toISOString(),
      profile: {
        name: "Participante Exemplo",
        email: "participante@exemplo.pt",
        institution: "",
        course: "",
      },
      emailVerified: true,
      ticket: {
        reference: "ENEI—XXXX",
        type: "Experiência completa",
        dates: "1–4 abril 2027",
      },
    };
    const file = new Blob([JSON.stringify(accountData, null, 2)], {
      type: "application/json",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(file);
    link.download = "dados-conta-enei.json";
    link.click();
    URL.revokeObjectURL(link.href);

    const status = document.querySelector("[data-export-status]");
    status.hidden = false;
    status.textContent = "Ficheiro preparado.";
  });
}

const deleteDialog = document.querySelector("[data-delete-dialog]");

if (deleteDialog) {
  const openButton = document.querySelector("[data-delete-open]");
  const cancelButton = deleteDialog.querySelector("[data-delete-cancel]");
  const input = deleteDialog.querySelector("[data-delete-input]");
  const confirmButton = deleteDialog.querySelector("[data-delete-confirm]");
  const status = document.querySelector("[data-delete-status]");

  openButton.addEventListener("click", () => {
    input.value = "";
    confirmButton.disabled = true;
    deleteDialog.showModal();
    window.setTimeout(() => input.focus(), 0);
  });

  input.addEventListener("input", () => {
    confirmButton.disabled = input.value.trim().toUpperCase() !== "ELIMINAR";
  });

  cancelButton.addEventListener("click", () => deleteDialog.close());

  confirmButton.addEventListener("click", () => {
    deleteDialog.close();
    status.hidden = false;
    status.textContent =
      "Demonstração: o pedido seria agora enviado de forma segura.";
  });
}
