import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import API from "../lib/api";

export default function ReportsPage() {
  const { data: summary } = useQuery({
    queryKey: ["report-summary"],
    queryFn: () => API.get("/reports/summary", {
      params: { start_date: format(subDays(new Date(), 30), "yyyy-MM-dd"), end_date: format(new Date(), "yyyy-MM-dd") }
    }).then(r => r.data),
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Reports</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-2xl font-bold text-brand-900">{summary?.total_revenue ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">Revenue (30d)</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-2xl font-bold text-brand-900">{summary?.total_customers ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">New customers (30d)</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-2xl font-bold text-brand-900">{summary?.total_appointments ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">Appointments (30d)</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-2xl font-bold text-brand-900">{summary?.cancellation_rate ?? "—"}%</div>
          <div className="text-sm text-gray-500 mt-1">Cancellation rate</div>
        </div>
      </div>

      {/* Revenue by day */}
      {summary?.revenue_by_day?.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-5 py-3 border-b font-medium text-gray-700">Revenue — last 30 days</div>
          <div className="p-5">
            <div className="flex items-end gap-1 h-32">
              {summary.revenue_by_day.map((r: any, i: number) => {
                const max = Math.max(...summary.revenue_by_day.map((d: any) => d.total || 1));
                const pct = ((r.total || 0) / max) * 100;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div className="w-full bg-brand-200 hover:bg-brand-400 rounded-t" style={{ height: `${Math.max(pct, 2)}%` }} />
                    <span className="text-[9px] text-gray-400">{format(new Date(r.date), "d")}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Practitioner breakdown */}
      {summary?.practitioner_stats?.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-5 py-3 border-b font-medium text-gray-700">Practitioner Activity</div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-4 py-2.5 font-medium">Practitioner</th>
                <th className="px-4 py-2.5 font-medium text-right">Customers</th>
                <th className="px-4 py-2.5 font-medium text-right">Appointments</th>
                <th className="px-4 py-2.5 font-medium text-right">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {summary.practitioner_stats.map((p: any) => (
                <tr key={p.practitioner_id} className="border-t">
                  <td className="px-4 py-2.5 font-medium">{p.practitioner_id || "—"}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{p.customer_count ?? 0}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{p.appointment_count ?? 0}</td>
                  <td className="px-4 py-2.5 text-right font-medium">£{parseFloat(p.revenue || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}