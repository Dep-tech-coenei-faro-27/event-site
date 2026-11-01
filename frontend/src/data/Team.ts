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
    eyebrow: "Direção",
    title: "Coordenação do encontro",
    description: "Estratégia, gestão e representação do ENEI 2027.",
    members: [
      dir("David Gonçalves", "david-goncalves", "Presidente"),
      dir("Diogo Almeida", "diogo-almeida", "Vice-Presidente"),
      dir("David Rodrigues", "david-rodrigues", "Tesoureiro"),
      dir("Afonso Bitoque", "afonso-bitoque", "Administrador"),
      dir("Raquel Nunes", "raquel", "Coordenadora LEI"),
      dir("Afonso", "afonso", "Coordenador LESTI"),
      dir("Rian Sabarense", "ryan", "Coordenador EEC"),
      dir("David Silvestre", "david-silvestre", "Secretário"),
      { name: "Carolina Pires", role: "Secretária" },
    ],
  },
  {
    id: "marketing",
    label: "Marketing",
    eyebrow: "Marketing",
    title: "Marca e comunicação",
    description: "Conteúdos, identidade e comunicação do encontro.",
    members: [
      { name: "Hugo Pinto" },
      dir("João Pedro", "joao"),
      { name: "Inês Campelo" },
      { name: "Afonso Amador" },
      { name: "Bruno Horta" },
    ],
  },
  {
    id: "atividades",
    label: "Atividades",
    eyebrow: "Atividades",
    title: "Programa e experiências",
    description: "Conteúdo, comunidade e momentos que dão vida ao evento.",
    members: [
      dir("Leonardo Cantachini", "leonardo-cantachini", "Diretor"),
      { name: "Afonso Francisco" },
      { name: "Simão Reis" },
      { name: "Rodrigo Silva" },
      dir("Rodrigo Linhas", "rodrigo-linhas"),
      dir("Gonçalo Santinho", "goncalo-santinho"),
      dir("Pedro Salgueiro", "pedro-salgueiro"),
    ],
  },
  {
    id: "tecnologia",
    label: "Tecnologia",
    eyebrow: "Tecnologia",
    title: "Plataforma e infraestrutura",
    description: "Produto digital, sistemas e experiência tecnológica.",
    members: [
      dir("Francisco Melo", "francisco-melo", "Diretor"),
      dir("Martim Neves", "martim-neves"),
      dir("Diogo Carvalho", "diogo-carvalho"),
      dir("Leo Souza", "leo-souza"),
      dir("Guilherme Guerreiro", "guilherme-guerreiro"),
      dir("Miguel Alvito", "miguel-alvito"),
      { name: "Gabriel Vaz" },
      dir("Alexandre Guerreiro", "alexandre-guerreiro"),
      dir("Diogo Almeida", "diogo-almeida2"),
    ],
  },
  {
    id: "comercial",
    label: "Comercial",
    eyebrow: "Comercial",
    title: "Parcerias e relações",
    description: "Patrocínios e ligação ao ecossistema empresarial.",
    members: [
      dir("Mohammed Rohaim", "mohammed-rohaim", "Diretor"),
      dir("Matilde Saldanha", "matilde-saldanha"),
      { name: "Márcio" },
      { name: "José Tico" },
      { name: "Duarte Cunha" },
      { name: "Tarsila Krigger" },
    ],
  },
  {
    id: "logistica",
    label: "Logística",
    eyebrow: "Logística",
    title: "Recinto e operação",
    description: "Acolhimento, mobilidade e execução no terreno.",
    members: [
      dir("Ricardo Vicente", "ricardo-vicente"),
      dir("João Batista", "joao-baptista"),
      dir("Francisco Afonso", "francisco-afonso"),
      dir("Tiago Lino", "tiago-lino"),
      dir("Lara", "lara"),
      { name: "Rafael Simão" },
      dir("Guilherme Bacoco", "guilherme-bacoco"),
      dir("Beatriz Mateia", "beatriz-mateia"),
      dir("Bárbara Pereira", "barbara-pereira", "Diretora"),
      dir("Bruno Brás", "bruno-bras"),
    ],
  },
];