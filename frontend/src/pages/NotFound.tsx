import { Link } from 'react-router-dom';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';
import SystemState from './estados/SystemState';

/** `ui-ux/erros/404`: o endereço aberto não corresponde a nenhuma página. */
export default function NotFound() {
  useBodyPage('estado', 'system-state-page');
  usePageMeta(
    'Página não encontrada · ENEI 2027',
    'A página que procuras não foi encontrada no site do ENEI 2027.',
  );
  return (
    <SystemState
      icon={
        <>
          <path d="M9 9h.01M15 9h.01M8.5 16a5 5 0 0 1 7 0" />
          <circle cx="12" cy="12" r="9" />
        </>
      }
      kicker="Página não encontrada"
      title="Não encontrámos esta página."
      lead="Confirma o endereço ou volta à página inicial."
      actions={
        <>
          <Link className="btn btn--primary" to="/">
            Voltar ao início
          </Link>
          <Link className="btn btn--secondary" to="/agenda">
            Ver agenda
          </Link>
        </>
      }
      note="Se chegaste aqui através de uma ligação do ENEI, avisa-nos para a podermos corrigir."
      detailLabel="Detalhes do erro"
      detail={{
        code: '404',
        heading: 'Não encontrámos este endereço.',
        text: 'Usa o menu para escolher outra página.',
        facts: [
          { label: 'Código', value: '404' },
          { label: 'Conta', value: 'Sem alterações' },
          { label: 'Próximo passo', value: 'Escolher outra página' },
        ],
      }}
    />
  );
}
