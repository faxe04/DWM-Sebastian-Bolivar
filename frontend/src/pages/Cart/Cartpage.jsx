import "./CartPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCart, changeQuantity, removeFromCart } from "../../services/cart";
import { useRef } from "react";
import { createOrder } from "../../services/orders";


export function CartPage() {
    const navigate = useNavigate();
    const [cartProducts, setCartProducts] = useState(getCart);
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [createdOrder, setCreatedOrder] = useState(null);
    const orderKey = useRef(crypto.randomUUID());
    const subtotal = cartProducts.reduce(
        (total, product) =>
            total + product.price * product.quantity,
        0
    );

    const handleQuantity = (id, amount) => {
        setCartProducts(changeQuantity(id, amount));
    };

    const handleRemove = (id) => {
        setCartProducts(removeFromCart(id));
        orderKey.current = crypto.randomUUID();
    };

    
    const handleCheckout = async () => {
        const token = sessionStorage.getItem("access_token");

        if (!token) {
            navigate("/login");
            return;
        }

        if (loading || createdOrder || cartProducts.length === 0) {
            return;
        }

        setLoading(true);
        setMessage("");

        try {
            const order = await createOrder(
                cartProducts,
                token,
                orderKey.current
            );

            setCreatedOrder(order);

            navigate(`/pagar/${order.id}`);

        } catch (error) {
            setMessage(error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="cart-page">
            <h1>Mi carrito</h1>

            <div className="cart-products">
                {cartProducts.length === 0 && (
                    <p>Tu carrito está vacío.</p>
                )}

                {cartProducts.map(product => (
                    <article
                        className="cart-product"
                        key={product.id}
                    >
                        {product.image && (
                            <img
                                src={product.image}
                                alt={product.name}
                            />
                        )}

                        <div className="cart-product-info">
                            <h2>{product.name}</h2>

                            <p>
                                ${product.price.toLocaleString("es-CL")}
                            </p>

                            <div className="cart-quantity">
                                <button
                                    onClick={() =>
                                        handleQuantity(product.id, -1)
                                    }
                                >
                                    -
                                </button>

                                <span>{product.quantity}</span>

                                <button
                                    onClick={() =>
                                        handleQuantity(product.id, 1)
                                    }
                                >
                                    +
                                </button>
                            </div>
                        </div>

                        <button
                            className="cart-remove"
                            onClick={() => handleRemove(product.id)}
                        >
                            Eliminar
                        </button>
                    </article>
                ))}
            </div>

            <div className="cart-summary">
                <div>
                    <span>Subtotal</span>
                    <strong>
                        ${subtotal.toLocaleString("es-CL")}
                    </strong>
                </div>

                <button
                    className="cart-checkout"
                    disabled={cartProducts.length === 0 || loading || !!createdOrder}
                    onClick={handleCheckout}
                >
                    {loading
                        ? "Creando pedido..."
                        : createdOrder
                            ? "Pedido creado"
                            : "Confirmar pedido"
                    }
                </button>

                {message && <p role="status">{message}</p>}
            </div>
        </section>
    );
}
