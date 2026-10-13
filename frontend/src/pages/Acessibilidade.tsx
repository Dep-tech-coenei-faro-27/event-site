import LegalPageLayout, { type LegalSection } from '../components/LegalPageLayout';

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
            <p>
                A interface utiliza hierarquia tipográfica, contraste entre texto e fundo, estados visuais
                consistentes e larguras de leitura controladas. A informação importante não depende apenas da cor.
            </p>
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
                O site adapta-se a desktop, tablet e telemóvel e procura respeitar preferências do dispositivo. A
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
                utilizada e descreve o problema através de Informação &amp; Ajuda. Esse detalhe ajuda a organização
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
            version="1.0"
            lastUpdated="8 outubro 2026"
            lastUpdatedISO="2026-10-08"
            sections={sections}
        />
    );
}