import { NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

const links = [
  { to: "/", label: "Trang chủ" },
  { to: "/chat", label: "Chat" },
  // { to: "/library", label: "Thư viện" },
  // { to: "/quests", label: "Nhiệm vụ" },
  // { to: "/profile", label: "Hồ sơ" },
];

interface Props {
  children: React.ReactNode;
}

const MainLayout = ({ children }: Props) => {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const handleLogout = () => {
    logout();
    navigate("/login");
  };
  return (
    <div className="min-h-screen flex bg-slate-100">
      <aside className="w-64 bg-white border-r hidden md:flex flex-col py-6 px-4">
        <h1 className="text-2xl font-semibold text-brand-primary leading-snug">THCS Lý Tự Trọng</h1>
        <nav className="mt-8 flex-1 space-y-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md font-medium ${isActive ? "bg-brand-primary text-white" : "text-slate-700"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <button className="text-sm text-slate-500" onClick={handleLogout}>
          Đăng xuất
        </button>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="md:hidden flex items-center justify-between bg-white px-4 py-3 shadow">
          <span className="font-semibold text-sm leading-snug">THCS Lý Tự Trọng</span>
          <button className="text-sm text-brand-primary" onClick={handleLogout}>
            Thoát
          </button>
        </header>
        <main className="flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
};

export default MainLayout;
