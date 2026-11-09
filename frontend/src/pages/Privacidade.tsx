import LegalPageLayout, { type LegalSection } from '../components/LegalPageLayout';
import { LEGAL_DOCS, legalMeta } from '../data/LegalDocs';

// Só o conteúdo: o índice, os ids (secao-1...), as caixas e o estilo do texto vêm do layout.
const sections: LegalSection[] = [
    {
        title: 'Responsável pelo tratamento',
        content: (
            <p>
                O responsável pelo tratamento dos teus dados é a AAUalg, NIF 504035266, com sede no Campus da Penha, Instituto Superior de Engenharia, Estrada da Penha, 8005-139 Faro. Para qualquer questão sobre dados pessoais, escreve para{' '}
                <a href="mailto:geral@eneiconf.pt">geral@eneiconf.pt</a>.
            </p>
        ),
    },
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
            <>
                <p>
                    Os dados só são disponibilizados a prestadores que apoiam o encontro, na medida do necessário e sujeitos às obrigações aplicáveis. Não são vendidos dados pessoais. Os prestadores são:
                </p>
                <ul>
                    <li><strong>Stripe</strong>, para processar o pagamento (recebe o valor, o telefone do MB WAY, a modalidade comprada, a referência da compra e, se o indicares, o NIF para a fatura);</li>
                    <li><strong>Brevo</strong> e <strong>Resend</strong>, para enviar os emails da conta e do bilhete;</li>
                    <li><strong>Cloudflare</strong>, para proteger e entregar o site e para guardar as cópias de segurança, que são cifradas;</li>
                    <li><strong>OVH</strong>, que aloja o servidor onde os dados ficam guardados.</li>
                </ul>
            </>
        ),
    },
    {
        title: 'Conservação e segurança',
        content: (
            <p>
                Conservamos os teus dados durante o encontro e até duas semanas depois de ele terminar. Os dados de faturação ficam o tempo que a lei fiscal exige. As cópias de segurança, cifradas, guardam-se até 30 dias: quem pede a eliminação dos dados continua nelas até expirarem. São adotadas medidas organizativas e técnicas destinadas a reduzir o risco de acesso, alteração ou divulgação indevida.
            </p>
        ),
    },
    {
        title: 'Os teus direitos',
        content: (
            <p>
                Podes solicitar acesso, correção, limitação ou eliminação dos teus dados quando aplicável, bem como esclarecer dúvidas sobre o tratamento. Escreve para <a href="mailto:geral@eneiconf.pt">geral@eneiconf.pt</a> com o pedido. Também podes apresentar uma reclamação à Comissão Nacional de Proteção de Dados (cnpd.pt).
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
            {...legalMeta(LEGAL_DOCS.privacidade)}
            sections={sections}
        />
    );
}
