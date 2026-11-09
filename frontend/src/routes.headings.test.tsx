import { cleanup, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { allRoutes, renderRoute } from "./test/routes";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("cada rota tem um e um só <h1>", () => {
  it("a lista de rotas vem do App e inclui a 404", () => {
    const routes = allRoutes();
    expect(routes.length).toBeGreaterThan(25);
    expect(routes).toContain("/esta-pagina-nao-existe");
  });

  it.each(allRoutes())("%s", async (path) => {
    await renderRoute(path);
    await waitFor(() => expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1));
  });
});
