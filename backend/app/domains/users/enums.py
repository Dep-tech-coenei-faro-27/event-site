from enum import Enum, StrEnum


class Role(Enum):
    USER = "user"
    ADMIN = "admin"


class PortugueseInstitution(StrEnum):
    """Instituições de ensino superior reconhecidas.

    Já não se guarda na conta da pessoa: é a lista de onde o comprovativo de
    estudante tira o nome e as variantes para reconhecer a instituição da
    assinatura (``app/domains/students/institutions.py``).
    """

    ULISBOA = "Universidade de Lisboa"
    UPORTO = "Universidade do Porto"
    UCOIMBRA = "Universidade de Coimbra"
    UNL = "Universidade Nova de Lisboa"
    UMINHO = "Universidade do Minho"
    UA = "Universidade de Aveiro"
    ISCTE = "ISCTE - Instituto Universitário de Lisboa"
    UBI = "Universidade da Beira Interior"
    UCA = "Universidade Católica Portuguesa"

    # Subsistema Universitário - Públicas e Comunitárias
    UABERTA = "Universidade Aberta"
    UACORES = "Universidade dos Açores"
    UALG = "Universidade do Algarve"
    UEVORA = "Universidade de Évora"
    UMADEIRA = "Universidade da Madeira"
    UTAD = "Universidade de Trás-os-Montes e Alto Douro"
    ISMT = "Instituto Superior Miguel Torga"

    # Subsistema Universitário - Privadas
    UAL = "Universidade Autónoma de Lisboa Luís de Camões"
    UMAIA = "Universidade da Maia"
    UEUROPEIA = "Universidade Europeia"
    UFP = "Universidade Fernando Pessoa"
    ULUSIADA = "Universidade Lusíada"
    ULUSIADA_NORTE = "Universidade Lusíada - Norte"
    ULUSOFONA = "Universidade Lusófona de Humanidades e Tecnologias"
    ULUSOFONA_PORTO = "Universidade Lusófona do Porto"
    UPT = "Universidade Portucalense Infante D. Henrique"
    ATLANTICA = "Atlântica - Instituto Universitário"
    IUCS = "Instituto Universitário de Ciências da Saúde"
    IUEM = "Instituto Universitário Egas Moniz"
    ISPA = "ISPA - Instituto Universitário de Ciências Psicológicas, Sociais e da Vida"
    ESAP = "Escola Superior Artística do Porto"
    ESG = "Escola Superior Gallaecia"
    EUVG = "Escola Universitária Vasco da Gama"
    ISEIT_ALMADA = (
        "Instituto Superior de Estudos Interculturais e Transdisciplinares - Almada"
    )
    ISEIT_VISEU = (
        "Instituto Superior de Estudos Interculturais e Transdisciplinares - Viseu"
    )
    ISG = "Instituto Superior de Gestão"
    ISMAT = "Instituto Superior Manuel Teixeira Gomes"
    ISSSP = "Instituto Superior de Serviço Social do Porto"

    # Subsistema Politécnico - Universidades Politécnicas e Institutos Politécnicos
    IPBEJA = "Universidade Politécnica de Beja"
    IPB = "Universidade Politécnica de Bragança"
    IPCB = "Universidade Politécnica de Castelo Branco"
    IPCA = "Universidade Politécnica do Cávado e do Ave"
    IPC = "Universidade Politécnica de Coimbra"
    IPG = "Universidade Politécnica da Guarda"
    IPL = "Universidade Politécnica de Lisboa"
    IPPORTALEGRE = "Universidade Politécnica de Portalegre"
    IPSANTAREM = "Universidade Politécnica de Santarém"
    IPSETUBAL = "Universidade Politécnica de Setúbal"
    IPT = "Universidade Politécnica de Tomar"
    IPVC = "Universidade Politécnica de Viana do Castelo"
    IPV = "Universidade Politécnica de Viseu"
    CESPU_IPSN = "CESPU - Instituto Politécnico de Saúde do Norte"
    IPLUSOFONIA = "Instituto Politécnico da Lusofonia"
    IPMAIA = "Instituto Politécnico da Maia"
    PIAGET_NORTE = "Instituto Politécnico Jean Piaget do Norte"
    PIAGET_SUL = "Instituto Politécnico Jean Piaget do Sul"
    ISPGAYA = "Instituto Superior Politécnico Gaya"
    ISLA_GAIA = "ISLA - Instituto Politécnico de Gestão e Tecnologia"

    # Subsistema Politécnico - Unidades Não Integradas
    ESENFC = "Escola Superior de Enfermagem de Coimbra"
    ESEL = "Escola Superior de Enfermagem de Lisboa"
    ESEP = "Escola Superior de Enfermagem do Porto"
    ESHTE = "Escola Superior de Hotelaria e Turismo do Estoril"
    ENIDH = "Escola Superior Náutica Infante D. Henrique"
    ANSO = "Academia Nacional Superior de Orquestra"
    ESAD = "Escola Superior de Artes e Design"
    ESAI = "Escola Superior de Atividades Imobiliárias"
    ESE_FAFE = "Escola Superior de Educação de Fafe"
    ESEJD = "Escola Superior de Educação de João de Deus"
    ESEPF = "Escola Superior de Educação de Paula Frassinetti"
    ESEMU = "Escola Superior de Educadores de Infância Maria Ulrich"
    ESECVP_ALTO_TAMEGA = (
        "Escola Superior de Enfermagem Cruz Vermelha Portuguesa - Alto Tâmega"
    )
    ESESFM = "Escola Superior de Enfermagem S. Francisco das Misericórdias"
    ESESJC = "Escola Superior de Enfermagem São José de Cluny"
    ESNA = "Escola Superior de Negócios Atlântico"
    ESSAT = "Escola Superior de Saúde Atlântica"
    ESSFP = "Escola Superior de Saúde da Fundação «Fernando Pessoa»"
    ESSA = "Escola Superior de Saúde do Alcoitão"
    ESSCVP_LISBOA = "Escola Superior de Saúde da Cruz Vermelha Portuguesa - Lisboa"
    ESSSM = "Escola Superior de Saúde de Santa Maria"
    ESSEM = "Escola Superior de Saúde Egas Moniz"
    ESSP_GAIA = "Escola Superior de Saúde Jean Piaget de Vila Nova de Gaia"
    ESSP_VISEU = "Escola Superior de Saúde Jean Piaget de Viseu"
    ESSN_CVP = "Escola Superior de Saúde Norte da Cruz Vermelha Portuguesa"
    EST_FAFE = "Escola Superior de Tecnologias de Fafe"
    ISAVE = "ISAVE - Instituto Superior de Saúde"
    ISCE = "ISCE - Instituto Superior de Lisboa e Vale do Tejo"
    ISEC_LISBOA = "ISEC Lisboa - Instituto Superior de Educação e Ciências"
    ISLA_SANTAREM = "ISLA - Instituto Superior de Gestão e Administração de Santarém"
    IPAM_LISBOA = "Instituto Português de Administração de Marketing de Lisboa"
    IPAM_PORTO = "Instituto Português de Administração de Marketing do Porto"
    ISAG = "Instituto Superior de Administração e Gestão"
    ISAL = "Instituto Superior de Administração e Línguas"
    ISCE_DOURO = "Instituto Superior de Ciências Educativas do Douro"
    ISCET = "Instituto Superior de Ciências Empresariais e do Turismo"
    ISCIA = "Instituto Superior de Ciências da Informação e da Administração"
    ISDOMDINIS = "Instituto Superior D. Dinis"
    ISVOUGA = "Instituto Superior de Entre Douro e Vouga"
    ISTEC_LISBOA = "Instituto Superior de Tecnologias Avançadas de Lisboa"
    ISTEC_PORTO = "Instituto Superior de Tecnologias Avançadas do Porto"

    # Subsistema Politécnico - Unidades Integradas em Universidades
    ESEC_UALG = "Escola Superior de Educação e Comunicação"
    ESGHT_UALG = "Escola Superior de Gestão, Hotelaria e Turismo"
    ESS_UALG = "Escola Superior de Saúde"
    ISE_UALG = "Instituto Superior de Engenharia"
    ESESJD_UEVORA = "Escola Superior de Enfermagem de São João de Deus"
    ESS_UACORES = "Escola Superior de Saúde"
    EST_UACORES = "Escola Superior de Tecnologias"
    ESSUA = "Escola Superior de Saúde de Aveiro"
    ESAN_UA = (
        "Escola Superior de Design, Gestão e Tecnologias da Produção de Aveiro-Norte"
    )
    ESTGA_UA = "Escola Superior de Tecnologia e Gestão de Águeda"
    ISCA_UA = "Instituto Superior de Contabilidade e Administração de Aveiro"
    ESS_UFP = "Escola Superior de Saúde"
    ESS_UMADEIRA = "Escola Superior de Saúde"
    ESTG_UMADEIRA = "Escola Superior de Tecnologias e Gestão"
    ESE_UMINHO = "Escola Superior de Enfermagem"
    ESS_UTAD = "Escola Superior de Saúde"
    ESPS_UCP_LISBOA = "Escola Superior Politécnica de Saúde (Lisboa)"
    ESPS_UCP_PORTO = "Escola Superior Politécnica de Saúde (Porto)"
    UFP_PONTE_DE_LIMA = (
        "Universidade Fernando Pessoa (unidade de Ponte de Lima - ensino politécnico)"
    )
