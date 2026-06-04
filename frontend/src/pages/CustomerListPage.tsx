import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import API from "../lib/api";

export default function CustomerListPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["customers", page, search],
    queryFn: () => API.get("/customers", { params: { page, page_size: 20, search: search || undefined } }).then(r => r.data),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Customers</h1>
        <Link to="/customers/new" className="bg-brand-600 text-white text-sm px-4 py-2 rounded hover:bg-brand-700">
          + New Customer
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow">
        {/* Search */}
        <div className="p-4 border-b">
          <input type="text" placeholder="Search by name or email…" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="w-full max-w-xs border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>

        {isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading…</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Email</th>
                  <th className="px-4 py-2.5 font-medium">Phone</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {(data?.items || data || []).map((c: any) => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2.5">
                      <Link to={`/customers/${c.id}`} className="text-brand-700 hover:underline font-medium">{c.name}</Link>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{c.email || "—"}</td>
                    <td className="px-4 py-2.5 text-gray-600">{c.phone || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${
                        c.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                      }`}>{c.is_active ? "Active" : "Inactive"}</span>
                    </td>
                  </tr>
                ))}
                {(!data?.items && !Array.isArray(data)) && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No customers found</td></tr>
                )}
              </tbody>
            </table>

            {/* Pagination */}
            {data?.total_pages > 1 && (
              <div className="p-4 border-t flex items-center gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  className="px-3 py-1 text-sm border rounded disabled:opacity-40">← Prev</button>
                <span className="text-sm text-gray-500">Page {page} of {data.total_pages}</span>
                <button onClick={() => setPage(p => p + 1)} disabled={page >= data.total_pages}
                  className="px-3 py-1 text-sm border rounded disabled:opacity-40">Next →</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}