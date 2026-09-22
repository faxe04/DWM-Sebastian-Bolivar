import "./LoginPage.css";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";


export function LoginPage() {
    const Navigate = useNavigate();

    const [form, setForm] = useState({
        email: "",
        password: "" // Ver como guardar hash luego 
    })

    const handleChange = (event) => {
        setForm({
            ...form,
            [event.target.name]: event.target.value
        });
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        console.log(form); // Temp
        Navigate("/");
    };

    return (
        <section className="auth-page">
            <div className="auth-card">

                <h1>Iniciar sesión</h1>

                <p className="auth-description">
                Ingresa a tu cuenta para continuar.
                </p>

                <form onSubmit={handleSubmit}>
                    <label htmlFor="email">Correo electrónico</label>

                    <input
                        id="email"
                        name="email"
                        type="email"
                        value={form.email}
                        onChange={handleChange}
                        required
                    />

                    <label htmlFor="password">Contraseña</label>

                    <input
                        id="password"
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                        required
                    />

                    <button type="submit">Ingresar</button>

                </form>

                <p className="auth-register">
                    ¿No tienes una cuenta?{" "}
                    <Link to="/registro">Regístrate</Link>
                </p>

            </div>
        </section>
    )
}
