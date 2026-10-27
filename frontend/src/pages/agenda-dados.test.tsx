import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Agenda from "./Agenda";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const at = (element: React.ReactElement, path = "/?dia=quinta") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>{element}</main>
    </MemoryRouter>,
  );

describe("Agenda lê da fonte de dados", () => {
  const tag = { kind: "Palestra", category: "palestras" as const };

  it("desenha cada item com hora, local e orador, e não desenha os que têm visible:false", () => {
    at(
      <Agenda
        items={[
          { id: "qui-1000-abertura", start: "2027-04-01T10:00", title: "Abertura", ...tag, location: "Auditório 1", speaker: { name: "Ana Silva", company: "Empresa X" } },
          { id: "qui-1100-escondida", start: "2027-04-01T11:00", title: "Sessão escondida", ...tag, visible: false },
        ]}
      />,
    );
    expect(screen.getByRole("heading", { name: "Abertura" })).toBeInTheDocument();
    expect(screen.getByText("Auditório 1")).toBeInTheDocument();
    expect(screen.getByText("Ana Silva")).toBeInTheDocument();
    expect(screen.getByText(/Empresa X/)).toBeInTheDocument();
    expect(screen.queryByText("Sessão escondida")).toBeNull();
    // o `id` do item fica no elemento (âncora e ligação das inscrições) e a hora leva o fuso de Lisboa
    expect(document.getElementById("qui-1000-abertura")).not.toBeNull();
    expect(document.querySelector("time")!.getAttribute("datetime")).toBe("2027-04-01T10:00+01:00");
  });
});
