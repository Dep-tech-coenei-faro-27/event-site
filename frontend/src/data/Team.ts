export type Member = { name: string; role?: string; photo?: string };

export type Department = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  /** Nome do departamento, usado na legenda "Cargo · Departamento" */
  label: string;
  members: Member[];
};

const dir = (name: string, photo: string, role?: string): Member => ({ name, photo, role });

export const departments: Department[] = [
  {
    id: "direcao",
    label: "Direção",
    eyebrow: "01 · Direção",
    title: "Coordenação do encontro",
    description: "Estratégia, gestão e representação do ENEI 2027.",
    members: [
      dir("David Gonçalves", "david-goncalves", "Presidente"),
      dir("Diogo Almeida", "diogo-almeida", "Vice-Presidente"),
      dir("Afonso Bitoque", "afonso-bitoque", "Administrador"),
      dir("David Rodrigues", "david-rodrigues", "Tesoureiro"),
      dir("Raquel", "raquel", "Coordenadora LEI"),
      dir("Ryan", "ryan", "Coordenador EEC"),
      dir("Afonso", "afonso", "Coordenador LESTI"),
      dir("David Silvestre", "david-silvestre", "Secretário"),
    ],
  },
  {
    id: "marketing",
    label: "Marketing",
    eyebrow: "02 · Marketing",
    title: "Marca e comunicação",
    description: "Conteúdos, identidade e comunicação do encontro.",
    members: [{ name: "Jorge", role: "Diretor" }, { name: "Inês" }],
  },
  {
    id: "atividades",
    label: "Atividades",
    eyebrow: "03 · Atividades",
    title: "Programa e experiências",
    description: "Conteúdo, comunidade e momentos que dão vida ao evento.",
    members: [
      dir("Leonardo Cantachini", "leonardo-cantachini", "Diretor"),
      { name: "Pedro Salgueiro" },
      { name: "Gonçalo Santinho" },
      { name: "Rodrigo Linhas" },
      dir("Francisco Afonso", "francisco-afonso"),
      { name: "Simão Reis" },
      { name: "Rodrigo Silva" },
    ],
  },
  {
    id: "tecnologia",
    label: "Tecnologia",
    eyebrow: "04 · Tecnologia",
    title: "Plataforma e infraestrutura",
    description: "Produto digital, sistemas e experiência tecnológica.",
    members: [
      dir("Francisco Melo", "francisco-melo", "Diretor"),
      dir("Miguel Alvito", "miguel-alvito"),
      { name: "Martim Neves" },
      { name: "Guilherme Silvestre" },
      dir("Diogo Carvalho", "diogo-carvalho"),
      dir("Diogo Almeida", "diogo-almeida2"),
      { name: "Gabriel Vaz" },
    ],
  },
  {
    id: "comercial",
    label: "Comercial",
    eyebrow: "05 · Comercial",
    title: "Parcerias e relações",
    description: "Patrocínios e ligação ao ecossistema empresarial.",
    members: [
      dir("Mohammed Rohaim", "mohammed-rohaim", "Diretor"),
      { name: "João Teixeira" },
      { name: "Duarte Cunha" },
      { name: "José Tico" },
      { name: "Matilde Saldanha" },
      { name: "Tarsila Krieger" },
      { name: "Márcio" },
    ],
  },
  {
    id: "logistica",
    label: "Logística",
    eyebrow: "06 · Logística",
    title: "Recinto e operação",
    description: "Acolhimento, mobilidade e execução no terreno.",
    members: [
      dir("Bárbara Pereira", "barbara-pereira", "Diretora"),
      dir("Beatriz Mateia", "beatriz-mateia"),
      dir("Guilherme Bacoco", "guilherme-bacoco"),
      dir("Francisco Afonso", "francisco-afonso"),
      dir("João Baptista", "joao-baptista"),
      dir("Lara", "lara"),
      dir("Ricardo Vicente", "ricardo-vicente"),
      dir("Tiago Lino", "tiago-lino"),
      dir("Bruno Brás", "bruno-bras"),
    ],
  },
];