import { useEffect, useState } from "react";
import api from "../lib/api";

interface Notification {
  id: number;
  title: string;
  body: string;
  category: string;
  is_read: boolean;
  created_at: string;
}

const NotificationsPage = () => {
  const [items, setItems] = useState<Notification[]>([]);

  useEffect(() => {
    api.get("/notifications").then((res) => setItems(res.data.items));
  }, []);

  const markRead = async (id: number) => {
    await api.post(`/notifications/${id}/read`);
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, is_read: true } : item)));
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Thông báo</h1>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="bg-white rounded-2xl shadow p-4 flex justify-between items-center">
            <div>
              <p className="font-semibold">{item.title}</p>
              <p className="text-sm text-slate-600">{item.body}</p>
            </div>
            {!item.is_read && (
              <button className="text-brand-secondary" onClick={() => markRead(item.id)}>
                Đánh dấu đã đọc
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NotificationsPage;
