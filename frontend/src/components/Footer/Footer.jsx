import "./Footer.css"
//import { Link } from "react-router-dom"


export function Footer(){
    return (
        <footer className="footer">
            <div className="footer-content">
                {/* Logo */}
                <div className="footer-brand">
                    <p>CAFE & AROMA</p>
                </div>

                {/* Info */}
                <div className="footer-section">
                    <h3>Contacto</h3>
                    <p>contacto@cafeyaroma.cl</p>
                    <p>+56 9 1234 5678</p>
                    <p>Santiago, Chile</p>
                </div>

                {/* Social */}
                <div className="footer-social">
                    <p>Facebook</p>
                    <p>Instagram</p>
                    <p>Whatsapp</p>
                </div>
            </div>
            {/* C */}
            <div className="footer-bottom">
                <p>©2026 Cafe & Aroma</p>
            </div>
        </footer>
    )
}


