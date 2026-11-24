
import { createContext, useContext, useEffect, useState } from "react";
import { getMe, logout as logoutRequest } from "../services/auth";
const AuthContext = createContext(null);


export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loadingSession, setLoadingSession] = useState(true);

    useEffect(() => {
        const token = sessionStorage.getItem("access_token");

        if (!token) {
            setLoadingSession(false);
            return;
        }

        let cancelled = false;

        getMe(token)
            .then(data => {
                if (!cancelled) setUser(data);
            })
            .catch(() => {
                if (!cancelled) {
                    sessionStorage.removeItem("access_token");
                    setUser(null);
                }
            })
            .finally(() => {
                if (!cancelled) setLoadingSession(false);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    const signIn = (token, userData) => {
        sessionStorage.setItem("access_token", token);
        setUser(userData);
    };

    const signOut = async () => {
        const token = sessionStorage.getItem("access_token");

        try {
            if (token) await logoutRequest(token);
        } finally {
            sessionStorage.removeItem("access_token");
            setUser(null);
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                loadingSession,
                signIn,
                signOut
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}


export function useAuth() {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error("useAuth requiere AuthProvider");
    }

    return context;
}
