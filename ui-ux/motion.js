(() => {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const body = document.body;
  const header = document.querySelector(".site-header");

  body.classList.add("motion-ready");

  const progress = document.createElement("div");
  progress.className = "site-progress";
  progress.setAttribute("aria-hidden", "true");
  progress.innerHTML = '<span class="site-progress__bar"></span>';
  body.prepend(progress);

  const hero = document.querySelector(".hero");
  const logoPasser = document.querySelector("[data-logo-passer]");
  const logoPasserMark = document.querySelector("[data-logo-passer-mark]");
  if (hero) {
    const signal = document.createElement("span");
    signal.className = "hero-signal";
    signal.setAttribute("aria-hidden", "true");
    hero.append(signal);
  }

  const revealGroups = [
    [".section-heading > *", "up"],
    [".home-edition .split > *", "up"],
    [".pathway", "up"],
    [".programme-preview__item", "up"],
    [".home-faro-photo", "left"],
    [".home-experience .split > *", "up"],
    [".home-closing .container > *", "up"],
    [".fact", "up"],
    [".timeline-item", "up"],
    [".photo", "up"],
    [".speaker-profile", "up"],
    [".experience-tile", "up"],
    [".team-department__header", "left"],
    [".team-member", "up"],
    [".benefit-item", "up"],
    [".tier", "up"],
    [".logo-placeholder", "up"],
    [".ticket-card", "up"],
    [".checkout-step", "up"],
    [".checkout-panel", "left"],
    [".auth-intro > *", "left"],
    [".auth-card", "right"],
    [".account-content > *", "up"],
    [".location-card", "up"],
    [".countdown", "up"],
    [".faq-layout > *", "up"],
    [".legal-layout > *", "up"],
    [".system-state-content > *", "up"],
    [".payment-status > *", "up"],
    [".checkout-heading__copy > *", "up"],
    [".registration-checklist > *", "up"],
    [".programme-axis", "up"],
    [".platform-flow__item", "up"],
    [".support-panel", "right"],
    [".legal-section", "up"],
    [".footer-main > *", "up"],
  ];

  const revealItems = new Set();
  revealGroups.forEach(([selector, direction]) => {
    document.querySelectorAll(selector).forEach((element, index) => {
      if (revealItems.has(element)) return;
      revealItems.add(element);
      element.dataset.motionItem = direction;
      element.style.setProperty(
        "--motion-delay",
        `${Math.min(index * 36, 144)}ms`,
      );
    });
  });

  const mediaItems = document.querySelectorAll(
    ".photo, .campus-photo, .location-card__visual, .home-faro-photo, .team-member__photo, .speaker-profile__media",
  );
  mediaItems.forEach((element) => element.classList.add("motion-media"));

  document.querySelectorAll("main > .section").forEach((section) => {
    section.classList.add("motion-section");
    const trace = document.createElement("span");
    trace.className = "motion-section__trace";
    trace.setAttribute("aria-hidden", "true");
    section.prepend(trace);
  });

  const revealImmediately =
    reducedMotion.matches || !("IntersectionObserver" in window);

  if (revealImmediately) {
    revealItems.forEach((element) => element.classList.add("motion-visible"));
    mediaItems.forEach((element) =>
      element.classList.add("motion-media-visible"),
    );
    document
      .querySelectorAll(".motion-section")
      .forEach((section) => section.classList.add("motion-section-active"));
  } else {
    const observer = new IntersectionObserver(
      (entries, activeObserver) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("motion-visible");
          entry.target.classList.add("motion-media-visible");
          entry.target.classList.add("motion-section-active");
          activeObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -5%" },
    );
    revealItems.forEach((element) => observer.observe(element));
    mediaItems.forEach((element) => observer.observe(element));
    document
      .querySelectorAll(".motion-section")
      .forEach((section) => observer.observe(section));
  }

  let ticking = false;
  const updateScrollState = () => {
    const scrollRange = document.documentElement.scrollHeight - innerHeight;
    const scrollProgress = scrollRange > 0 ? scrollY / scrollRange : 0;
    body.style.setProperty(
      "--scroll-progress",
      String(Math.max(0, Math.min(1, scrollProgress))),
    );
    header?.classList.toggle("motion-header--scrolled", scrollY > 20);
    if (
      hero &&
      !reducedMotion.matches &&
      hero.getBoundingClientRect().bottom > 0
    ) {
      hero.style.setProperty(
        "--hero-shift",
        `${Math.min(scrollY * 0.045, 22)}px`,
      );
    }
    if (logoPasser && logoPasserMark && !reducedMotion.matches) {
      const bounds = logoPasser.getBoundingClientRect();
      const progress = Math.max(
        0,
        Math.min(1, (innerHeight - bounds.top) / (innerHeight + bounds.height)),
      );
      logoPasser.style.setProperty(
        "--passing-logo-y",
        `${(0.5 - progress) * 84}px`,
      );
      logoPasser.style.setProperty(
        "--passing-logo-opacity",
        String(0.22 + progress * 0.28),
      );
      logoPasser.style.setProperty(
        "--passing-logo-scale",
        String(0.96 + progress * 0.1),
      );
    }
    ticking = false;
  };

  const requestScrollUpdate = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(updateScrollState);
  };

  updateScrollState();
  addEventListener("scroll", requestScrollUpdate, { passive: true });

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (
      !link ||
      reducedMotion.matches ||
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      link.target === "_blank" ||
      link.hasAttribute("download")
    ) {
      return;
    }

    const url = new URL(link.href, location.href);
    if (
      !["http:", "https:", "file:"].includes(url.protocol) ||
      (url.protocol !== "file:" && url.origin !== location.origin) ||
      (url.pathname === location.pathname && url.hash)
    ) {
      return;
    }

    event.preventDefault();
    body.classList.add("motion-page-leave");
    setTimeout(() => {
      location.href = url.href;
    }, 120);
  });
})();
