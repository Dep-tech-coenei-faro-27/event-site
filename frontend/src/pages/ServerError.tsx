import Eyebrow from '../components/EyeBrow';
import PrimaryButton from '../components/PrimaryButton';
import SectionHeading from '../components/SectionHeading';

interface ServerErrorProps {
  onRetry: () => void;
  /** Fora do layout da aplicação (sem Navbar nem rotas): leva o seu próprio `<main>`. */
  standalone?: boolean;
}

const wrapper =
  'grid min-h-[70vh] place-items-center bg-azul-base px-5 pb-20 pt-[calc(76px+64px)]';

// Sem `Link` do router: este ecrã também aparece quando o próprio router falhou.
const helpLink = 'btn btn--secondary';

/**
 * Ecrã de erro do servidor do protótipo (`ui-ux/erros/servidor`), usado quando uma página
 * falha ao ser desenhada. Sem ele um erro deixava o site em branco.
 */
export default function ServerError({ onRetry, standalone = false }: ServerErrorProps) {
  const content = (
    <div className="mx-auto w-full max-w-[720px] text-center" role="alert">
      <SectionHeading
        align="center"
        eyebrow={<Eyebrow text="ERRO DO SERVIDOR" />}
        title="Algo não correu como esperado."
        lead="Não conseguimos concluir o teu pedido. O problema é temporário e os teus dados continuam seguros: tenta novamente dentro de momentos."
        className="mb-0"
        classNameTitle="text-[clamp(32px,5vw,56px)] leading-[1.06] tracking-[-0.045em] text-branco"
        classNameLead="text-cinza-texto"
      />
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <PrimaryButton text="Tentar novamente" onClick={onRetry} />
        <a href="/informacao-ajuda" className={helpLink}>
          Pedir ajuda
        </a>
      </div>
      <p className="mt-6 text-sm text-cinza-texto">
        Se o erro continuar, contacta a equipa de apoio.
      </p>
    </div>
  );

  // Dentro da aplicação o `<main>` já existe (App.tsx): não se aninha outro.
  return standalone ? (
    <main className={wrapper}>{content}</main>
  ) : (
    <section className={wrapper}>{content}</section>
  );
}
