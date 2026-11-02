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
  { id: 1, category: 'inscricoes', question: 'Como compro o bilhete?', answer: 'Escolhe uma modalidade em Bilhetes, entra ou cria uma conta e conclui o pagamento. O bilhete fica disponível na área pessoal após a confirmação.' },
  { id: 2, category: 'inscricoes', question: 'Quanto custa?', answer: 'Consulta o valor e o que cada modalidade inclui antes de confirmar a compra.' },
  { id: 3, category: 'inscricoes', question: 'As refeições estão incluídas?', answer: 'Sim, nos bilhetes Acesso + refeições, Experiência completa e Passe geral + refeições. Confirma o que inclui a modalidade escolhida.' },
  { id: 4, category: 'inscricoes', question: 'Recebo certificado de participação?', answer: 'Os participantes elegíveis recebem um certificado após o evento. As instruções serão divulgadas na conta e nos canais oficiais.' },
  { id: 5, category: 'inscricoes', question: 'Como altero ou elimino os meus dados?', answer: 'Atualiza os dados na tua conta. Para pedir acesso, correção ou eliminação, escreve para coenei@aaualg.pt.' },
  { id: 6, category: 'inscricoes', question: 'Onde encontro as informações oficiais?', answer: 'Neste site: programa, bilhetes, informações práticas e documentos legais. Se tiveres dúvidas, contacta a organização.' },
  { id: 7, category: 'programa', question: 'Onde vejo o programa?', answer: 'Na Agenda. Escolhe o dia, pesquisa uma atividade e guarda as sessões que te interessam.' },
  { id: 8, category: 'programa', question: 'Que palestras e oficinas vão existir?', answer: 'Os temas, oradores, salas e limites de lotação aparecem na Agenda à medida que forem confirmados.' },
  { id: 9, category: 'programa', question: 'O que posso fazer no ENEI?', answer: 'Assistir a palestras, participar em sessões práticas e desafios, conhecer empresas e conviver com estudantes de todo o país.' },
  { id: 10, category: 'programa', question: 'E depois das palestras?', answer: 'Há arraial, convívio e atividades noturnas. Consulta os horários na Agenda.' },
  { id: 11, category: 'programa', question: 'Como funcionam os desafios digitais?', answer: 'A plataforma do evento prevê distintivos, moedas virtuais e recompensas por participares nas atividades. Os detalhes serão divulgados antes do encontro.' },
  { id: 12, category: 'alojamento', question: 'O bilhete inclui alojamento?', answer: 'O bilhete Experiência completa inclui alojamento coletivo. As outras modalidades não incluem estadia.' },
  { id: 13, category: 'alojamento', question: 'Onde fico alojado?', answer: 'Na Escola Secundária Tomás Cabreira, com o bilhete Experiência completa. Receberás os horários de entrada e a lista do que deves levar antes do evento.' },
  { id: 14, category: 'alojamento', question: 'Onde decorre o evento?', answer: 'O recinto principal é o Campus das Gambelas, na Universidade do Algarve, em Faro. Consulta o local de cada atividade na Agenda.' },
  { id: 15, category: 'transporte', question: 'Como chego a Faro?', answer: 'Podes chegar de comboio, autocarro ou avião. Consulta os horários e preços junto dos operadores.' },
  { id: 16, category: 'transporte', question: 'Como chego às Gambelas?', answer: 'Usa o mapa e o botão Obter direções nesta página. As indicações de transporte local serão divulgadas no guia do evento.' },
  { id: 17, category: 'transporte', question: 'Há transporte do evento?', answer: 'Está previsto transporte entre os principais locais do ENEI. Os percursos e horários serão divulgados antes do evento.' },
  { id: 18, category: 'parcerias', question: 'Quero ser parceiro. Com quem falo?', answer: 'Escreve para geral@eneiconf.pt e pede a apresentação das opções de parceria.' },
  { id: 19, category: 'programa', question: 'Preciso de inscrição para o Rally Tascas?', answer: 'Sim. O Rally Tascas é pago e exige inscrição própria. O valor e as indicações para te inscreveres serão divulgados pela organização.' },
  { id: 20, category: 'programa', question: 'Guardar uma sessão garante lugar?', answer: 'Não. Guardar serve para organizares a tua agenda neste dispositivo. Se uma atividade exigir inscrição, tens de a fazer em separado.' },
];
