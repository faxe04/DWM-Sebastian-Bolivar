
import "./NavBar.css";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

import IconCart from "../../assets/svgs/IconCart";
import IconHam from "../../assets/svgs/IconHam";
import IconUser from "../../assets/svgs/IconUser";

import { useAuth } from "../../context/AuthContext";


export function NavBar() {
    const [menuOpen, setMenuOpen] = useState(false);
    const { isAuthenticated, loadingSession, signOut } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        try {
            await signOut();
        } catch (error) {
            console.warn(error.message);
        }

        setMenuOpen(false);
        navigate("/");
    };

    return (
        <nav className="nav">
            <button
                className="nav-toggle"
                onClick={() => setMenuOpen(!menuOpen)}
                aria-expanded={menuOpen}
            >
                <IconHam strokeWidth={2} />
            </button>

            <Link className="nav-logo" to="/">
                Café & Aroma
            </Link>

            <Link className="nav-cart-mobile" to="/carrito">
                <IconCart size={30} strokeWidth={2} />
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
                        <IconCart size={30} strokeWidth={2} />
                    </Link>

                    {!loadingSession && (
                        isAuthenticated ? (
                            <button
                                type="button"
                                className="nav-logout"
                                onClick={handleLogout}
                                title="Cerrar sesión"
                            >
                                <IconUser size={30} strokeWidth={2} />
                                <span>Salir</span>
                            </button>
                        ) : (
                            <Link to="/login" title="Iniciar sesión">
                                <IconUser size={30} strokeWidth={2} />
                            </Link>
                        )
                    )}
                </div>
            </div>
        </nav>
    );
}
