
const API_URL = "http://127.0.0.1:8000/api/v1";


export async function login(username, password) {
    const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username,
            password
        })
    });

    const data = await response.json();

    if (!response.ok) {throw new Error(data.detail || "Error al iniciar sesión");}

    return data;
}


export async function getMe(token) {
    const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    if (!response.ok) {throw new Error("No se pudo validar la sesión");}

    return response.json();
}


export async function logout(token) {
    const response = await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    if (!response.ok) {
        throw new Error("No se pudo invalidar la sesión en el servidor");
    }
}
