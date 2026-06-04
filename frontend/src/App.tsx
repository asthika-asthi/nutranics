import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import CustomerListPage from "./pages/CustomerListPage";
import CustomerDetailPage from "./pages/CustomerDetailPage";
import AppointmentsPage from "./pages/AppointmentsPage";
import ProductsPage from "./pages/ProductsPage";
import ReportsPage from "./pages/ReportsPage";
import OfflineBanner from "./components/OfflineBanner";
import { syncQueuedNotes } from "./lib/offlineDB";
import API from "./lib/api";

function Protected({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

// Register service worker for offline support
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
    // Sync queued notes when coming back online
    window.addEventListener("online", () => syncQueuedNotes(API));
  });
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Protected><Layout /></Protected>}>
          <Route index element={<DashboardPage />} />
          <Route path="customers" element={<CustomerListPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
      </Routes>
      <OfflineBanner />
    </>
  );
}