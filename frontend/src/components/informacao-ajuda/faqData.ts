export type Category = 'inscricoes' | 'programa' | 'alojamento' | 'transporte' | 'parcerias';

export const CATEGORIES: { id: 'todos' | Category; label: string }[] = [
  { id: 'todos', label: 'Todas' },
  { id: 'inscricoes', label: 'Inscrições' },
  { id: 'programa', label: 'Programa' },
  { id: 'alojamento', label: 'Alojamento' },
  { id: 'transporte', label: 'Transporte' },
  { id: 'parcerias', label: 'Parcerias' },
];

export const FAQ_DATA: { id: number; category: Category; question: string; answer: string }[] = [
  { id: 1, category: 'inscricoes', question: 'Como compro o bilhete e concluo a inscrição?', answer: 'Acede à página de Bilhetes, compara as modalidades, escolhe a opção adequada e entra ou cria a tua conta. A inscrição fica concluída depois de preencheres os dados necessários e receberes a confirmação do processo.' },
  { id: 2, category: 'inscricoes', question: 'O evento é pago e quanto custa o bilhete?', answer: 'O ENEI tem diferentes modalidades de bilhete. Os preços, inclusões e condições em vigor são apresentados na página de Bilhetes antes de iniciares a compra.' },
  { id: 3, category: 'inscricoes', question: 'O evento inclui refeições?', answer: 'As modalidades Acesso + refeições e Experiência completa incluem refeições. A modalidade Apenas acesso não inclui refeições; confirma sempre o detalhe da opção escolhida.' },
  { id: 4, category: 'inscricoes', question: 'Recebo certificado de participação?', answer: 'Sim. Serão emitidos certificados de participação aos participantes elegíveis depois do evento. As instruções para os obter serão comunicadas através da conta e dos canais oficiais.' },
  { id: 5, category: 'inscricoes', question: 'Como posso corrigir ou eliminar os meus dados?', answer: 'Podes atualizar os dados disponíveis na tua conta ou pedir acesso, correção ou eliminação através de coenei@aaualg.pt.' },
  { id: 6, category: 'inscricoes', question: 'Onde encontro documentos e informações oficiais?', answer: 'A agenda, as condições dos bilhetes, os documentos legais e as informações logísticas são atualizados neste website à medida que ficam confirmados. Em caso de dúvida, utiliza os contactos oficiais apresentados nesta página.' },
  { id: 7, category: 'programa', question: 'Onde consulto a agenda?', answer: 'A página Agenda reúne os quatro dias do programa, os horários, as categorias de atividade e os oradores confirmados.' },
  { id: 8, category: 'programa', question: 'Quais palestras e workshops estarão disponíveis?', answer: 'O programa inclui blocos de palestras e workshops técnicos. Os temas, oradores, salas e eventuais limites de lotação serão publicados na Agenda à medida que forem confirmados.' },
  { id: 9, category: 'programa', question: 'Que tipos de atividades fazem parte do ENEI?', answer: 'O programa combina competições técnicas, palestras, workshops, networking, atividades recreativas e uma experiência de gamificação.' },
  { id: 10, category: 'programa', question: 'Que atividades sociais existem?', answer: 'O programa prevê momentos de integração, arraial académico, tertúlias, atividades noturnas e uma experiência junto à praia, além dos momentos de networking ao longo do encontro.' },
  { id: 11, category: 'programa', question: 'O que é a gamificação do evento?', answer: 'A plataforma digital utiliza badges, moedas virtuais e recompensas pela interação com oradores, espaços e parceiros.' },
  { id: 12, category: 'alojamento', question: 'O bilhete inclui alojamento?', answer: 'A modalidade Experiência completa inclui alojamento coletivo. Compara todas as inclusões na página de Bilhetes.' },
  { id: 13, category: 'alojamento', question: 'Onde fico alojado durante o evento?', answer: 'O alojamento coletivo destina-se aos participantes com a modalidade Experiência completa. A localização, os horários de entrada e a lista do que deves levar serão enviados aos participantes confirmados antes do evento.' },
  { id: 14, category: 'alojamento', question: 'Onde decorrerão as atividades?', answer: 'O Campus das Gambelas é o recinto principal, com salas, auditórios e pontos de encontro dedicados ao evento.' },
  { id: 15, category: 'transporte', question: 'Como chego a Faro?', answer: 'Faro tem aeroporto internacional e ligações nacionais por comboio e autocarro. Planeia a viagem até Faro com antecedência e consulta os operadores para horários e preços atualizados.' },
  { id: 16, category: 'transporte', question: 'Como chego ao Campus das Gambelas?', answer: 'O mapa e o botão Obter direções nesta página indicam o recinto principal. As opções de transporte local e os pontos de encontro serão detalhados no guia de mobilidade do evento.' },
  { id: 17, category: 'transporte', question: 'Haverá transporte dedicado?', answer: 'Uma rede dedicada de transporte liga os principais pontos da experiência ENEI.' },
  { id: 18, category: 'parcerias', question: 'Como posso tornar-me parceiro?', answer: 'Consulta a página de Parcerias e pede o dossier comercial à equipa responsável através de coenei@aaualg.pt. Existem níveis de participação adaptáveis a organizações com diferentes objetivos e dimensões.' },
];