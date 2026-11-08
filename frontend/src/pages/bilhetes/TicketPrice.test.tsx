import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getTiers } from "../../payments/api";
import type { Tier } from "../../payments/types";
import { EarlyBirdNotice, TicketPrice } from "./TicketPrice";
import { useTierPrices } from "./useTierPrices";

vi.mock("../../payments/api", () => ({ getTiers: vi.fn() }));

function tier(slug: string, price: number | null, normal: number | null = null): Tier {
  return {
    tier: slug,
    name: slug,
    price_cents: price,
    normal_price_cents: normal,
    currency: "EUR",
    is_student: false,
    sale_open: false,
    available: false,
    opens_at: null,
  };
}

function Page({ slugs }: { slugs: string[] }) {
  const prices = useTierPrices();
  return (
    <>
      <EarlyBirdNotice prices={prices} />
      {slugs.map((slug) => (
        <div key={slug} data-testid={slug}>
          <TicketPrice prices={prices} slug={slug} />
        </div>
      ))}
    </>
  );
}

beforeEach(() => {
  vi.mocked(getTiers).mockReset();
});
afterEach(cleanup);

describe("Preços na página de bilhetes (vêm do servidor)", () => {
  it("com Early Bird: o preço, o normal riscado, quanto se poupa e o aviso", async () => {
    vi.mocked(getTiers).mockResolvedValue([tier("completo", 2563, 3071), tier("geral", 4594, 5102)]);
    render(<Page slugs={["completo", "geral"]} />);

    const completo = await screen.findByTestId("completo");
    expect(completo.querySelector(".price-now .sr-only")?.textContent).toMatch(/^25,63\s€$/);
    expect(completo.querySelector("s.price-was")?.textContent).toMatch(/30,71/);
    expect(completo.querySelector(".price-save")?.textContent).toMatch(/^Poupas 5,08\s€$/);
    expect(completo.querySelector(".price-until")?.textContent).toBe("Preço Early Bird");
    expect(screen.getByRole("note")).toHaveTextContent("Preços Early Bird");
  });

  it("sem preço normal (já acabou o Early Bird): só o preço, sem riscado nem aviso", async () => {
    vi.mocked(getTiers).mockResolvedValue([tier("acesso", 1345)]);
    render(<Page slugs={["acesso"]} />);

    const acesso = await screen.findByTestId("acesso");
    await waitFor(() => expect(acesso.querySelector(".price-now")).not.toBeNull());
    expect(acesso.querySelector(".price-now .sr-only")?.textContent).toMatch(/^13,45\s€$/);
    expect(acesso.querySelector(".price-was")).toBeNull();
    expect(acesso.querySelector(".price-save")).toBeNull();
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("os cêntimos e o € ficam num elemento à parte, e os leitores de ecrã leem o valor inteiro", async () => {
    vi.mocked(getTiers).mockResolvedValue([tier("acesso", 838, 1345)]);
    render(<Page slugs={["acesso"]} />);

    const acesso = await screen.findByTestId("acesso");
    await waitFor(() => expect(acesso.querySelector(".price-cents")).not.toBeNull());
    expect(acesso.querySelector(".price-cents")?.textContent).toMatch(/^,38\s€$/);
    expect(acesso.querySelector(".price-now [aria-hidden='true']")?.textContent).toMatch(/^8,38\s€$/);
    expect(acesso.querySelector(".price-now .sr-only")?.textContent).toMatch(/^8,38\s€$/);
  });

  it("uma modalidade sem preço mostra «A confirmar» e não escreve nenhuma data", async () => {
    vi.mocked(getTiers).mockResolvedValue([tier("geral", null)]);
    const { container } = render(<Page slugs={["geral"]} />);

    await screen.findByText("A confirmar");
    expect(container.textContent).not.toMatch(/janeiro|fevereiro|\d{4}/i);
  });

  it("enquanto carrega avisa que está a carregar; se falhar, manda para o passo seguinte", async () => {
    vi.mocked(getTiers).mockRejectedValue(new Error("rede"));
    const { container } = render(<Page slugs={["acesso"]} />);

    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    await screen.findByText("Preço no passo seguinte");
    expect(screen.queryByRole("note")).toBeNull();
  });
});
