import "./ProductCard.css"
import { addToCart } from "../../services/cart";


export function ProductCard({ product }){
    return (
        <article className="product-card">
            <img 
                className="product-card-image"
                src={product.image} 
                alt={product.name}
            />
            <div className="product-card-content">
                <p className="product-card-category">
                    {product.category}
                </p>
                <h3>{product.name}</h3>
                <p className="product-card-price">
                  ${product.price.toLocaleString("es-CL")} 
                </p>
                <button
                    className="product-card-button"
                    disabled={!product.available}
                    onClick={() => addToCart(product)}
                >
                    {product.available ? "Agregar al carrito" : "No disponible"}
                </button>
            </div>
        </article>
    )
}
