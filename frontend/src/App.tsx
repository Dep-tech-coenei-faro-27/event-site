import Navbar from './components/Navbar.tsx'
import Footer from './components/Footer.tsx'
function App() {

  return (
    <>
      <Navbar /> 
        <div className="bg-background flex flex-col p-8 gap-4 items-start">
            
            <h1 className="text-h1">Test h1</h1>
            <h2 className="text-h2">Test h2</h2>
            <h3 className="text-h3">Test h3</h3>
            <p className="text-body">Test body</p>
            <p className="text-caption">Test caption</p>

            <p className="text-primary">Test primary color</p>
            <p className="text-body text-secondary">Test secundary color</p>

            <button className="bg-primary text-background font-sans text-caption p-4 gap-4 rounded-md">
                Botão de Teste
            </button>

        </div>
        <div> 
          <Footer/> 
        </div>
    </>
  )
}

export default App
