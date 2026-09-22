import "./NavBar.css"
import { Link } from "react-router-dom";
import { useState } from "react";
import IconCart from '../../assets/svgs/IconCart'
import IconHam from "../../assets/svgs/IconHam";
import IconUser from "../../assets/svgs/IconUser";


export function NavBar() {
    const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className='nav'>
        <button 
            className="nav-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-expanded={menuOpen}
        >
            <IconHam strokeWidth={2}></IconHam>
        </button>

        <Link className="nav-logo" to="/">Café & Aroma</Link>

        <Link className="nav-cart-mobile" to="/carrito">
            <IconCart size={30} strokeWidth={2}></IconCart>
        </Link>
        
        <div className={`nav-menu ${menuOpen ? "nav-menu-open" : ""}`}>
            <ul className="nav-links">
                <li><Link to="/">Inicio</Link></li>
                <li><Link to="/productos">Productos</Link></li>
                <li><Link to="/nosotros">Nosotros</Link></li>
                <li><Link to="/contacto">Contacto</Link></li>
            </ul>
            <div className="nav-actions">
                <Link className="nav-cart-desktop" to="/carrito">
                    <IconCart size={30} strokeWidth={2}></IconCart>
                </Link>
                <Link to="/login">
                    <IconUser size={30} strokeWidth={2}></IconUser>
                </Link>
            </div>
        </div>
    </nav>
  )
}