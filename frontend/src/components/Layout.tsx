import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { useState } from "react";

const nav = [
  { to: "/", label: "Dashboard", icon: "◉" },
  { to: "/customers", label: "Customers", icon: "👤" },
  { to: "/appointments", label: "Appointments", icon: "📅" },
  { to: "/products", label: "Products", icon: "📦" },
  { to: "/reports", label: "Reports", icon: "📊" },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className={`${collapsed ? "w-16" : "w-56"} bg-brand-900 text-white flex flex-col transition-width duration-200`}>
        <div className="p-4 font-bold text-lg border-b border-brand-800">
          {collapsed ? "WC" : "WellnessOS"}
        </div>
        <nav className="flex-1 py-2">
          {nav.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm cursor-pointer hover:bg-brand-800 ${isActive ? "bg-brand-700 border-r-4 border-blue-400" : ""}`
              }
            >
              <span>{icon}</span>
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-brand-800">
          <div className={`text-xs text-gray-400 mb-1 ${collapsed ? "text-center" : ""}`}>
            {!collapsed && user?.name}
          </div>
          <button onClick={handleLogout} className="text-xs text-red-400 hover:text-red-300">
            {collapsed ? "⇥" : "Sign out"}
          </button>
        </div>
        <button onClick={() => setCollapsed(c => !c)} className="p-2 text-center text-xs text-brand-700 hover:text-brand-500 border-t border-brand-800">
          {collapsed ? "→" : "←"}
        </button>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}