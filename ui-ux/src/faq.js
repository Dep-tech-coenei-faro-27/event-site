(() => {
  const items = [...document.querySelectorAll(".faq-item[data-category]")];
  if (!items.length) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const questions = [...document.querySelectorAll(".faq-question")];
  const categoryButtons = [...document.querySelectorAll("[data-faq-category]")];
  const mobileCategory = document.querySelector("[data-faq-mobile-category]");
  const search = document.querySelector("[data-faq-search]");
  const emptyState = document.querySelector("[data-faq-empty]");
  let activeCategory = "todos";

  const normalizeText = (value) =>
    value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();

  const setAnswerState = (button, open, animate = true) => {
    const answer = button.nextElementSibling;
    if (!answer?.classList.contains("faq-answer")) return;

    button.setAttribute("aria-expanded", String(open));
    answer.getAnimations().forEach((animation) => animation.cancel());

    if (reducedMotion.matches || !animate) {
      answer.hidden = !open;
      return;
    }

    if (open) {
      answer.hidden = false;
      const height = answer.scrollHeight;
      answer.animate(
        [
          { height: "0px", opacity: 0 },
          { height: `${height}px`, opacity: 1 },
        ],
        {
          duration: 220,
          easing: "cubic-bezier(0, 0, 0.2, 1)",
        },
      );
      return;
    }

    const height = answer.scrollHeight;
    answer
      .animate(
        [
          { height: `${height}px`, opacity: 1 },
          { height: "0px", opacity: 0 },
        ],
        {
          duration: 180,
          easing: "cubic-bezier(0.4, 0, 1, 1)",
        },
      )
      .finished.then(() => {
        if (button.getAttribute("aria-expanded") === "false") {
          answer.hidden = true;
        }
      })
      .catch(() => {});
  };

  questions.forEach((button, index) => {
    const answer = button.nextElementSibling;
    const buttonId = button.id || `faq-question-${index + 1}`;
    const answerId = answer?.id || `faq-answer-${index + 1}`;

    button.type = "button";
    button.id = buttonId;
    button.setAttribute("aria-controls", answerId);
    if (answer?.classList.contains("faq-answer")) {
      answer.id = answerId;
      answer.setAttribute("role", "region");
      answer.setAttribute("aria-labelledby", buttonId);
      answer.hidden = button.getAttribute("aria-expanded") !== "true";
    }

    button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") !== "true";
      setAnswerState(button, open);
    });
  });

  const filterItems = () => {
    const query = normalizeText(search?.value || "");
    let visibleCount = 0;

    items.forEach((item) => {
      const categoryMatches =
        activeCategory === "todos" || item.dataset.category === activeCategory;
      const textMatches =
        !query || normalizeText(item.textContent).includes(query);
      const visible = categoryMatches && textMatches;
      item.hidden = !visible;
      item.classList.toggle("hidden", !visible);
      if (visible) visibleCount += 1;
    });

    if (emptyState) {
      emptyState.hidden = visibleCount > 0;
      emptyState.classList.toggle("hidden", visibleCount > 0);
    }
  };

  const setCategory = (category) => {
    activeCategory = category;
    categoryButtons.forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.faqCategory === category),
      );
    });
    if (mobileCategory) mobileCategory.value = category;
    filterItems();
  };

  categoryButtons.forEach((button) => {
    button.type = "button";
    button.addEventListener("click", () =>
      setCategory(button.dataset.faqCategory),
    );
  });
  mobileCategory?.addEventListener("change", () =>
    setCategory(mobileCategory.value),
  );
  search?.addEventListener("input", filterItems);
})();
