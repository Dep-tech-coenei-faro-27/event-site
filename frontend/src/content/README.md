# Conteúdo da Agenda

A Agenda e os testes leem tudo de `agenda.ts`. Para mudar o programa edita-se só esse ficheiro.

## Acrescentar, mudar ou esconder um item

```ts
{
  id: 'sex-1000-workshop-react',          // estável: não muda se o item mudar de hora ou de dia
  start: '2027-04-02T10:00',              // AAAA-MM-DDTHH:MM, hora de Lisboa
  title: 'Workshop de React',
  tag: { label: 'Workshop', tone: 'coral' },   // sand | cyan | teal | coral | periwinkle
  location: 'Sala 2.14',                  // opcional
  speaker: {                              // opcional
    name: 'Ana Silva',
    company: 'Empresa X',
    photo: 'ana-silva.webp',              // ficheiro em src/assets/speakers/ (opcional; exige photoAlt)
    photoAlt: 'Retrato de Ana Silva',
  },
  visible: false,                         // esconde o item sem o apagar
}
```

- Mantém os itens por ordem de hora (o teste falha se não estiverem).
- O `id` só tem minúsculas, números e hífenes e é único. **Não o mudes** depois de existirem inscrições nesse item.
- Fotografias: coloca o ficheiro em `src/assets/speakers/`, com peso máximo de 900 kB, e escreve o nome em `photo`.

## O que os testes garantem (`agenda.test.ts`)

Campos obrigatórios, identificadores únicos, datas dentro de 1 a 4 de abril de 2027, horas válidas e por ordem, fuso
`Europe/Lisbon` (o desfasamento `+01:00` dá a mesma hora de parede em Lisboa em todos os itens), todos os dias com
pelo menos um item visível, cada fotografia existe e tem texto alternativo, e os itens com `visible: false` não se desenham.

## Correr

```
cd frontend
npx vitest run src/content
```
