import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Login from './pages/Login';
import Registo from './pages/Registo';
import Equipa from './pages/Equipa';
import InformacaoAjuda from './pages/InformacaoAjuda';
import Sobre from './pages/Sobre';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ProfilePage from './pages/Profile';
import ForgotPasswordPage from './pages/ForgotPassword';
import ResetPasswordPage from './pages/ResetPassword';
import ChangePasswordPage from './pages/ChangePassword';
import CheckoutPage from './pages/Checkout';
import Parcerias from './pages/Parcerias';
import Agenda from './pages/Agenda';
import NotFound from './pages/NotFound';
import Bilhetes from './pages/Bilhetes';
import Acessibilidade from './pages/Acessibilidade';
import Privacidade from './pages/Privacidade';
import Termos from './pages/TermosCondicoes';
import ScrollToTop from './components/ScrollToTop';
import { useMotion } from './utils/useMotion';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './utils/AuthContext';

// Um erro numa página mostra o ecrã de erro dentro do layout (com Navbar e Footer) e
// desaparece ao navegar para outra página.
function RouteErrorBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <ErrorBoundary resetKey={pathname}>{children}</ErrorBoundary>;
}

// Camada de animações do desenho novo (ver utils/useMotion.ts); vive dentro do router para saber
// em que página está.
function MotionLayer() {
  useMotion();
  return null;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ScrollToTop />
        <MotionLayer />
        <div className="flex flex-col min-h-screen bg-[#050d21]">

          <Navbar />

          <main className="flex-grow bg-[#050d21]">
            <RouteErrorBoundary>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/equipa" element={<Equipa />} />
              <Route path="/bilhetes" element={<Bilhetes />} />
              <Route path="/sobre" element={<Sobre />} />
              <Route path="/parcerias" element={<Parcerias />} />
              <Route path="/informacao-ajuda" element={<InformacaoAjuda />} />
              <Route path="/sobre" element={<Sobre />} />
              <Route path="/parcerias" element={<Parcerias />} />
              <Route path="/acessibilidade" element={<Acessibilidade/>}/>
              <Route path="/termos" element={<Termos/>} /> 
              <Route path="/agenda" element={<Agenda />} />
              <Route path="/privacidade" element={<Privacidade />}/>
              <Route path="/conta" element={<Login />} />
              <Route path="/conta/criar" element={<Registo />} />
              <Route path="/conta/verificar" element={<VerifyEmailPage />} />
              <Route path="/conta/recuperar" element={<ForgotPasswordPage />} />
              <Route path="/conta/redefinir" element={<ResetPasswordPage />} />

              <Route element={<ProtectedRoute />}>
                <Route path="/perfil" element={<ProfilePage />} />
                <Route path="/conta/alterar-palavra-passe" element={<ChangePasswordPage />} />
                <Route path="/bilhetes/checkout" element={<CheckoutPage />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
            </RouteErrorBoundary>
          </main>
          <Footer />

        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App;
