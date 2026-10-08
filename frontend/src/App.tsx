import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar'; 
import Footer from './components/Footer'; 
import Home from './pages/Home';
import Login from './pages/Login';
import Registo from './pages/Registo';
import Equipa from './pages/Equipa';
import InformacaoAjuda from './pages/InformacaoAjuda';
import Sobre from './pages/Sobre';
import VerifyEmailPage from './pages/VerifyEmailPage';

function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-[#050d21]">
        
        <Navbar />

        <main className="flex-grow bg-[#050d21]">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/equipa" element={<Equipa />} />
            <Route path="/bilhetes" element ={<Bilhetes/>} />
            <Route path="/sobre" element ={<Sobre/>} />
            <Route path="/parcerias" element ={<Parcerias/>} />
            <Route path="/informacao-ajuda" element={<InformacaoAjuda />} />
            <Route path="/sobre" element={<Sobre />} />

            <Route path="/conta" element={<Login />} />
            <Route path="/conta/criar" element={<Registo />} />
            <Route path="/conta/verificar" element={<VerifyEmailPage />} />
          </Routes>
        </main>

        <Footer />
        
      </div>
    </BrowserRouter>
  )
}

export default App;