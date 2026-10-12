import { Link } from 'react-router-dom';
import Eyebrow from '../components/EyeBrow';
import SectionHeading from '../components/SectionHeading';

export default function NotFound() {
  return (
    <main className="grid min-h-[70vh] place-items-center bg-azul-base px-5 pb-20 pt-[calc(76px+64px)]">
      <div className="mx-auto w-full max-w-[720px] text-center">
        <SectionHeading
          align="center"
          eyebrow={<Eyebrow text="ERRO 404" />}
          title="Esta página não existe."
          lead="O endereço que abriste não existe ou ainda não está disponível."
          className="mb-0"
          classNameTitle="text-[clamp(32px,5vw,56px)] leading-[1.06] tracking-[-0.045em] text-branco"
          classNameLead="text-cinza-texto"
        />
        <Link
          to="/"
          className="mt-8 inline-flex min-h-[46px] items-center justify-center rounded-full bg-acento-principal px-6 text-sm font-bold text-texto-sobre-ciano transition hover:-translate-y-0.5 hover:bg-acento-forte"
        >
          Voltar ao início
        </Link>
      </div>
    </main>
  );
}