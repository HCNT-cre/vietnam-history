import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";

const RegisterPage = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      await api.post("/auth/register", { ...form, locale: "vi-VN" });
      setMessage("Đăng ký thành công! Hãy đăng nhập để tiếp tục.");
      setTimeout(() => navigate("/login"), 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Đăng ký thất bại");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-center">Tạo tài khoản cho mô hình tương tác lịch sử</h1>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div>
          <label className="text-sm text-slate-600">Tên hiển thị</label>
          <input
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            required
          />
        </div>
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
          <label className="text-sm text-slate-600">Mật khẩu (≥12 ký tự)</label>
          <input
            type="password"
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={12}
          />
        </div>
        <button type="submit" className="w-full rounded-md bg-brand-primary text-white py-2 font-semibold">
          Đăng ký
        </button>
        <p className="text-sm text-center">
          Đã có tài khoản? <Link to="/login" className="text-brand-secondary">Đăng nhập</Link>
        </p>
      </form>
    </div>
  );
};

export default RegisterPage;
