import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import Footer from "./Footer";

afterEach(cleanup);

describe("rodapé", () => {
  it("as redes sociais levam às páginas oficiais do ENEI e abrem noutro separador", () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    );
    const expected: Record<string, string> = {
      Instagram: "https://www.instagram.com/eneiconf/",
      Facebook: "https://www.facebook.com/eneiconf/?locale=pt_PT",
      LinkedIn: "https://pt.linkedin.com/company/eneiconf",
    };
    for (const [name, href] of Object.entries(expected)) {
      const link = screen.getByRole("link", { name: new RegExp(name) });
      expect(link).toHaveAttribute("href", href);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link.getAttribute("rel")).toContain("noopener");
    }
  });
});
