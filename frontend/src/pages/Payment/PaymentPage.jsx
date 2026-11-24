
import "./PaymentPage.css";

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getOrder, createPayment, testPayment } from "../../services/payments";

export function PaymentPage() {
    const { orderId } = useParams();
    const navigate = useNavigate();

    const [order, setOrder] = useState(null);
    const [cardNumber, setCardNumber] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        const token = sessionStorage.getItem("access_token");

        if (!token) {
            navigate("/login");
            return;
        }

        let active = true;

        getOrder(orderId, token)
            .then(data => {
                if (!active) return;

                if (data.status === "PAID") {
                    navigate("/pago-aprobado", {
                        replace: true,
                        state: { orderId: data.id }
                    });
                    return;
                }

                setOrder(data);
            })
            .catch(err => {
                if (active) setError(err.message);
            });

        return () => {
            active = false;
        };
    }, [orderId, navigate]);

    const handlePayment = async (event) => {
        event.preventDefault();

        if (loading || !order) return;

        const token = sessionStorage.getItem("access_token");

        if (!token) {
            navigate("/login");
            return;
        }

        setLoading(true);
        setError("");

        try {
            // Crear el pago asociado al pedido
            const payment = await createPayment(order.id, token);

            // Procesar la tarjeta de prueba
            const result = await testPayment(
                payment.id,
                cardNumber.replace(/\s/g, ""),
                token
            );

            if (result.status === "APPROVED") {
                // Verificar que Orders también haya confirmado el pago
                const updatedOrder = await getOrder(order.id, token);

                if (updatedOrder.status !== "PAID") {
                    throw new Error(
                        "El pago fue aprobado, pero el pedido aún no se confirma"
                    );
                }

                // Limpiar el carrito después de confirmar la compra
                localStorage.removeItem("aroma_cart");

                navigate("/pago-aprobado", {
                    replace: true,
                    state: { orderId: order.id }
                });

            } else if (result.status === "REJECTED") {
                navigate("/pago-rechazado", {
                    replace: true,
                    state: { orderId: order.id }
                });

            } else {
                setError("El pago sigue pendiente de confirmación.");
            }

        } catch (err) {
            setError(err.message);

        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="payment-page">
            <div className="payment-card">
                <h1>Realizar pago</h1>

                {order && (
                    <div className="payment-summary">
                        <h2>Pedido #{order.id}</h2>

                        <p>
                            Total: ${order.total.toLocaleString("es-CL")}
                        </p>
                    </div>
                )}

                {order?.status === "PENDING_PAYMENT" && (
                    <form onSubmit={handlePayment}>
                        <label htmlFor="cardNumber">
                            Número de tarjeta de prueba
                        </label>

                        <input
                            id="cardNumber"
                            type="text"
                            inputMode="numeric"
                            placeholder="0000 0000 0000 0001"
                            value={cardNumber}
                            onChange={e => setCardNumber(e.target.value)}
                            maxLength={23}
                            required
                            disabled={loading}
                        />

                        <button type="submit" disabled={loading}>
                            {loading ? "Procesando..." : "Pagar"}
                        </button>
                    </form>
                )}

                {order && order.status !== "PENDING_PAYMENT" && (
                    <p>Este pedido no se encuentra pendiente de pago.</p>
                )}

                {error && <p role="alert">{error}</p>}
            </div>
        </section>
    );
}
