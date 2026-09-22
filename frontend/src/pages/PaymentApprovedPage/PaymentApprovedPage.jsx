import "./PaymentApprovedPage.css";
import { Link } from "react-router-dom";
import IconCheck from "../../assets/svgs/IconCheck";

export function PaymentApprovedPage() {
  return (
    <section className="payment-approved-page">
      <div className="payment-approved-card">

        <div className="payment-approved-icon">
          <IconCheck size={50}></IconCheck>
        </div>

        <h1>Pago aprobado</h1>

        <p>Tu compra fue realizada correctamente.</p>

        <p>
          Tu pedido comenzará a ser preparado.
        </p>

        <div className="payment-approved-actions">
          <Link to="/">
            Volver al inicio
          </Link>
        </div>

      </div>
    </section>
  );
}