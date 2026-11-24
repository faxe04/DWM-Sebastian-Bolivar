
const CART_KEY = "aroma_cart";


export function getCart() {
    try {
        const data = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
        return Array.isArray(data) ? data : [];
    } catch {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    return cart;
}


export function addToCart(product) {
    if (!product.available) return getCart();

    const cart = getCart();
    const existing = cart.find(item => item.id === product.id);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            quantity: 1
        });
    }
    console.log("Carrito actualizado! Añadido")
    return saveCart(cart);
}


export function changeQuantity(id, amount) {
    const cart = getCart()
        .map(item =>
            item.id === id
                ? { ...item, quantity: item.quantity + amount }
                : item
        )
        .filter(item => item.quantity > 0);

    return saveCart(cart);
}

export function removeFromCart(id) {
    const cart = getCart().filter(item => item.id !== id);
    console.log("Carrito actualizado! Eliminado")
    return saveCart(cart);
}
