import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import API from "../lib/api";
import { queueOfflineNote } from "../lib/offlineDB";

type Tab = "overview" | "notes" | "tests" | "plans" | "invoices";

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [newNote, setNewNote] = useState("");
  const [noteType, setNoteType] = useState("general");

  const { data: customer, isLoading } = useQuery({ queryKey: ["customer", id], queryFn: () => API.get(`/customers/${id}`).then(r => r.data) });
  const { data: notes } = useQuery({ queryKey: ["notes", id], queryFn: () => API.get(`/customers/${id}/notes`).then(r => r.data), enabled: tab === "notes" });
  const { data: testResults } = useQuery({ queryKey: ["tests", id], queryFn: () => API.get(`/customers/${id}/test-results`).then(r => r.data), enabled: tab === "tests" });
  const { data: subscriptions } = useQuery({ queryKey: ["plans", id], queryFn: () => API.get(`/subscriptions?customer_id=${id}`).then(r => r.data), enabled: tab === "plans" });

  const addNote = useMutation({
    mutationFn: async (payload: any) => {
      if (!navigator.onLine) {
        await queueOfflineNote({ ...payload, customer_id: id!, created_at: new Date().toISOString() });
        return { offline: true };
      }
      return API.post(`/customers/${id}/notes`, payload);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notes", id] }); setNewNote(""); },
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!customer) return <div className="p-6 text-red-500">Customer not found</div>;

  const tabs: Tab[] = ["overview", "notes", "tests", "plans"];

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate("/customers")} className="text-sm text-gray-500 hover:text-gray-700 mb-1">← Customers</button>
          <h1 className="text-xl font-bold text-gray-900">{customer.name}</h1>
          <p className="text-sm text-gray-500">{customer.email} · {customer.phone}</p>
        </div>
        <div className="flex gap-2">
          <span className={`px-3 py-1 rounded-full text-sm ${customer.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
            {customer.is_active ? "Active" : "Inactive"}
          </span>
          <button className="bg-brand-600 text-white text-sm px-4 py-2 rounded hover:bg-brand-700">Edit</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-1">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition ${
              tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>{t}</button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg shadow p-5 space-y-3">
            <h3 className="font-medium text-gray-700">Contact</h3>
            <div className="text-sm space-y-1">
              <p><span className="text-gray-500">Email:</span> {customer.email || "—"}</p>
              <p><span className="text-gray-500">Phone:</span> {customer.phone || "—"}</p>
              <p><span className="text-gray-500">Postcode:</span> {customer.postcode || "—"}</p>
              <p><span className="text-gray-500">Source:</span> {customer.source || "—"}</p>
              <p><span className="text-gray-500">Preferred:</span> {customer.preferred_contact || "—"}</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-5 space-y-3">
            <h3 className="font-medium text-gray-700">Health Flags</h3>
            {customer.health_flags?.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {(customer.health_flags as string[]).map((f: string) => (
                  <span key={f} className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded">{f}</span>
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No flags recorded</p>}
          </div>
        </div>
      )}

      {tab === "notes" && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-medium text-gray-700 mb-3">Add Note</h3>
            <div className="flex gap-2">
              <select value={noteType} onChange={e => setNoteType(e.target.value)}
                className="border rounded px-2 py-1 text-sm">
                <option value="general">General</option>
                <option value="intake">Intake</option>
                <option value="follow_up">Follow-up</option>
                <option value="consultation">Consultation</option>
              </select>
              <textarea value={newNote} onChange={e => setNewNote(e.target.value)} rows={2}
                placeholder="Write a note…"
                className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              <button onClick={() => addNote.mutate({ content: newNote, note_type: noteType, sync_id: crypto.randomUUID() })}
                disabled={!newNote.trim()} className="bg-brand-600 text-white px-4 rounded text-sm disabled:opacity-50 hover:bg-brand-700">
                Save
              </button>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow divide-y">
            {(notes || []).length === 0 && <p className="p-6 text-center text-gray-400 text-sm">No notes yet</p>}
            {(notes || []).map((n: any) => (
              <div key={n.id} className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-brand-600 uppercase">{n.note_type}</span>
                  <span className="text-xs text-gray-400">{format(new Date(n.created_at), "MMM d, yyyy HH:mm")}</span>
                </div>
                <p className="text-sm text-gray-800">{n.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "tests" && (
        <div className="bg-white rounded-lg shadow">
          {(testResults || []).length === 0
            ? <p className="p-6 text-center text-gray-400 text-sm">No test results recorded</p>
            : <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Date</th>
                    <th className="px-4 py-2.5 font-medium">Type</th>
                    <th className="px-4 py-2.5 font-medium">Biomarkers</th>
                    <th className="px-4 py-2.5 font-medium">Practitioner</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(testResults || []).map((t: any) => (
                    <tr key={t.id} className="border-t">
                      <td className="px-4 py-2.5">{t.test_date ? format(new Date(t.test_date), "MMM d, yyyy") : "—"}</td>
                      <td className="px-4 py-2.5">{t.test_type}</td>
                      <td className="px-4 py-2.5 text-gray-600">{t.marker_count ?? t.markers?.length ?? 0} markers</td>
                      <td className="px-4 py-2.5 text-gray-600">{t.practitioner_id || "—"}</td>
                      <td className="px-4 py-2.5"><span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">{t.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
          }
        </div>
      )}

      {tab === "plans" && (
        <div className="bg-white rounded-lg shadow divide-y">
          {(subscriptions || []).length === 0
            ? <p className="p-6 text-center text-gray-400 text-sm">No active subscriptions</p>
            : (subscriptions || []).map((s: any) => (
              <div key={s.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{s.plan_id || "—"}</div>
                    <div className="text-xs text-gray-500">
                      {s.start_date ? `Since ${format(new Date(s.start_date), "MMM d, yyyy")}` : ""} · {s.status}
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    s.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>{s.status}</span>
                </div>
              </div>
            ))
          }
        </div>
      )}
    </div>
  );
}