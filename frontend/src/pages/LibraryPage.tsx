import { useEffect, useState } from "react";
import api from "../lib/api";

interface Topic {
  id: number;
  title: string;
  summary: string;
  period: string;
  topic_type: string;
  tags: string[];
  agent_id: string;
}

interface TopicDetail extends Topic {
  markdown: string;
  documents: { id: number; source: string; period: string; content: string }[];
}

const LibraryPage = () => {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<TopicDetail | null>(null);

  useEffect(() => {
    api.get("/library/topics").then((res) => setTopics(res.data.items));
  }, []);

  const handleSelect = async (topic: Topic) => {
    const { data } = await api.get(`/library/topics/${topic.id}`);
    setSelected(data);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr,2fr]">
      <aside className="bg-white rounded-2xl shadow p-4 space-y-3">
        <h2 className="font-semibold">Danh mục</h2>
        {topics.map((topic) => (
          <button
            key={topic.id}
            className={`w-full text-left px-3 py-2 rounded-lg ${selected?.id === topic.id ? "bg-brand-primary text-white" : "bg-slate-100"}`}
            onClick={() => handleSelect(topic)}
          >
            <p className="font-medium">{topic.title}</p>
            <p className="text-xs text-slate-600">{topic.period}</p>
          </button>
        ))}
      </aside>
      <section className="bg-white rounded-2xl shadow p-6">
        {selected ? (
          <div className="space-y-4">
            <header>
              <p className="text-sm uppercase text-slate-500">{selected.period}</p>
              <h2 className="text-2xl font-semibold">{selected.title}</h2>
              <p className="text-slate-600">{selected.summary}</p>
            </header>
            <article className="text-slate-700 whitespace-pre-line">{selected.markdown}</article>
            <div>
              <h3 className="font-semibold">Nguồn liên quan</h3>
              <ul className="list-disc pl-5 text-sm">
                {selected.documents.map((doc) => (
                  <li key={doc.id}>
                    <a href={doc.source} className="text-brand-secondary" target="_blank" rel="noreferrer">
                      {doc.source}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <p className="text-slate-500">Chọn một chủ đề để xem nội dung chi tiết.</p>
        )}
      </section>
    </div>
  );
};

export default LibraryPage;
