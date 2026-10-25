/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";
import { AGENDA, AGENDA_DAYS, AGENDA_TIMEZONE, AGENDA_UTC_OFFSET, itemsOfDay, timeOf, type AgendaItem } from "./agenda";

// Os ficheiros de `assets/speakers/` (o nome do ficheiro é o que o item guarda em `speaker.photo`).
const speakerFiles = Object.keys(import.meta.glob("../assets/speakers/*.{webp,jpg,jpeg,png,svg}")).map((p) => p.split("/").pop());

const START = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;
const EVENT_DAYS = ["2027-04-01", "2027-04-02", "2027-04-03", "2027-04-04"];

describe("dados da agenda (esquema)", () => {
  it("os quatro dias do evento, 1 a 4 de abril de 2027, cada um com o seu separador", () => {
    expect(AGENDA_DAYS.map((d) => d.date)).toEqual(EVENT_DAYS);
    expect(new Set(AGENDA_DAYS.map((d) => d.key)).size).toBe(4);
  });

  it("cada item tem identificador, hora, título e etiqueta; os identificadores são únicos e estáveis (só minúsculas, números e hífenes)", () => {
    const ids = AGENDA.map((i) => i.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const item of AGENDA) {
      expect(item.id, item.title).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
      expect(item.title.trim(), item.id).not.toBe("");
      expect(item.tag.label.trim(), item.id).not.toBe("");
      expect(["sand", "cyan", "teal", "coral", "periwinkle"], item.id).toContain(item.tag.tone);
    }
  });

  it("as horas são `AAAA-MM-DDTHH:MM` válidas, dentro dos dias do evento e por ordem", () => {
    let previous = "";
    for (const item of AGENDA) {
      const m = START.exec(item.start);
      expect(m, `${item.id}: ${item.start}`).not.toBeNull();
      expect(EVENT_DAYS, item.id).toContain(item.start.slice(0, 10));
      expect(Number(m![4]), item.id).toBeLessThan(24);
      expect(Number(m![5]), item.id).toBeLessThan(60);
      expect(item.start >= previous, `${item.id} está fora de ordem`).toBe(true);
      previous = item.start;
    }
  });

  it("o fuso é Europe/Lisbon: o desfasamento declarado dá a mesma hora de parede em Lisboa em todos os itens", () => {
    expect(AGENDA_TIMEZONE).toBe("Europe/Lisbon");
    const fmt = new Intl.DateTimeFormat("sv-SE", { timeZone: AGENDA_TIMEZONE, dateStyle: "short", timeStyle: "short" });
    for (const item of AGENDA) {
      const instant = new Date(`${item.start}:00${AGENDA_UTC_OFFSET}`);
      expect(fmt.format(instant).replace(" ", "T"), item.id).toBe(item.start);
    }
  });

  it("cada dia tem pelo menos um item visível", () => {
    for (const day of AGENDA_DAYS) expect(itemsOfDay(AGENDA, day).length, day.key).toBeGreaterThan(0);
  });

  it("cada fotografia de orador existe em assets/speakers/ e tem texto alternativo; sem nome em branco", () => {
    for (const item of AGENDA.filter((i) => i.speaker)) {
      const s = item.speaker!;
      expect(s.name.trim(), item.id).not.toBe("");
      if (s.photo) {
        expect(speakerFiles, `${item.id}: ${s.photo} não existe em src/assets/speakers/`).toContain(s.photo);
        expect((s.photoAlt ?? "").trim(), `${item.id}: falta o texto alternativo da fotografia`).not.toBe("");
      }
    }
  });

  it("`itemsOfDay` esconde os itens com visible:false e mantém a ordem; `timeOf` dá HH:MM", () => {
    const items: AgendaItem[] = [
      { id: "b", start: "2027-04-01T18:00", title: "B", tag: { label: "x", tone: "cyan" } },
      { id: "a", start: "2027-04-01T14:00", title: "A", tag: { label: "x", tone: "cyan" } },
      { id: "h", start: "2027-04-01T15:00", title: "H", tag: { label: "x", tone: "cyan" }, visible: false },
      { id: "o", start: "2027-04-02T10:00", title: "O", tag: { label: "x", tone: "cyan" } },
    ];
    const result = itemsOfDay(items, AGENDA_DAYS[0]);
    expect(result.map((i) => i.id)).toEqual(["a", "b"]);
    expect(timeOf(result[0])).toBe("14:00");
  });
});
