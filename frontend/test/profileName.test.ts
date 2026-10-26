import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../src/utils/http";
import { NAME_MAX_LENGTH, nameErrors, profileSaveError } from "../src/utils/profileName";

// Os mesmos casos que o backend aceita e recusa em app/core/validators.py (validate_name).
describe("nameErrors: as regras do nome são as do servidor", () => {
  it.each([
    "Ana Silva",
    "  João Ção  ",
    "Zoë O'Brien-Smith",
    "李小龙",
    "A",
    "Ana 2",
    "a".repeat(NAME_MAX_LENGTH),
    "😀".repeat(NAME_MAX_LENGTH - 1) + "a", // 255 caracteres Unicode, 510 unidades UTF-16
  ])("aceita %j", (name) => {
    expect(nameErrors(name)).toEqual([]);
  });

  it.each([
    ["", "O nome não pode estar vazio."],
    ["   \t ", "O nome não pode estar vazio."],
    ["<b>Ana</b>", "O nome contém caracteres não permitidos."],
    ["Ana > Rui", "O nome contém caracteres não permitidos."],
    ["Ana\u0007", "O nome contém caracteres não permitidos."], // controlo (Cc)
    ["Ana​Silva", "O nome contém caracteres não permitidos."], // invisível (Cf)
    ["Ana", "O nome contém caracteres não permitidos."], // uso privado (Co)
    ["12345", "O nome tem de incluir pelo menos uma letra."],
    ["--- ...", "O nome tem de incluir pelo menos uma letra."],
  ])("recusa %j", (name, message) => {
    expect(nameErrors(name)).toEqual([message]);
  });

  it("junta as regras quando falham várias, como o servidor", () => {
    expect(nameErrors("<123>")).toEqual([
      "O nome contém caracteres não permitidos.",
      "O nome tem de incluir pelo menos uma letra.",
    ]);
  });

  it("conta o tamanho em caracteres, depois de tirar os espaços das pontas", () => {
    expect(nameErrors(` ${"a".repeat(NAME_MAX_LENGTH)} `)).toEqual([]);
    expect(nameErrors("a".repeat(NAME_MAX_LENGTH + 1))).toEqual(["O nome pode ter no máximo 255 caracteres."]);
  });
});

describe("profileSaveError: onde aparece cada falha de PUT /users/me", () => {
  const nameInvalid = [{ type: "name_invalid", loc: ["body", "name"], msg: "x", ctx: { rules: ["no_letter"] } }];

  it("422 do nome vai para o campo do nome", () => {
    expect(profileSaveError(new ApiError(422, "x", nameInvalid))).toEqual({
      name: ["O nome tem de incluir pelo menos uma letra."],
    });
  });

  it("422 de outro campo fica no formulário", () => {
    expect(profileSaveError(new ApiError(422, "x", [{ type: "enum", loc: ["body", "course"] }]))).toEqual({
      form: "Os dados não são válidos.",
    });
  });

  it.each([
    [new ApiError(401, "x"), "A tua sessão terminou. Entra novamente."],
    [new ApiError(403, "x"), "Confirma o teu email antes de alterares os dados."],
    [new ApiError(429, "x", undefined, "30"), "Demasiados pedidos. Tenta novamente dentro de 30 segundos."],
    [new ApiError(503, "x"), "Não foi possível guardar. Tenta novamente."],
    [new NetworkError(), "Não foi possível contactar o servidor."],
  ])("%s", (err, form) => {
    expect(profileSaveError(err)).toEqual({ form });
  });
});
