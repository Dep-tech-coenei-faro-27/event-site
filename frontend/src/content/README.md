# Conteúdo da Agenda

A Agenda e os testes leem tudo de `agenda.ts`. Para mudar o programa edita-se só esse ficheiro.

## Acrescentar, mudar ou esconder um item

```ts
{
  id: 'sex-1000-workshop-react',          // estável: não muda se o item mudar de hora ou de dia
  start: '2027-04-02T10:00',              // AAAA-MM-DDTHH:MM, hora de Lisboa
  end: '2027-04-02T11:00',                // opcional: fim (no mesmo dia, ou na madrugada do dia seguinte numa noite); sem ele o cartão mostra só a hora de início
  day: 'sexta',                           // opcional: o separador do dia a que pertence, quando não é o da data de `start` (a discoteca de sexta é à 00:00 de sábado)
  title: 'Workshop de React',
  kind: 'Workshop',                       // o tipo, em texto simples ao lado da hora («Palestra», «Refeição», «Tertúlia»…)
  category: 'workshops',                  // 'encontro' (momento) | 'palestras' | 'workshops': decide o cartão e os filtros
  tone: 'azul',                           // opcional: cor do cartão; sem ele, a da categoria (areia, azul ou lilás)
  location: 'Sala 2.14',                  // opcional; sem ele a página diz «Salas/Auditório/Local a confirmar»
  speaker: {                              // opcional; sem ele a página diz «Orador a anunciar» (ver `announce`)
    name: 'Ana Silva',
    company: 'Empresa X',
    photo: 'ana-silva.webp',              // ficheiro em src/assets/speakers/ (opcional; exige photoAlt)
    photoAlt: 'Retrato de Ana Silva',
  },
  announce: 'Convidados a anunciar',      // opcional: o texto «por anunciar» enquanto não há `speaker`
  visible: false,                         // esconde o item sem o apagar
}
```

- **`category`** manda: `encontro` desenha o cartão com o azulejo no lugar do retrato; `palestras` e `workshops` desenham-no com o retrato (o retrato por anunciar enquanto não há fotografia). O filtro «Palestras» da página inclui os workshops; «Workshops» só os workshops.
- **As horas vêm do calendário enviado pela organização a 28/10/2026**, fins incluídos. Uma noite que passa da meia-noite leva o `end` no dia seguinte (o teste exige que seja até às 06:00) e, se começar depois da meia-noite mas fizer parte do dia anterior, `day`.
- Mantém os itens por ordem de hora (o teste falha se não estiverem).
- O `id` só tem minúsculas, números e hífenes e é único. **Não o mudes** depois de existirem inscrições nesse item. A página guarda no dispositivo de cada pessoa os ids das sessões que ela guardou (`localStorage`, chave `enei-agenda-saved`); um id que desaparece da agenda deixa de contar.
- Fotografias: coloca o ficheiro em `src/assets/speakers/`, com peso máximo de 900 kB, e escreve o nome em `photo`. Sem fotografia, o cartão mostra o retrato por anunciar do protótipo (`assets/portrait-placeholder.svg`, um busto sobre azulejo). Os momentos (refeições, chegadas, convívio) não têm retrato: a coluna da imagem leva o azulejo do site (o padrão `azulejo-pattern-transparent.webp` em máscara, como nas secções e nas caixas finais).
- **Cor:** `tone: 'azul'` pinta o cartão de azul, seja qual for a categoria. Os itens do primeiro dia (quinta, 1 de abril) têm-no; o teste exige que todos os desse dia o tenham e que nenhum dos outros dias tenha cor própria.
- Os dias (`AGENDA_DAYS`) levam o texto dos botões (`tab`, `short`) e o nome por extenso (`label`); a página abre na sexta-feira e aceita `?dia=quinta|sexta|sabado|domingo`.

## O botão de inscrição, compra… (por ligar)

Cada cartão tem no canto inferior direito um espaço para uma ação. A página aceita `renderAction(item)`, que devolve o botão desse item (ou nada):

```tsx
<Agenda renderAction={(item) => (item.category === 'workshops' ? <button className="ag-action">Inscrever-me</button> : null)} />
```

O botão `.ag-action` é o antigo «Ver mais» (contorno azul sobre fundo azul transparente, 38 px de altura), só com outro texto e outra função. O pé de todos os cartões reserva a altura de um botão, por isso os cartões com e sem botão têm o mesmo tamanho.

## O que os testes garantem

`agenda.test.ts` (dados): campos obrigatórios, categoria válida, identificadores únicos, datas dentro de 1 a 4 de abril de 2027, horas válidas e por ordem, fim depois do início e no mesmo dia, fuso `Europe/Lisbon` (o desfasamento `+01:00` dá a mesma hora de parede em Lisboa em todos os itens), todos os dias com pelo menos um item visível, cada fotografia existe e tem texto alternativo, `visible: false` esconde, o texto «por confirmar» por tipo de sessão e os filtros.

`agenda-desenho.test.tsx` (página): dia por omissão e `?dia=`, separadores com teclado, filtros, pesquisa sem acentos (também pela hora de fim), estado vazio, sessões guardadas (e armazenamento estragado ou indisponível), o cartão (hora de início e fim, sem «Ver mais», o tipo sem pílula), o espaço da ação e as alturas iguais, e o texto da página.

## Correr

```
cd frontend
npx vitest run src/content
```
