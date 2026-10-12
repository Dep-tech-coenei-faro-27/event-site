import LegalPageLayout, { type LegalSection } from '../components/LegalPageLayout';

// Só o conteúdo: o índice, os ids (secao-1...), as caixas e o estilo do texto vêm do layout.
const sections: LegalSection[] = [
    {
        title: 'Dados tratados',
        content: (
            <p>
                Podem ser tratados dados de identificação e contacto, informação académica, dados associados à conta, à modalidade escolhida, ao pagamento e ao bilhete. Os dados técnicos estritamente necessários ao funcionamento e segurança do site também podem ser registados.
            </p>
        ),
    },
    {
        title: 'Finalidades',
        content: (
            <p>
                A informação é utilizada para criar e proteger a conta, processar a inscrição, disponibilizar o bilhete, prestar apoio, comunicar alterações relevantes e assegurar o funcionamento e a segurança do encontro.
            </p>
        ),
    },
    {
        title: 'Fundamento e minimização',
        content: (
            <p>
                O tratamento pode ser necessário para executar a inscrição ou compra, cumprir obrigações legais, proteger interesses legítimos de segurança ou responder a consentimentos específicos. Apenas devem ser pedidos os dados adequados a cada finalidade.
            </p>
        ),
    },
    {
        title: 'Partilha de dados',
        content: (
            <p>
                Os dados podem ser disponibilizados a prestadores que apoiem pagamentos, alojamento técnico, comunicação ou operação do evento, apenas na medida necessária e sujeitos às obrigações aplicáveis. Não são vendidos dados pessoais.
            </p>
        ),
    },
    {
        title: 'Conservação e segurança',
        content: (
            <p>
                A informação deve ser conservada apenas durante o período necessário para as finalidades indicadas e para cumprir obrigações aplicáveis. São adotadas medidas organizativas e técnicas destinadas a reduzir o risco de acesso, alteração ou divulgação indevida.
            </p>
        ),
    },
    {
        title: 'Os teus direitos',
        content: (
            <p>
                Podes solicitar acesso, correção, limitação ou eliminação dos teus dados quando aplicável, bem como esclarecer dúvidas sobre o tratamento. Utiliza a página Informação & Ajuda para encaminhar o pedido à organização.
            </p>
        ),
    },
];

export default function Acessibilidade() {
    return (
        <LegalPageLayout
            eyebrow="PRIVACIDADE"
            title="Política de privacidade"
            lead="Informação clara sobre os dados necessários para gerir a conta, o bilhete e a participação no encontro."
            version="1.0"
            lastUpdated="8 outubro 2026"
            lastUpdatedISO="2026-10-08"
            sections={sections}
        />
    );
}