
import "./PaymentRejectedPage.css";
import { Link } from "react-router-dom";
import IconCancel from "../../assets/svgs/IconCancel";


export function PaymentRejectedPage() {
    return (
        <section className="payment-approved-page payment-rejected-page">
            <div className="payment-approved-card">

                <div className="payment-approved-icon">
                    <IconCancel size={50} />
                </div>

                <h1>Pago rechazado</h1>

                <p>No pudimos procesar tu pago.</p>

                <p>
                    No se realizó ningún cobro.
                </p>

                <p>
                    Puedes volver al carrito e intentar realizar un nuevo pedido.
                </p>

                <div className="payment-approved-actions">
                    <Link to="/carrito">
                        Volver al carrito
                    </Link>

                    <Link to="/">
                        Volver al inicio
                    </Link>
                </div>

            </div>
        </section>
    );
}
