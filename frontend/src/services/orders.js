const API_URL = "http://127.0.0.1:8000/api/v1";


export async function createOrder(cart, token, idempotencyKey) {
    const response = await fetch(`${API_URL}/orders`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
            "Idempotency-Key": idempotencyKey
        },
        body: JSON.stringify({
            delivery_method: "pickup",
            items: cart.map(product => ({
                product_id: product.id,
                quantity: product.quantity
            }))
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "No se pudo crear el pedido"
        );
    }

    return data;
}
