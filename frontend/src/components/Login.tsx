import { type FormEvent, useState } from "react";
import { login } from "../api";

interface Props {
  onLogin: (token: string) => void;
}

export function Login({ onLogin }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(username, password);
      onLogin(token);
    } catch {
      setError("Username or password is incorrect.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="centered-screen">
      <form className="card login" onSubmit={handleSubmit}>
        <h1>Document Analyst</h1>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
