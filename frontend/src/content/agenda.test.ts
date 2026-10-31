/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";
import { AGENDA, AGENDA_DAYS, AGENDA_TIMEZONE, AGENDA_UTC_OFFSET, cardOf, endOf, itemsOfDay, matchesFilter, pendingLocation, pendingSpeaker, timeOf, timeRange, type AgendaItem } from "./agenda";

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
      expect(item.kind.trim(), item.id).not.toBe("");
      expect(["encontro", "palestras", "workshops"], item.id).toContain(item.category);
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
      { id: "b", start: "2027-04-01T18:00", title: "B", kind: "x", category: "encontro" },
      { id: "a", start: "2027-04-01T14:00", title: "A", kind: "x", category: "encontro" },
      { id: "h", start: "2027-04-01T15:00", title: "H", kind: "x", category: "encontro", visible: false },
      { id: "o", start: "2027-04-02T10:00", title: "O", kind: "x", category: "encontro" },
    ];
    const result = itemsOfDay(items, AGENDA_DAYS[0]);
    expect(result.map((i) => i.id)).toEqual(["a", "b"]);
    expect(timeOf(result[0])).toBe("14:00");
  });

  it("cada dia tem o texto dos botões: etiqueta, número e nome por extenso", () => {
    for (const day of AGENDA_DAYS) {
      expect(day.short, day.key).toBe(`${Number(day.date.slice(8, 10))} Abr`);
      expect(day.tab, day.key).toBe(day.tab.toUpperCase());
      expect(day.label, day.key).toMatch(new RegExp(`, ${Number(day.date.slice(8, 10))} abril$`));
    }
  });

  it("a hora de fim, quando existe, é depois do início e no mesmo dia; só as noites acabam na madrugada do dia seguinte (até às 06:00)", () => {
    for (const item of AGENDA) {
      if (!item.end) continue;
      expect(START.test(item.end), item.id).toBe(true);
      expect(item.end > item.start, `${item.id}: o fim tem de ser depois do início`).toBe(true);
      if (item.end.slice(0, 10) !== item.start.slice(0, 10)) {
        const next = new Date(`${item.start.slice(0, 10)}T00:00:00Z`);
        next.setUTCDate(next.getUTCDate() + 1);
        expect(item.end.slice(0, 10), `${item.id}: o fim só pode ser no dia seguinte`).toBe(next.toISOString().slice(0, 10));
        expect(item.end.slice(11) <= "06:00", `${item.id}: uma noite acaba até às 06:00`).toBe(true);
      }
    }
  });

  it("só o último item de um dia pode não ter fim", () => {
    for (const day of AGENDA_DAYS) {
      const ofDay = itemsOfDay(AGENDA, day);
      expect(ofDay.slice(0, -1).every((i) => i.end), `${day.key}: só o último item do dia pode estar sem fim`).toBe(true);
    }
  });

  it("`day` põe um item no separador desse dia, mesmo começando depois da meia-noite (a discoteca de sexta é à 00:00 de sábado)", () => {
    const disco = AGENDA.find((i) => i.id === "sex-0000-discoteca")!;
    expect(disco.start.slice(0, 10)).toBe("2027-04-03");
    const [, sexta, sabado] = AGENDA_DAYS;
    expect(itemsOfDay(AGENDA, sexta).at(-1)).toBe(disco);
    expect(itemsOfDay(AGENDA, sabado).map((i) => i.id)).not.toContain(disco.id);
    // sem `day`, o item fica no dia da sua data
    expect(itemsOfDay([{ ...disco, day: undefined }], sabado)).toHaveLength(1);
  });

  it("uma noite que passa da meia-noite mostra «22:00 – 04:00»", () => {
    const arraial = AGENDA.find((i) => i.id === "qui-2200-arraial")!;
    expect(timeRange(arraial)).toBe("22:00 – 04:00");
  });

  it("`timeRange` dá «11:00 – 12:00», ou só a hora de início sem fim", () => {
    const base = { id: "x", title: "X", kind: "k", category: "encontro" as const };
    expect(timeRange({ ...base, start: "2027-04-02T11:00", end: "2027-04-02T12:00" })).toBe("11:00 – 12:00");
    expect(timeRange({ ...base, start: "2027-04-02T11:00" })).toBe("11:00");
    expect(endOf({ ...base, start: "2027-04-02T11:00" })).toBeNull();
  });

  it("todos os itens do primeiro dia são azuis (`tone: 'azul'`) e nenhum dos outros dias tem cor própria", () => {
    const [first, ...others] = AGENDA_DAYS;
    for (const item of itemsOfDay(AGENDA, first)) expect(item.tone, item.id).toBe("azul");
    for (const day of others) for (const item of itemsOfDay(AGENDA, day)) expect(item.tone, item.id).toBeUndefined();
  });

  it("só os momentos (`encontro`) são cartões de momento; palestras e workshops levam retrato", () => {
    for (const item of AGENDA) expect(cardOf(item), item.id).toBe(item.category === "encontro" ? "moment" : "speaker");
  });

  it("o texto «por confirmar» depende do tipo de sessão, e `announce` e `location` mandam quando existem", () => {
    const base = { id: "x", start: "2027-04-02T10:00", title: "X", kind: "Palestra" };
    expect(pendingLocation({ ...base, category: "workshops" })).toBe("Salas a confirmar");
    expect(pendingLocation({ ...base, category: "palestras" })).toBe("Auditório a confirmar");
    expect(pendingLocation({ ...base, category: "palestras", kind: "Tertúlia" })).toBe("Local a confirmar");
    expect(pendingLocation({ ...base, category: "encontro" })).toBe("Local a confirmar");
    expect(pendingSpeaker({ ...base, category: "workshops" })).toBe("Oradores e facilitadores a anunciar");
    expect(pendingSpeaker({ ...base, category: "palestras", kind: "Tertúlia" })).toBe("Convidados a anunciar");
    expect(pendingSpeaker({ ...base, category: "palestras" })).toBe("Orador a anunciar");
    expect(pendingSpeaker({ ...base, category: "palestras", announce: "Keynote surpresa" })).toBe("Keynote surpresa");
  });

  it("o filtro «Palestras» inclui os workshops; «Workshops» só os workshops; «Guardados» só os guardados", () => {
    const mk = (id: string, category: AgendaItem["category"]): AgendaItem => ({ id, start: "2027-04-02T10:00", title: id, kind: "k", category });
    const [m, p, w] = [mk("m", "encontro"), mk("p", "palestras"), mk("w", "workshops")];
    const saved = new Set(["m"]);
    const of = (f: Parameters<typeof matchesFilter>[1]) => [m, p, w].filter((i) => matchesFilter(i, f, saved)).map((i) => i.id);
    expect(of("all")).toEqual(["m", "p", "w"]);
    expect(of("palestras")).toEqual(["p", "w"]);
    expect(of("workshops")).toEqual(["w"]);
    expect(of("saved")).toEqual(["m"]);
  });
});
