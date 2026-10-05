import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar'; 
import Footer from './components/Footer'; 
import Home from './pages/Home';
import Login from './pages/Login';
import Registo from './pages/Registo';
import Equipa from './pages/Equipa';

function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-background">
        
        <Navbar />

 <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/registo" element={<Registo />} />
            <Route path="/equipa" element={<Equipa />} />
          </Routes>
        </main>

        <Footer />
        
      </div>
    </BrowserRouter>
  )
}

export default App;