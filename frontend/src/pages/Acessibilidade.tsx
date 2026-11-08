import LegalPageLayout, { type LegalSection } from '../components/LegalPageLayout';
import { LEGAL_DOCS, legalMeta } from '../data/LegalDocs';

const sections: LegalSection[] = [
    {
        title: 'Navegação',
        content: (
            <p>
                As páginas incluem uma ligação para saltar diretamente para o conteúdo, uma ordem de navegação
                coerente e controlos identificados. Os percursos principais podem ser utilizados com teclado, sem
                depender exclusivamente do rato.
            </p>
        ),
    },
    {
        title: 'Leitura e contraste',
        content: (
            <>
                <p>
                    O texto sobre as superfícies escuras do site cumpre o contraste mínimo de 4,5:1 (nível AA das
                    WCAG 2.1) nos pares de cores utilizados, o que é verificado por testes automáticos. A interface
                    usa hierarquia tipográfica, estados visuais consistentes e larguras de leitura controladas, e a
                    informação importante não depende apenas da cor.
                </p>
                <p>
                    <strong>Exceção conhecida.</strong> Nas caixas finais com fundo azul-claro em degradê (nas
                    páginas Início, Sobre, Agenda e Bilhetes), o texto branco sobre a parte mais clara do degradê
                    tem um contraste medido entre cerca de 2,2:1 e 5:1: os parágrafos descem a cerca de 2,2:1 e os
                    títulos a cerca de 2,9:1, abaixo do mínimo de 4,5:1 (3:1 para texto grande). Os destinos dessas
                    caixas (Bilhetes, Agenda e Informações e ajuda) estão também no menu principal. Medição feita
                    a 8 de novembro de 2026.
                </p>
            </>
        ),
    },
    {
        title: 'Estrutura e alternativas',
        content: (
            <p>
                Os conteúdos usam títulos, regiões e listas semânticas. Imagens informativas devem incluir
                alternativas textuais; elementos decorativos são ocultados das tecnologias de apoio sempre que
                adequado.
            </p>
        ),
    },
    {
        title: 'Formulários e mensagens',
        content: (
            <p>
                Os campos têm etiquetas associadas, instruções próximas e mensagens compreensíveis. Os estados de
                confirmação, espera ou erro devem indicar claramente o que aconteceu e qual é o passo seguinte.
            </p>
        ),
    },
    {
        title: 'Compatibilidade',
        content: (
            <p>
                O site adapta-se a diferentes tamanhos de ecrã e respeita as preferências do dispositivo. A
                experiência pode variar consoante o navegador, a tecnologia de apoio ou serviços externos utilizados
                no processo de pagamento.
            </p>
        ),
    },
    {
        title: 'Comunicar uma barreira',
        content: (
            <p>
                Se encontrares uma dificuldade de acesso, indica a página, o dispositivo ou tecnologia de apoio
                utilizada e descreve o problema através de Informações e ajuda. Esse detalhe ajuda a organização
                a investigar e melhorar a experiência.
            </p>
        ),
    },
];

export default function Acessibilidade() {
    return (
        <LegalPageLayout
            eyebrow="ACESSIBILIDADE"
            title="Declaração de acessibilidade"
            lead="Queremos que a informação e os principais percursos do ENEI sejam claros, navegáveis e utilizáveis por todas as pessoas."
            {...legalMeta(LEGAL_DOCS.acessibilidade)}
            sections={sections}
        />
    );
}
