/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Agenda from "./Agenda";
import Bilhetes from "./Bilhetes";
import Equipa from "./Equipa";
import InformacaoAjuda from "./InformacaoAjuda";
import Sobre from "./Sobre";

// O CSS não se importa com `?raw` nos testes (o vitest devolve-o vazio): lê-se do disco.
const css = (name: string) => readFileSync(join(import.meta.dirname, "..", name), "utf8");
const equipaOverrides = css("equipa.overrides.css");

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const at = (element: React.ReactElement, path = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>{element}</main>
    </MemoryRouter>,
  );

const headings = () => screen.getAllByRole("heading").map((h) => h.textContent);

describe("Sobre: menos história, mais informação", () => {
  it("já não tem a História, os Valores nem a Organização", () => {
    at(<Sobre />);
    const text = headings().join(" | ");
    expect(text).not.toMatch(/hist[oó]ria|pilares|quem organiza/i);
    expect(document.body.textContent).not.toMatch(/<HISTÓRIA|<VALORES|<ORGANIZAÇÃO/);
    expect(screen.getByRole("heading", { name: /porquê faro/i })).toBeInTheDocument();
  });
});

describe("Agenda: só o programa por dia", () => {
  it("já não tem os oradores, os 3 eixos nem as experiências, e mantém os quatro dias", () => {
    at(<Agenda />);
    expect(document.getElementById("oradores")).toBeNull();
    expect(document.querySelectorAll(".speaker-profile, .programme-axis, .experience-tile")).toHaveLength(0);
    expect(screen.getAllByRole("tab")).toHaveLength(4);
  });
});

describe("Equipa", () => {
  it("não tem a introdução «Equipa completa» nem o fecho «Comunidade», nem o contacto de outro domínio", () => {
    const { container } = at(<Equipa />);
    expect(container.textContent).not.toMatch(/EQUIPA_COMPLETA|COMUNIDADE/);
    expect(container.querySelector(".team-directory")).toBeNull();
    expect(container.querySelector('a[href^="mailto:"]')).toBeNull();
  });

  it("põe seis pessoas por linha a partir de 1100 px, e três entre 701 e 899 px", () => {
    expect(equipaOverrides).toMatch(/@media \(min-width: 1100px\)[^}]*\{[^}]*\.team-members\s*\{[^}]*repeat\(6,/s);
    expect(equipaOverrides).toMatch(/@media \(min-width: 701px\) and \(max-width: 899px\)[^}]*\{[^}]*repeat\(3,/s);
  });
});

describe("Contactos", () => {
  it("o email de contacto de Informação & Ajuda é geral@eneiconf.pt", () => {
    at(<InformacaoAjuda />);
    const mails = [...document.querySelectorAll('a[href^="mailto:"]')].map((a) => a.getAttribute("href"));
    expect(mails).toContain("mailto:geral@eneiconf.pt");
    expect(mails).not.toContain("mailto:geral@enei.pt");
  });
});

describe("Bilhetes", () => {
  it("diz que o bilhete de estudante pede um documento que prove que é estudante (email ou PDF na área pessoal)", () => {
    at(<Bilhetes />);
    const notice = screen.getByRole("heading", { name: /bilhete de estudante/i }).closest("article")!;
    // qualquer documento que prove que é estudante; o email e o PDF na área pessoal são os dois caminhos
    expect(notice.textContent).toMatch(/prove que és estudante/i);
    expect(notice.textContent).toMatch(/comprovativo de matrícula, o cartão de estudante ou outro documento da tua instituição/i);
    expect(notice.textContent).toMatch(/geral@eneiconf\.pt/);
    expect(notice.textContent).toMatch(/PDF na tua área pessoal/);
    expect(notice.textContent).not.toMatch(/assinatura digital/i);
    // «Canal oficial» no mesmo tom: compra e acompanha-se no site e na área pessoal; as dúvidas vão para o mesmo email
    const channel = screen.getByRole("heading", { name: "Canal oficial" }).closest("article")!;
    expect(channel.textContent).toMatch(/Compra e acompanha o teu bilhete aqui no site e na tua área pessoal/);
    expect(channel.textContent).toMatch(/geral@eneiconf\.pt/);
    expect(channel.textContent).not.toMatch(/apenas/i);
  });
});

describe("Bilhetes: a lista «Prepara a tua inscrição» só pede o que o site recolhe", () => {
  it("não pede Instituição, Curso nem Necessidades alimentares (nada as recolhe)", () => {
    at(<Bilhetes />);
    expect(screen.queryByText("Instituição")).toBeNull();
    expect(screen.queryByText("Curso")).toBeNull();
    expect(screen.queryByText(/necessidades alimentares/i)).toBeNull();
    expect(screen.queryByRole("heading", { name: "Participação" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Dados pessoais" })).toBeInTheDocument();
  });
});
