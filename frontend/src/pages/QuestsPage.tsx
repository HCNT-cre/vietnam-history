import { useEffect, useState } from "react";
import api from "../lib/api";

interface Quest {
  id: number;
  title: string;
  description: string;
  category: string;
  status: string;
}

const QuestsPage = () => {
  const [quests, setQuests] = useState<Quest[]>([]);

  useEffect(() => {
    api.get("/quests").then((res) => setQuests(res.data.quests));
  }, []);

  const handleComplete = async (questId: number) => {
    await api.post(`/quests/${questId}/progress`, { status: "completed" });
    setQuests((prev) => prev.map((q) => (q.id === questId ? { ...q, status: "completed" } : q)));
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Nhiệm vụ</h1>
      <div className="grid gap-4 md:grid-cols-2">
        {quests.map((quest) => (
          <div key={quest.id} className="bg-white rounded-2xl p-5 shadow">
            <p className="text-sm uppercase text-slate-500">{quest.category}</p>
            <h3 className="text-xl font-semibold">{quest.title}</h3>
            <p className="text-slate-600">{quest.description}</p>
            <button
              onClick={() => handleComplete(quest.id)}
              disabled={quest.status === "completed"}
              className="mt-4 px-4 py-2 rounded-md bg-brand-secondary text-white disabled:bg-slate-300"
            >
              {quest.status === "completed" ? "Đã hoàn thành" : "Đánh dấu hoàn thành"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default QuestsPage;
