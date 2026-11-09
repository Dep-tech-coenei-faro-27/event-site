import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderRoute } from "../test/routes";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

describe("ligação «Saltar para o conteúdo»", () => {
  it.each(["/", "/bilhetes", "/conta", "/perfil"])("em %s é o primeiro elemento focável", async (path) => {
    await renderRoute(path);
    const first = document.querySelector<HTMLElement>(FOCUSABLE);
    expect(first).toHaveTextContent("Saltar para o conteúdo");
    expect(first).toHaveAttribute("href", "#conteudo");
  });

  it("fica fora do ecrã até receber foco e aparece quando o recebe", async () => {
    await renderRoute("/");
    const link = screen.getByRole("link", { name: "Saltar para o conteúdo" });
    // Escondida com posição (não com display/visibility), para continuar a receber foco.
    expect(link.className).toMatch(/(^|\s)-top-20(\s|$)/);
    expect(link.className).toMatch(/(^|\s)focus:top-4(\s|$)/);
    expect(link.className).not.toMatch(/(^|\s)(hidden|invisible)(\s|$)/);
  });

  it("leva ao <main id=conteudo> e move-lhe o foco", async () => {
    await renderRoute("/bilhetes");
    const main = document.querySelector("main")!;
    expect(main).toHaveAttribute("id", "conteudo");
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(document.querySelectorAll("#conteudo")).toHaveLength(1);

    const link = screen.getByRole("link", { name: "Saltar para o conteúdo" });
    link.focus();
    fireEvent.click(link);
    expect(document.activeElement).toBe(main);
  });

  it.each(["/", "/bilhetes", "/equipa", "/informacao-ajuda", "/termos", "/conta", "/conta/criar", "/perfil", "/bilhetes/checkout"])(
    "em %s há um só elemento com id=conteudo",
    async (path) => {
      await renderRoute(path);
      expect(document.querySelectorAll("#conteudo")).toHaveLength(1);
    },
  );
});
