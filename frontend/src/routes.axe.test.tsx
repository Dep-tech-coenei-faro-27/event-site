// @vitest-environment jsdom
import { cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { allRoutes, renderRoute } from "./test/routes";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// O jsdom não desenha a página: as regras que dependem de cores e posições calculadas
// (contraste, alvos de toque, elementos que se tapam) não dão resultado fiável e ficam de fora.
// O contraste tem o seu próprio teste (contrast.test.tsx).
const NOT_COMPUTED_IN_JSDOM = { "color-contrast": { enabled: false }, "target-size": { enabled: false } };

describe("axe: zero violações em cada página", () => {
  it.each(allRoutes())("%s", async (path) => {
    const { container } = await renderRoute(path);
    const results = await axe(container, { rules: NOT_COMPUTED_IN_JSDOM });
    const violations = results.violations.map((v) => ({
      rule: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target.join(" ")),
    }));
    expect(violations).toEqual([]);
  });
});
