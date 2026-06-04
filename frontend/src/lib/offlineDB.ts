/**
 * IndexedDB wrapper for offline support.
 * Stores: notes queue (pending sync), local data cache.
 */

const DB_NAME = "wellness_os";
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("notes_queue")) {
        db.createObjectStore("notes_queue", { keyPath: "sync_id" });
      }
      if (!db.objectStoreNames.contains("offline_cache")) {
        db.createObjectStore("offline_cache", { keyPath: "key" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function queueOfflineNote(note: {
  sync_id: string;
  customer_id: string;
  content: string;
  note_type: string;
  created_at: string;
}): Promise<void> {
  const db = await openDB();
  const tx = db.transaction("notes_queue", "readwrite");
  tx.objectStore("notes_queue").add({ ...note, queued_at: new Date().toISOString() });
  return new Promise((res, rej) => {
    tx.oncomplete = () => { db.close(); res(); };
    tx.onerror = () => { db.close(); rej(tx.error); };
  });
}

export async function getQueuedNotes(): Promise<any[]> {
  const db = await openDB();
  const tx = db.transaction("notes_queue", "readonly");
  const req = tx.objectStore("notes_queue").getAll();
  return new Promise((res, rej) => {
    req.onsuccess = () => { db.close(); res(req.result); };
    req.onerror = () => { db.close(); rej(req.error); };
  });
}

export async function removeQueuedNote(sync_id: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction("notes_queue", "readwrite");
  tx.objectStore("notes_queue").delete(sync_id);
  return new Promise((res, rej) => {
    tx.oncomplete = () => { db.close(); res(); };
    tx.onerror = () => { db.close(); rej(tx.error); };
  });
}

export async function syncQueuedNotes(api: typeof import("../lib/api").default): Promise<{ synced: number; failed: number }> {
  const queue = await getQueuedNotes();
  let synced = 0, failed = 0;
  for (const note of queue) {
    try {
      await api.post(`/customers/${note.customer_id}/notes`, {
        content: note.content,
        note_type: note.note_type,
        sync_id: note.sync_id,
      });
      await removeQueuedNote(note.sync_id);
      synced++;
    } catch {
      failed++;
    }
  }
  return { synced, failed };
}