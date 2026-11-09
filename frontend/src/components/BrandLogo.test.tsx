import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BrandLogo from "./BrandLogo";

const scrollTo = vi.fn();
const reload = vi.fn();

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <BrandLogo />
      <Routes>
        <Route path="/" element={<p>página inicial</p>} />
        <Route path="/sobre" element={<p>página sobre</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  scrollTo.mockClear();
  reload.mockClear();
  vi.stubGlobal("scrollTo", scrollTo);
  vi.stubGlobal("location", { ...window.location, reload });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("logótipo do ENEI", () => {
  it("na página inicial sobe ao topo e recarrega a página (o router sozinho não fazia nada)", () => {
    renderAt("/");
    fireEvent.click(screen.getByRole("link"));
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("noutra página leva à página inicial pelo router (o ScrollToTop trata de ir ao topo)", () => {
    renderAt("/sobre");
    expect(screen.getByText("página sobre")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link"));
    expect(screen.getByText("página inicial")).toBeInTheDocument();
    expect(scrollTo).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
  });

  it("com Ctrl, Cmd ou Shift deixa o browser abrir a ligação como sempre", () => {
    renderAt("/");
    for (const modifier of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }]) {
      fireEvent.click(screen.getByRole("link"), modifier);
    }
    expect(scrollTo).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
  });

  it("aponta sempre para /", () => {
    renderAt("/sobre");
    expect(screen.getByRole("link")).toHaveAttribute("href", "/");
  });
});
