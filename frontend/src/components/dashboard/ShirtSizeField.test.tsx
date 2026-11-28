import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../../utils/http";
import type { AccountTicket } from "../../payments/types";
import ShirtSizeField from "./ShirtSizeField";

const mocks = vi.hoisted(() => ({ setShirtSize: vi.fn() }));
vi.mock("../../payments/api", () => ({ setShirtSize: mocks.setShirtSize }));

const ticket = (extra: Partial<AccountTicket> = {}): AccountTicket => ({
  reference: "ENEI-1",
  tier: "acesso",
  tier_name: "Apenas acesso",
  holder_name: "Ana",
  paid_at: null,
  shirt_applies: true,
  shirt_size: null,
  shirt_can_change: true,
  shirt_change_until: "2027-04-01T00:00:00+01:00",
  ...extra,
});

beforeEach(() => mocks.setShirtSize.mockReset());
afterEach(cleanup);

describe("tamanho da camisola na área pessoal", () => {
  it("quem ainda não escolheu vê o aviso e as opções de XS a XXL", () => {
    render(<ShirtSizeField ticket={ticket()} onSaved={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent(/ainda não escolheste o tamanho/i);
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Escolhe", "XS", "S", "M", "L", "XL", "XXL"]);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
  });

  it("escolhe, guarda e avisa o ecrã para recarregar", async () => {
    mocks.setShirtSize.mockResolvedValue(ticket({ shirt_size: "L" }));
    const onSaved = vi.fn();
    render(<ShirtSizeField ticket={ticket()} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText(/tamanho \(unissexo\)/i), { target: { value: "L" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(mocks.setShirtSize).toHaveBeenCalledWith("L");
    expect(screen.getByText("Tamanho guardado.")).toBeInTheDocument();
  });

  it("com tamanho já guardado mostra-o escolhido e só deixa guardar se mudar", () => {
    render(<ShirtSizeField ticket={ticket({ shirt_size: "M" })} onSaved={vi.fn()} />);
    expect(screen.queryByText(/ainda não escolheste/i)).toBeNull();
    expect(screen.getByLabelText(/tamanho \(unissexo\)/i)).toHaveValue("M");
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/tamanho \(unissexo\)/i), { target: { value: "XL" } });
    expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
  });

  it("depois da data só mostra o tamanho, sem opção de o mudar", () => {
    render(<ShirtSizeField ticket={ticket({ shirt_size: "S", shirt_can_change: false })} onSaved={vi.fn()} />);
    expect(screen.getByText(/tamanho s \(unissexo\)/i)).toBeInTheDocument();
    expect(screen.getByText(/a lista da camisola já fechou/i)).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Guardar" })).toBeNull();
  });

  it("409: diz que a lista fechou; rede: pede para tentar outra vez; nada fica «guardado»", async () => {
    const onSaved = vi.fn();
    render(<ShirtSizeField ticket={ticket()} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText(/tamanho \(unissexo\)/i), { target: { value: "M" } });

    mocks.setShirtSize.mockRejectedValueOnce(new ApiError(409, "closed", "closed", null));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/lista da camisola fechou/i);

    mocks.setShirtSize.mockRejectedValueOnce(new NetworkError());
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/sem ligação/i));
    expect(onSaved).not.toHaveBeenCalled();
  });
});
