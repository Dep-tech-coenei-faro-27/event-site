import LegalPageLayout, { type LegalSection } from '../components/LegalPageLayout';

const sections: LegalSection[] = [
    {
        title: 'Âmbito',
        content: (
            <p>
                Estes termos aplicam-se à utilização do site do ENEI 2027, à criação de conta, à consulta de informação e ao processo de compra de bilhetes. Ao utilizar estas funcionalidades, deves fornecer informação verdadeira e respeitar as indicações apresentadas em cada etapa.   </p>
        ),
    },
    {
        title: 'Conta e acesso',
        content: (
            <p>A conta é pessoal. És responsável por manter as credenciais seguras, confirmar que o email indicado te pertence e atualizar os dados necessários para a inscrição. Se detetares acesso indevido, utiliza a área de recuperação ou procura apoio através da página Informação & Ajuda.
            </p>
        ),
    },
    {
        title: 'Bilhetes',
        content: (
            <p>
                Cada bilhete é pessoal e intransmissível e fica associado ao respetivo participante. A modalidade, o preço, os serviços incluídos e outras condições relevantes são apresentados antes da confirmação da compra. O código de entrada não deve ser partilhado.
            </p>
        ),
    },
    {
        title: 'Pagamentos',
        content: (
            <>
            <p>
                O pagamento é iniciado através do método apresentado no checkout. A inscrição apenas fica confirmada depois de o pagamento ser validado. Em caso de recusa, expiração ou falha, não é efetuada uma cobrança confirmada e podes repetir o processo.
            </p>
            <p>
                A fatura é emitida manualmente pela AAUalg, a entidade vendedora, e enviada para o email da tua conta até 20 dias úteis após a compra. Se a quiseres com número de contribuinte, indica o NIF (campo opcional) no checkout.
            </p>
            </>
        ),
    },
    {
        title: 'Alterações e cancelamentos',
        content: (
            <p>
                A organização pode atualizar horários, espaços ou atividades quando tal for necessário para o funcionamento ou segurança do encontro. As condições específicas de cancelamento, reembolso ou alteração aplicáveis à compra devem ser apresentadas no momento da aquisição, sem prejuízo dos direitos previstos na lei.
            </p>
        ),
    },
    {
        title: 'Utilização responsável',
        content: (
            <p>
                Não é permitido tentar comprometer o site, contornar mecanismos de segurança, utilizar dados de terceiros ou reproduzir bilhetes de forma fraudulenta. A organização pode limitar o acesso quando existam indícios de abuso ou utilização indevida. </p>
        ),
    },
];

export default function Acessibilidade() {
    return (
        <LegalPageLayout
            eyebrow="INFORMAÇÃO LEGAL"
            title="Termos e condições"
            lead="As regras essenciais para utilizar o site, gerir a tua conta e participar no ENEI 2027."
            version="1.0"
            lastUpdated="8 outubro 2026"
            lastUpdatedISO="2026-10-08"
            sections={sections}
        />
    );
}