import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Profile from "../src/pages/Profile";
import type { User } from "../src/utils/authContextValue";
import { ApiError, NetworkError } from "../src/utils/http";
import {
  STUDENT_PROOF_MAX_BYTES,
  studentProofError,
  studentProofFileError,
  studentStatus,
} from "../src/utils/studentProof";

const mocks = vi.hoisted(() => ({
  http: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock("../src/utils/http", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/utils/http")>()),
  http: mocks.http,
}));
vi.mock("../src/utils/users", () => ({ getMe: mocks.getMe }));
vi.mock("../src/utils/useAuth", () => ({
  useAuth: () => ({ user: null, loading: false, refresh: vi.fn(), logout: vi.fn() }),
}));

const user = (status: User["student_verification_status"]): User => ({
  id: 3,
  name: "Francisco Melo",
  email: "francisco@gmail.com",
  role: "user",
  is_verified: true,
  course: null,
  institution: null,
  qr_code: null,
  student_verification_status: status,
});

const pdf = (bytes = 10, name = "comprovativo.pdf") =>
  new File([new Uint8Array(bytes)], name, { type: "application/pdf" });

function Where() {
  const { pathname, search } = useLocation();
  return <div data-testid="where">{pathname + search}</div>;
}

function renderProfile() {
  return render(
    <MemoryRouter initialEntries={["/perfil"]}>
      <Routes>
        <Route path="/perfil" element={<Profile />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

const section = async () =>
  within(
    (await screen.findByRole("heading", { name: "Comprovativo de estudante" })).closest("article") as HTMLElement,
  );

/** Abre o perfil e devolve a secção do comprovativo. */
async function openProfile() {
  renderProfile();
  return section();
}

async function chooseAndSend(file: File = pdf(), panel?: ReturnType<typeof within>) {
  panel ??= await openProfile();
  fireEvent.change(panel.getByLabelText("Ficheiro do comprovativo"), { target: { files: [file] } });
  fireEvent.click(panel.getByRole("button", { name: "Enviar comprovativo" }));
  return panel;
}

beforeEach(() => {
  mocks.http.mockReset();
  mocks.getMe.mockReset().mockResolvedValue(user("none"));
});
afterEach(cleanup);

describe("estado de estudante", () => {
  it("«pending» (nome antigo), em falta ou desconhecido conta como «none»", () => {
    expect(studentStatus("pending")).toBe("none");
    expect(studentStatus(undefined)).toBe("none");
    expect(studentStatus("outra")).toBe("none");
    expect(studentStatus("rejected")).toBe("rejected");
  });

  it("o ficheiro é verificado antes de enviar: falta, vazio, mais de 1 MB, tipo errado", () => {
    expect(studentProofFileError(null)).toMatch(/escolhe/i);
    expect(studentProofFileError(pdf(0))).toMatch(/vazio/i);
    expect(studentProofFileError(pdf(STUDENT_PROOF_MAX_BYTES + 1))).toMatch(/1 MB/);
    expect(studentProofFileError(pdf(10, "comprovativo.docx"))).toMatch(/PDF, JPG ou PNG/);
    expect(studentProofFileError(pdf(STUDENT_PROOF_MAX_BYTES))).toBeNull();
    expect(studentProofFileError(pdf(10, "FOTO.JPEG"))).toBeNull();
  });

  it("cada resposta de erro da API tem o seu texto em português", () => {
    const api = (status: number, detail = "x", retryAfter: string | null = null) =>
      studentProofError(new ApiError(status, detail, detail, retryAfter));
    expect(studentProofError(new NetworkError()).message).toMatch(/sem ligação/i);
    expect(api(401)).toMatchObject({ sessionEnded: true });
    expect(api(409, "The account is already a verified student")).toMatchObject({
      stale: true,
      message: expect.stringMatching(/já está verificada/),
    });
    expect(api(409, "A proof is already waiting for a decision")).toMatchObject({
      stale: true,
      message: expect.stringMatching(/à espera/),
    });
    expect(api(413).message).toMatch(/1 MB/);
    expect(api(415).message).toMatch(/PDF, JPG ou PNG/);
    expect(api(422).message).toMatch(/vazio/);
    expect(api(429, "x", "120").message).toMatch(/2 minutos/);
    expect(api(500).message).toMatch(/servidor/);
  });
});

describe("perfil: comprovativo de estudante", () => {
  it("sem comprovativo mostra as regras e o envio", async () => {
    const panel = await openProfile();
    expect(panel.getByText(/ano letivo 2026\/2027/)).toBeInTheDocument();
    expect(panel.getByLabelText("Ficheiro do comprovativo")).toHaveAttribute("accept", expect.stringContaining(".pdf"));
    expect(panel.getByRole("button", { name: "Enviar comprovativo" })).toBeEnabled();
  });

  it("a conta antiga com «pending» também pode enviar", async () => {
    mocks.getMe.mockResolvedValue(user("pending"));
    const panel = await openProfile();
    expect(panel.getByRole("button", { name: "Enviar comprovativo" })).toBeInTheDocument();
  });

  it("sem ficheiro ou com mais de 1 MB avisa junto ao campo e não faz pedido", async () => {
    const panel = await openProfile();
    fireEvent.click(panel.getByRole("button", { name: "Enviar comprovativo" }));
    expect(panel.getByRole("alert")).toHaveTextContent(/escolhe o ficheiro/i);
    expect(panel.getByLabelText("Ficheiro do comprovativo")).toHaveAttribute("aria-invalid", "true");

    await chooseAndSend(pdf(STUDENT_PROOF_MAX_BYTES + 1), panel);
    expect(panel.getByRole("alert")).toHaveTextContent(/1 MB/);
    expect(mocks.http).not.toHaveBeenCalled();
  });

  it("envia o ficheiro em multipart e, enquanto espera, mostra «A enviar…» sem deixar repetir", async () => {
    let answer: (value: unknown) => void = () => {};
    mocks.http.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    const file = pdf();
    const panel = await chooseAndSend(file);

    const button = panel.getByRole("button", { name: "A enviar…" });
    expect(button).toBeDisabled();
    expect(mocks.http).toHaveBeenCalledTimes(1);
    const [path, options] = mocks.http.mock.calls[0];
    expect(path).toBe("/users/me/student-proof");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect((options.body as FormData).get("file")).toBe(file);

    await act(async () => answer({ status: "submitted" }));
    expect(panel.getByText("Em revisão")).toBeInTheDocument();
  });

  it("aprovado na hora: fica verificado, anuncia-o e deixa de pedir o ficheiro", async () => {
    mocks.http.mockResolvedValue({ status: "verified" });
    const panel = await chooseAndSend();

    expect(await panel.findByText("Verificado")).toBeInTheDocument();
    expect(panel.getByText(/comprovativo aceite/i)).toHaveAttribute("aria-live", "polite");
    expect(panel.queryByLabelText("Ficheiro do comprovativo")).toBeNull();
    expect(panel.getByRole("link", { name: /comprar um bilhete de estudante/i })).toHaveAttribute(
      "href",
      "/bilhetes/checkout",
    );
  });

  it("à espera de uma pessoa: mostra «Em revisão» e anuncia o envio", async () => {
    mocks.http.mockResolvedValue({ status: "submitted" });
    const panel = await chooseAndSend();

    expect(await panel.findByText("Em revisão")).toBeInTheDocument();
    expect(panel.getByText(/comprovativo enviado/i)).toHaveAttribute("aria-live", "polite");
    expect(panel.queryByRole("button", { name: "Enviar comprovativo" })).toBeNull();
  });

  it.each([
    ["sem rede", new NetworkError(), /sem ligação/i],
    ["erro do servidor (5xx)", new ApiError(503, "x"), /servidor não conseguiu/i],
    ["tipo recusado (415)", new ApiError(415, "x"), /PDF, JPG ou PNG/],
    ["demasiados pedidos (429)", new ApiError(429, "x", "x", "30"), /30 segundos/],
  ])("falha (%s): avisa e deixa tentar outra vez", async (_case, error, text) => {
    mocks.http.mockRejectedValue(error);
    const panel = await chooseAndSend();

    expect(await panel.findByRole("alert")).toHaveTextContent(text);
    expect(panel.getByRole("button", { name: "Enviar comprovativo" })).toBeEnabled();
  });

  it("sessão terminada (401): leva ao login", async () => {
    mocks.http.mockRejectedValue(new ApiError(401, "x"));
    await chooseAndSend();
    expect(await screen.findByTestId("where")).toHaveTextContent("/conta?sessao=terminada");
  });

  it("409 (o estado mudou noutro lado): volta a ler a conta e mostra o estado novo", async () => {
    mocks.http.mockRejectedValue(new ApiError(409, "x", "A proof is already waiting for a decision"));
    await chooseAndSend();
    mocks.getMe.mockResolvedValue(user("submitted"));

    await waitFor(() => expect(mocks.getMe).toHaveBeenCalledTimes(2));
    expect(await (await section()).findByText("Em revisão")).toBeInTheDocument();
  });

  it("em revisão: diz que espera por uma pessoa e não deixa enviar outro", async () => {
    mocks.getMe.mockResolvedValue(user("submitted"));
    const panel = await openProfile();
    expect(panel.getByText("Em revisão")).toBeInTheDocument();
    expect(panel.getByText(/alguém da organização vai revê-lo/i)).toBeInTheDocument();
    expect(panel.queryByLabelText("Ficheiro do comprovativo")).toBeNull();
  });

  it("recusado: explica porquê, dá o contacto e deixa enviar outro", async () => {
    mocks.getMe.mockResolvedValue(user("rejected"));
    const panel = await openProfile();
    expect(panel.getByText("Recusado")).toBeInTheDocument();
    expect(panel.getByRole("heading", { name: /porque não tens o preço de estudante/i })).toBeInTheDocument();
    expect(panel.getByRole("link", { name: "geral@enei.pt" })).toHaveAttribute("href", "mailto:geral@enei.pt");
    expect(panel.getByText(/nome igual ao da conta/i)).toBeInTheDocument();
    expect(panel.getByRole("button", { name: "Enviar comprovativo" })).toBeEnabled();
  });

  it("verificado (por email de aluno ou comprovativo): sem envio", async () => {
    mocks.getMe.mockResolvedValue(user("verified"));
    const panel = await openProfile();
    expect(panel.getByText("Verificado")).toBeInTheDocument();
    expect(panel.queryByRole("button", { name: "Enviar comprovativo" })).toBeNull();
  });
});
