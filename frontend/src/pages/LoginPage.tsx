import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuthStore } from "../store/auth";

const LoginPage = () => {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/auth/login", form);
      setSession(data.user, data.access_token, data.refresh_token);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-center">Đăng nhập mô hình tương tác lịch sử</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div>
          <label className="text-sm text-slate-600">Email</label>
          <input
            type="email"
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="text-sm text-slate-600">Mật khẩu</label>
          <input
            type="password"
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-brand-primary text-white py-2 font-semibold"
        >
          {loading ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
        <div className="flex justify-between text-sm">
          <Link to="/register" className="text-brand-secondary">
            Tạo tài khoản
          </Link>
          <Link to="/reset-password" className="text-brand-secondary">
            Quên mật khẩu?
          </Link>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
