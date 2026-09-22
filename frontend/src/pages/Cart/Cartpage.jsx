import "./CartPage.css";
import { products } from "../../services/products";
import { useNavigate } from "react-router-dom";


export function CartPage() {
    const navigate = useNavigate();
    const cartProducts = [
        {
        ...products[0],
        quantity: 1
        },
        {
        ...products[2],
        quantity: 2
        }
    ];

    const subtotal = cartProducts.reduce(
        (total, product) =>
        total + product.price * product.quantity,
        0
    );

        const handlePayment = () => {
            navigate("/pago-aprobado");
        }

    return (
        <section className="cart-page">
        <h1>Mi carrito</h1>

        <div className="cart-products">
            {cartProducts.map(product => (
            <article
                className="cart-product"
                key={product.id}
            >
                <img
                    src={product.image}
                    alt={product.name}
                />

                <div className="cart-product-info">
                    <h2>{product.name}</h2>

                    <p>
                        ${product.price.toLocaleString("es-CL")}
                    </p>

                    <div className="cart-quantity">
                        <button>-</button>
                        <span>{product.quantity}</span>
                        <button>+</button>
                    </div>
                </div>

                <button className="cart-remove">
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
                    onClick={handlePayment}
                >
                    Ir a pagar
                </button>
            </div>
        </section>
    );
}