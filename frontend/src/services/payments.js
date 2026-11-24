
const API_URL = "http://127.0.0.1:8000/api/v1";

async function readResponse(response) {
    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "No se pudo procesar el pago"
        );
    }

    return data;
}

export async function getOrder(orderId, token) {
    const response = await fetch(`${API_URL}/orders/${orderId}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    return readResponse(response);
}

export async function createPayment(orderId, token) {
    const response = await fetch(`${API_URL}/payments`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            "Idempotency-Key": `demo-order-${orderId}`
        },
        body: JSON.stringify({
            order_id: orderId
        })
    });

    return readResponse(response);
}

export async function testPayment(paymentId, cardNumber, token) {
    const response = await fetch(
        `${API_URL}/payments/${paymentId}/test`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                number: cardNumber
            })
        }
    );

    return readResponse(response);
}
