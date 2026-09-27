import logoEnei from '../assets/ENEI-logo.svg';

function Footer() {
    return (
        <footer className="bg-[#404040] px-12 py-8 mt-12 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] font-sans">

            <div className="max-w-7xl w-full mx-auto flex flex-col gap-16 text-white">

                <div className="py-5 flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <img src={logoEnei} alt="Logótipo ENEI" className="h-8 w-auto" />
                        <span className="text-3xl font-semibold tracking-tight">enei</span>
                    </div>
                </div>

                <div className="w-full flex flex-col md:flex-row justify-between items-start md:items-end gap-12">

                    <div className="flex flex-wrap gap-12 md:gap-24">

                        <div className="flex flex-col gap-4">
                            <h4 className="text-[#D1D5DB] font-bold text-xs tracking-wider mb-2">DESCOBRIR</h4>
                            <ul className="flex flex-col gap-3 text-sm text-[#9CA3AF]">
                                <li><a href="#" className="hover:text-white transition-colors">Calendário</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Oradores</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Desafios</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Equipa</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Informação & Ajuda</a></li>
                            </ul>
                        </div>

                        <div className="flex flex-col gap-4">
                            <h4 className="text-[#D1D5DB] font-bold text-xs tracking-wider mb-2">O TEU ENEI</h4>
                            <ul className="flex flex-col gap-3 text-sm text-[#9CA3AF]">
                                <li><a href="#" className="hover:text-white transition-colors">Área Pessoal</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Survival Guide</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Formulário de Feedback</a></li>
                            </ul>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-12 md:gap-16">
                        <div className="flex flex-col gap-4">
                            <h4 className="text-[#D1D5DB] font-bold text-xs tracking-wider mb-2">REDES SOCIAIS</h4>
                            <div className="flex gap-2">
                                {[...Array(4)].map((_, i) => (
                                    <a key={i} href="#" className="bg-[#5A5A5A] p-2 rounded hover:bg-[#6B6B6B] transition-colors flex items-center justify-center w-8 h-8">
                                        <div className="w-4 h-4 bg-[#D1D5DB] rounded-sm"></div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </footer>
    )
}

export default Footer;