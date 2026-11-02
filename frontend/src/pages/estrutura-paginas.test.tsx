/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
    expect(screen.getByRole("heading", { name: /prepara os quatro dias/i })).toBeInTheDocument();
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

  it("usa a coluna do departamento e a grelha de três retratos da versão 02", () => {
    at(<Equipa />);
    expect(equipaOverrides).toMatch(/grid-template-columns: 270px minmax\(0,1fr\)/);
    expect(equipaOverrides).toMatch(/grid-template-columns: repeat\(3,minmax\(0,1fr\)\)/);
    expect(screen.getByRole("group", { name: "Filtrar departamentos" }).querySelectorAll("a")).toHaveLength(0);
  });

  it("filtra nos botões e no menu móvel, e Tudo repõe a equipa completa", () => {
    at(<Equipa />, '/equipa');
    const trigger = screen.getByRole('button', { name: 'Departamento Tudo' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(document.querySelectorAll('.team-department')).toHaveLength(6);

    fireEvent.click(screen.getByRole('button', { name: /^Tecnologia/ }));
    expect(document.querySelectorAll('.team-department')).toHaveLength(1);
    expect(document.querySelector('.team-department')).toHaveAttribute('id', 'tecnologia');
    expect(document.querySelectorAll('.team-member')).toHaveLength(9);
    expect(screen.getByRole('button', { name: /^Tecnologia/ })).toHaveAttribute('aria-pressed', 'true');
    expect(trigger).toHaveAccessibleName('Departamento Tecnologia');
    fireEvent.click(screen.getByRole('button', { name: /^Tudo/ }));
    expect(document.querySelectorAll('.team-department')).toHaveLength(6);
    expect(document.querySelectorAll('.team-member')).toHaveLength(46);

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const options = screen.getByRole('group', { name: 'Escolher departamento' });
    fireEvent.click(within(options).getByRole('button', { name: /^Marketing/ }));
    expect(document.querySelectorAll('.team-department')).toHaveLength(1);
    expect(document.querySelector('.team-department')).toHaveAttribute('id', 'marketing');
    expect(document.querySelectorAll('.team-member')).toHaveLength(5);
    expect(trigger).toHaveAccessibleName('Departamento Marketing');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).toHaveFocus();
    expect(screen.getByRole('status')).toHaveTextContent('A mostrar apenas Marketing.');

    fireEvent.click(trigger);
    fireEvent.keyDown(within(options).getByRole('button', { name: /^Tudo/ }), { key: 'Escape' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).toHaveFocus();
    expect(document.querySelector('.team-department')).toHaveAttribute('id', 'marketing');

    fireEvent.click(trigger);
    fireEvent.click(within(options).getByRole('button', { name: /^Tudo/ }));
    expect(document.querySelectorAll('.team-department')).toHaveLength(6);
    expect(document.querySelectorAll('.team-member')).toHaveLength(46);
    expect(trigger).toHaveAccessibleName('Departamento Tudo');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).toHaveFocus();
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
    expect(notice.textContent).toMatch(/comprova que és estudante/i);
    expect(notice.textContent).toMatch(/matrícula.*cartão de estudante.*outro documento/i);
    expect(notice.textContent).toMatch(/geral@eneiconf\.pt/);
    expect(notice.textContent).toMatch(/comprovativo na área pessoal/);
    expect(notice.textContent).not.toMatch(/assinatura digital/i);
    // «Canal oficial» no mesmo tom: compra e acompanha-se no site e na área pessoal; as dúvidas vão para o mesmo email
    const channel = screen.getByRole("heading", { name: "O bilhete fica na tua conta" }).closest("article")!;
    expect(channel.textContent).toMatch(/Compra aqui e consulta o bilhete na área pessoal/);
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
