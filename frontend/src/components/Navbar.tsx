function Navbar() {
  return (
    <nav className="bg-background px-8 py-6 shadow-md font-sans">
        
        <ul className="flex justify-center gap-12 text-body">
            <li>
              <a href="#" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                Home
              </a>
            </li>
            <li>
              <a href="#" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                News
              </a>
            </li>
            <li>
              <a href="#" className="block p-2 text-secondary hover:text-primary transition-colors duration-200">
                Contact
              </a>
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