import { useState } from "react";
import api from "../lib/api";

const ResetPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/auth/password/reset/request", { email });
    setMessage("Nếu email tồn tại, mô hình tương tác lịch sử đã gửi hướng dẫn đặt lại mật khẩu.");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold text-center">Quên mật khẩu</h1>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        <div>
          <label className="text-sm text-slate-600">Email</label>
          <input
            type="email"
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="w-full rounded-md bg-brand-primary text-white py-2 font-semibold">
          Gửi hướng dẫn
        </button>
      </form>
    </div>
  );
};

export default ResetPasswordPage;
