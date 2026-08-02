import { useState } from "react";
import { AuthenticatedApp } from "./components/AuthenticatedApp";
import { Login } from "./components/Login";

const TOKEN_KEY = "rag_token";

export default function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );

  function handleLogin(newToken: string) {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return <AuthenticatedApp token={token} onLogout={handleLogout} />;
}
