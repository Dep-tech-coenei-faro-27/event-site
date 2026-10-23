import { useSearchParams } from "react-router-dom";
import Eyebrow from "../components/EyeBrow";
import SecondaryButton from "../components/SecundaryButton";
import { usePageMeta } from "../utils/usePageMeta";
import { useAuth } from "../utils/useAuth";
import { isTicketSlug, TICKET_NAMES } from "../data/Tickets";

/**
 * Início do checkout: /bilhetes/checkout?bilhete=<modalidade>.
 * Está dentro do ProtectedRoute, por isso quem não tem sessão entra primeiro e volta aqui.
 * O formulário de pagamento (MB Way) é feito na issue #153 e entra nesta página.
 */
export default function CheckoutPage() {
  usePageMeta("Checkout · ENEI 2027", "Compra o teu bilhete para o ENEI 2027.");

  const [params] = useSearchParams();
  const slug = params.get("bilhete");
  const { user } = useAuth();

  const valid = isTicketSlug(slug);

  return (
    <div className="azulejo-bg min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px] max-[620px]:pb-[84px]">
      <section
        className="relative z-[1] py-[clamp(48px,7vw,92px)]"
      >
        <div className="mx-auto w-[min(calc(100%-28px),760px)] border border-[rgba(26,178,255,0.42)] bg-azul-painel px-[22px] py-[30px] min-[621px]:w-[min(calc(100%-40px),760px)] min-[621px]:p-[clamp(38px,6vw,64px)]">
          {valid ? (
            <>
              <Eyebrow text="CHECKOUT" />
              <h1 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                {TICKET_NAMES[slug]}
              </h1>
              <p className="mt-3.5 text-cinza-texto">
                Escolheste esta modalidade
                {user ? (
                  <>
                    {" "}com a conta <strong className="text-white">{user.email}</strong>
                  </>
                ) : null}
                .
              </p>
              <p
                role="status"
                className="mt-6 border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-3 text-sm text-gelo"
              >
                O pagamento ainda não está disponível. Volta a esta página quando a
                bilheteira abrir.
              </p>
            </>
          ) : (
            <>
              <Eyebrow text="CHECKOUT" />
              <h1 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                Escolhe uma modalidade.
              </h1>
              <p role="alert" className="mt-3.5 text-cinza-texto">
                Não encontrámos a modalidade de bilhete indicada. Escolhe uma na
                página dos bilhetes.
              </p>
            </>
          )}

          <div className="mt-8">
            <SecondaryButton
              text="Ver modalidades"
              to="/bilhetes#tipos"
              className="max-[620px]:w-full"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
