import { useQuery } from "@tanstack/react-query";
import API from "../lib/api";
import { format } from "date-fns";

const StatCard = ({ label, value, sub }: { label: string; value: string | number; sub?: string }) => (
  <div className="bg-white rounded-lg shadow p-5">
    <div className="text-3xl font-bold text-brand-900">{value}</div>
    <div className="text-sm text-gray-500 mt-1">{label}</div>
    {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
  </div>
);

export default function DashboardPage() {
  const { data: report } = useQuery({ queryKey: ["report"], queryFn: () => API.get("/reports/dashboard").then(r => r.data) });
  const { data: appts } = useQuery({
    queryKey: ["appts-today"],
    queryFn: () => API.get("/appointments", { params: { start_date: format(new Date(), "yyyy-MM-dd"), end_date: format(new Date(), "yyyy-MM-dd") } }).then(r => r.data),
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Active Customers" value={report?.customer_counts?.active ?? "—"} sub="currently active" />
        <StatCard label="Today's Appointments" value={appts?.length ?? 0} sub={format(new Date(), "MMM d, yyyy")} />
        <StatCard label="Pending Invoices" value={report?.pending_invoices ?? "—"} />
        <StatCard label="Low Stock Items" value={report?.low_stock_count ?? "—"} sub="below reorder threshold" />
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-5 py-3 border-b font-medium text-gray-700">Upcoming Appointments</div>
        {appts?.length > 0 ? (
          <ul>
            {appts.slice(0, 6).map((a: any) => (
              <li key={a.id} className="flex items-center justify-between px-5 py-3 border-b last:border-0">
                <div>
                  <div className="font-medium text-sm">{a.customer_id}</div>
                  <div className="text-xs text-gray-500">{a.type} · {a.location}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">{a.scheduled_at ? format(new Date(a.scheduled_at), "HH:mm") : ""}</div>
                  <div className={`text-xs px-2 py-0.5 rounded-full ${
                    a.status === "confirmed" ? "bg-blue-100 text-blue-700" :
                    a.status === "checked_in" ? "bg-green-100 text-green-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{a.status}</div>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className="px-5 py-6 text-sm text-gray-400 text-center">No appointments today</p>}
      </div>
    </div>
  );
}