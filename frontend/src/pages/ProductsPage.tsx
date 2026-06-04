import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import API from "../lib/api";

export default function ProductsPage() {
  const qc = useQueryClient();
  const [category, setCategory] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: products, isLoading } = useQuery({
    queryKey: ["products", category],
    queryFn: () => API.get("/products", { params: category ? { category } : {} }).then(r => r.data),
  });

  const importCSV = useMutation({
    mutationFn: (formData: FormData) => API.post("/products/import/csv", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      alert(`Created: ${res.data.created}, Updated: ${res.data.updated}`);
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (err: any) => alert(err.response?.data || "Import failed"),
  });

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    importCSV.mutate(fd);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Products</h1>
        <div className="flex items-center gap-3">
          <select value={category} onChange={e => setCategory(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">All categories</option>
            {["IV Supplies", "Supplements", "Lab", "Services"].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input type="file" ref={fileRef} accept=".csv" onChange={handleFile}
            className="text-sm file:mr-3 file:px-3 file:py-1.5 file:rounded file:border-0 file:bg-brand-600 file:text-white file:text-sm file:hover:bg-brand-700" />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-4 py-2.5 font-medium">SKU</th>
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Category</th>
                <th className="px-4 py-2.5 font-medium text-right">Cost</th>
                <th className="px-4 py-2.5 font-medium text-right">Retail</th>
                <th className="px-4 py-2.5 font-medium text-right">Stock</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(products || []).map((p: any) => (
                <tr key={p.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{p.sku}</td>
                  <td className="px-4 py-2.5 font-medium">{p.name}</td>
                  <td className="px-4 py-2.5 text-gray-600">{p.category}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600">£{parseFloat(p.cost_price || 0).toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-right font-medium">£{parseFloat(p.retail_price || 0).toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={p.stock_level <= p.reorder_threshold ? "text-red-600 font-medium" : "text-gray-600"}>
                      {p.stock_level}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {p.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}