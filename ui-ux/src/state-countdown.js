const countdown = document.querySelector("[data-state-countdown]");

if (countdown) {
  const output = countdown.querySelector("[data-countdown-output]");
  const button = document.querySelector("[data-countdown-action]");
  let remaining = Number.parseInt(countdown.dataset.stateCountdown || "0", 10);

  const render = () => {
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    output.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    if (remaining <= 0) {
      button.disabled = false;
      button.textContent = "Tentar novamente";
      countdown.querySelector("span").textContent = "Já podes voltar a tentar";
      return;
    }

    remaining -= 1;
    window.setTimeout(render, 1000);
  };

  render();
}
