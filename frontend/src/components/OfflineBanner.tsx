import { useState, useEffect } from "react";

export default function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  if (online) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-amber-500 text-white text-center py-2 text-sm font-medium z-50">
      📴 You are offline — notes will sync when connection is restored
    </div>
  );
}