// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearReference, loadReference, saveReference } from "./reference";

describe("referência do pagamento em curso", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("guarda, lê e apaga", () => {
    expect(loadReference()).toBeNull();
    saveReference("ENEI-ABC123");
    expect(loadReference()).toBe("ENEI-ABC123");
    clearReference();
    expect(loadReference()).toBeNull();
  });

  it("apagar com `only` não apaga a referência de outro pagamento", () => {
    saveReference("ENEI-NOVA");
    clearReference("ENEI-VELHA");
    expect(loadReference()).toBe("ENEI-NOVA");
    clearReference("ENEI-NOVA");
    expect(loadReference()).toBeNull();
  });

  it("com o armazenamento bloqueado nada rebenta", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    expect(() => saveReference("ENEI-X")).not.toThrow();
    expect(loadReference()).toBeNull();
    expect(() => clearReference()).not.toThrow();
  });
});
