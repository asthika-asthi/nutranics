import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, startOfWeek, addDays } from "date-fns";
import API from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-700",
  confirmed: "bg-indigo-100 text-indigo-700",
  checked_in: "bg-green-100 text-green-700",
  completed: "bg-gray-100 text-gray-600",
  no_show: "bg-red-100 text-red-700",
  cancelled: "bg-gray-200 text-gray-500",
};

export default function AppointmentsPage() {
  const qc = useQueryClient();
  const [weekOffset, setWeekOffset] = useState(0);

  const weekStart = addDays(startOfWeek(new Date(), { weekStartsOn: 1 }), weekOffset * 7);
  const days = Array.from({ length: 5 }, (_, i) => addDays(weekStart, i));

  const { data: appointments } = useQuery({
    queryKey: ["appts", days[0].toISOString(), days[4].toISOString()],
    queryFn: () => API.get("/appointments", {
      params: {
        start_date: format(days[0], "yyyy-MM-dd"),
        end_date: format(days[4], "yyyy-MM-dd"),
      }
    }).then(r => r.data),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => API.patch(`/appointments/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["appts"] }),
  });

  const grouped = (appointments || []).reduce((acc: Record<string, any[]>, a: any) => {
    const d = a.scheduled_at?.slice(0, 10);
    if (!d) return acc;
    (acc[d] = acc[d] || []).push(a);
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Appointments</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => setWeekOffset(w => w - 1)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">←</button>
          <span className="text-sm font-medium min-w-[160px] text-center">
            {format(days[0], "MMM d")} – {format(days[4], "MMM d, yyyy")}
          </span>
          <button onClick={() => setWeekOffset(w => w + 1)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">→</button>
          <button onClick={() => setWeekOffset(0)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">Today</button>
        </div>
      </div>

      {/* Week view */}
      <div className="grid grid-cols-5 gap-3">
        {days.map(day => {
          const key = format(day, "yyyy-MM-dd");
          const dayAppts = grouped[key] || [];
          return (
            <div key={key} className="bg-white rounded-lg shadow min-h-[200px]">
              <div className={`px-3 py-2 border-b text-center text-sm font-medium ${
                key === format(new Date(), "yyyy-MM-dd") ? "bg-brand-50 text-brand-700" : "text-gray-700"
              }`}>
                <div className="text-xs text-gray-400">{format(day, "EEE")}</div>
                <div>{format(day, "d")}</div>
              </div>
              <div className="p-2 space-y-1.5">
                {dayAppts.map((a: any) => (
                  <div key={a.id} className={`text-xs p-2 rounded border-l-2 bg-gray-50 ${STATUS_COLORS[a.status] || "bg-gray-50"}`}>
                    <div className="font-medium truncate">{a.customer_id?.slice(0, 8) || "—"}</div>
                    <div className="text-gray-500 truncate">{a.type} · {a.scheduled_at ? format(new Date(a.scheduled_at), "HH:mm") : ""}</div>
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {a.status === "scheduled" && (
                      <button onClick={() => updateStatus.mutate({ id: a.id, status: "confirmed" })}
                        className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded hover:bg-indigo-200">Confirm</button>
                    )}
                    {a.status === "confirmed" && (
                      <button onClick={() => updateStatus.mutate({ id: a.id, status: "checked_in" })}
                        className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded hover:bg-green-200">Check in</button>
                    )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}