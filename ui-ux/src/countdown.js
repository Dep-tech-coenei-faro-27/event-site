(() => {
  const countdowns = Array.from(document.querySelectorAll("[data-countdown]"));

  if (!countdowns.length) return;

  const second = 1000;
  const minute = 60 * second;
  const hour = 60 * minute;
  const day = 24 * hour;

  const setValue = (countdown, name, value, length) => {
    const output = countdown.querySelector(`[data-countdown-${name}]`);
    if (output) output.textContent = String(value).padStart(length, "0");
  };

  const updateCountdown = (countdown) => {
    const target = Date.parse(countdown.dataset.countdown);

    if (Number.isNaN(target)) return false;

    const remaining = Math.max(0, target - Date.now());
    const days = Math.floor(remaining / day);
    const hours = Math.floor((remaining % day) / hour);
    const minutes = Math.floor((remaining % hour) / minute);
    const seconds = Math.floor((remaining % minute) / second);

    setValue(countdown, "days", days, 3);
    setValue(countdown, "hours", hours, 2);
    setValue(countdown, "minutes", minutes, 2);
    setValue(countdown, "seconds", seconds, 2);

    if (remaining === 0) {
      const intro = countdown.querySelector(".countdown__intro");
      if (intro) intro.textContent = "O ENEI 2027 já começou.";
      return false;
    }

    return true;
  };

  let intervalId;

  const updateAll = () => {
    let hasActiveCountdown = false;
    countdowns.forEach((countdown) => {
      hasActiveCountdown = updateCountdown(countdown) || hasActiveCountdown;
    });
    if (!hasActiveCountdown && intervalId) window.clearInterval(intervalId);
  };

  updateAll();
  intervalId = window.setInterval(updateAll, second);
})();
