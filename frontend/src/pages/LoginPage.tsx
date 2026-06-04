import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import API from "../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@wellnessclinic.com");
  const [password, setPassword] = useState("Demo1234!");
  const [error, setError] = useState("");
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const { data } = await API.post("/auth/login", { email, password });
      const token: string = data.access_token;
      // Fetch profile
      const profile = await API.get("/auth/me");
      setAuth(profile.data, token);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed");
    }
  };

  return (
    <div className="min-h-screen bg-brand-900 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg p-8 w-96">
        <h1 className="text-2xl font-bold text-brand-900 mb-1">WellnessOS</h1>
        <p className="text-gray-500 text-sm mb-6">Sign in to your clinic account</p>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button type="submit" className="w-full bg-brand-600 text-white rounded py-2 font-medium hover:bg-brand-700 transition">
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}