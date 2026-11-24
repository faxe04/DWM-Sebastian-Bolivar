import "./LoginPage.css";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { login, getMe } from "../../services/auth";
import { useAuth } from "../../context/AuthContext";


export function LoginPage() {
    const navigate = useNavigate();
    const { signIn } = useAuth();
    const [form, setForm] = useState({
        username: "",
        password: ""
    });

    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (event) => {
        setForm({
            ...form,
            [event.target.name]: event.target.value
        });
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError("");
        setLoading(true);

        try {
            const result = await login(
                form.username,
                form.password
            );

            const userData = await getMe(result.access_token);

            signIn(result.access_token, userData);

            navigate("/");

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="auth-page">
            <div className="auth-card">

                <h1>Iniciar sesión</h1>

                <p className="auth-description">
                    Ingresa a tu cuenta para continuar.
                </p>

                <form onSubmit={handleSubmit}>
                    <label htmlFor="username">
                        Nombre de usuario
                    </label>

                    <input
                        id="username"
                        name="username"
                        type="text"
                        value={form.username}
                        onChange={handleChange}
                        required
                    />

                    <label htmlFor="password">
                        Contraseña
                    </label>

                    <input
                        id="password"
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                        required
                    />

                    {error && (
                        <p role="alert" className="auth-error">
                            {error}
                        </p>
                    )}

                    <button type="submit" disabled={loading}>
                        {loading ? "Ingresando..." : "Ingresar"}
                    </button>
                </form>

                <p className="auth-register">
                    ¿No tienes una cuenta?{" "}
                    <Link to="/registro">Regístrate</Link>
                </p>

            </div>
        </section>
    );
}
