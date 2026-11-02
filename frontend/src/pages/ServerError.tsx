import PrimaryButton from '../components/PrimaryButton';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';
import SystemState from './estados/SystemState';

interface ServerErrorProps {
  onRetry: () => void;
  /** Fora do layout da aplicação (sem Navbar nem rotas): leva o seu próprio `<main>`. */
  standalone?: boolean;
}

/**
 * Ecrã de erro do servidor do protótipo (`ui-ux/erros/servidor`), usado quando uma página
 * falha ao ser desenhada. Sem ele um erro deixava o site em branco.
 */
export default function ServerError({ onRetry, standalone = false }: ServerErrorProps) {
  useBodyPage('estado', 'system-state-page system-state-page--danger');
  usePageMeta(
    'Erro do servidor · ENEI 2027',
    'Ocorreu um erro temporário no site do ENEI 2027.',
  );

  const content = (
    <div role="alert">
      <SystemState
        icon={
          <>
            <path d="M12 8v5M12 16v.01" />
            <path d="M10.3 3.9 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
          </>
        }
        kicker="Erro do servidor"
        title="Não conseguimos abrir esta página."
        lead="Tenta novamente daqui a pouco. Se o problema continuar, contacta a equipa."
        actions={
          <>
            <PrimaryButton text="Tentar novamente" onClick={onRetry} />
            {/* Sem `Link` do router: este ecrã também aparece quando o próprio router falhou. */}
            <a className="btn btn--secondary" href="/informacao-ajuda">
              Pedir ajuda
            </a>
          </>
        }
        note="Se o erro continuar, indica à equipa de apoio o código apresentado nesta página."
        detailLabel="Detalhes do erro"
        detail={{
          code: '500',
          heading: 'O serviço está temporariamente indisponível.',
          text: 'Não precisas de repetir ações anteriores enquanto esta página estiver aberta.',
          facts: [
            { label: 'Código', value: '500' },
            { label: 'Conta', value: 'Sem alterações' },
            { label: 'Próximo passo', value: 'Tentar novamente' },
          ],
        }}
      />
    </div>
  );

  // Dentro da aplicação o `<main>` já existe (App.tsx): não se aninha outro.
  return standalone ? <main>{content}</main> : content;
}
