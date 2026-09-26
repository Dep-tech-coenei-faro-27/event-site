import { Link} from 'react-router-dom';

function Navbar() {
  return (
    <nav className="bg-background px-8 py-6 shadow-md font-sans">
        
        <ul className="flex justify-center gap-12 text-body">
            <li>
              <Link to="/" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                Home
              </Link>
            </li>
            <li>
              <Link to="/login" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                Login
              </Link>
            </li>
            <li>
              <Link to="/registo" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                Registo
              </Link>
            </li>
            <li>
              <a href="#" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                About
              </a>
            </li>
        </ul>
    </nav>
  )
}

export default Navbar;