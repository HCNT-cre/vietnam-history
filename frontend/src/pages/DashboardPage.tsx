import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import trongDongBanner from "../assets/trong_dong.jpg";

interface TimelineNode {
  id: number;
  slug: string;
  name: string;
  year_range: string;
  start_year?: number | null;
  end_year?: number | null;
  summary: string;
  agent_id: string;
  color: string;
  notable_figures?: string[];
  key_events?: string[];
}

const DashboardPage = () => {
  const [nodes, setNodes] = useState<TimelineNode[]>([]);
  const [currentGroup, setCurrentGroup] = useState<PeriodGroup | null>(null);
  const [selectedNode, setSelectedNode] = useState<TimelineNode | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/timeline").then((res) => setNodes(res.data.nodes));
  }, []);

  const groupedNodes = useMemo(() => groupByPeriod(nodes), [nodes]);
  const currentItems = currentGroup ? currentGroup.items : nodes;
  const stage = selectedNode ? "detail" : currentGroup ? "dynasty" : "group";
  const selectedBanner = trongDongBanner;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <section
        className="rounded-2xl p-6 shadow text-white"
        style={{
          backgroundImage: `linear-gradient(120deg, rgba(15,23,42,0.85), rgba(15,23,42,0.55)), url(${selectedBanner})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <h2 className="text-2xl font-semibold">Chào mừng quay lại mô hình tương tác lịch sử</h2>
        <p className="text-slate-100 max-w-2xl mb-6">
          Bạn muốn trò chuyện với ai hôm nay? Chọn một trong hai lựa chọn dưới đây để bắt đầu hành trình khám phá lịch sử Việt Nam.
        </p>
        
        {/* 2 Options chính */}
        <div className="grid md:grid-cols-2 gap-4 mt-6">
          <button
            onClick={() => navigate('/chat?mode=advisor')}
            className="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded-2xl p-6 text-left hover:bg-white/20 transition group"
          >
            <div className="text-4xl mb-3">🎓</div>
            <h3 className="text-xl font-bold mb-2">Chat với Cố vấn Lịch sử</h3>
            <p className="text-sm text-slate-200">
              Đặt câu hỏi tổng quát về lịch sử Việt Nam, tìm hiểu các sự kiện xuyên suốt thời kỳ.
            </p>
            <div className="mt-4 text-sm font-semibold group-hover:underline">
              Bắt đầu trò chuyện →
            </div>
          </button>

          <button
            onClick={() => {
              // Scroll xuống timeline
              document.getElementById('timeline-section')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded-2xl p-6 text-left hover:bg-white/20 transition group"
          >
            <div className="text-4xl mb-3">👑</div>
            <h3 className="text-xl font-bold mb-2">Chat với Nhân vật Lịch sử</h3>
            <p className="text-sm text-slate-200">
              Chọn triều đại, gặp gỡ các anh hùng dân tộc và trò chuyện theo phong cách nhập vai.
            </p>
            <div className="mt-4 text-sm font-semibold group-hover:underline">
              Xem timeline →
            </div>
          </button>
        </div>
      </section>

      <section id="timeline-section" className="bg-white rounded-2xl p-6 shadow space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">
              {stage === "group" && "Timeline các giai đoạn"}
              {stage === "dynasty" && currentGroup?.label}
              {stage === "detail" && selectedNode?.name}
            </h3>
            <p className="text-sm text-slate-500">
              {stage === "group" && "Chọn một giai đoạn để xem các triều đại tương ứng"}
              {stage === "dynasty" && "Chọn một triều đại để xem chi tiết"}
              {stage === "detail" && selectedNode?.year_range}
            </p>
          </div>
          {stage === "dynasty" && (
            <button
              onClick={() => {
                setCurrentGroup(null);
                setSelectedNode(null);
              }}
              className="text-xs font-semibold text-brand-primary hover:underline"
            >
              ← Quay lại giai đoạn
            </button>
          )}
          {stage === "detail" && (
            <button
              onClick={() => setSelectedNode(null)}
              className="text-xs font-semibold text-brand-primary hover:underline"
            >
              ← Quay lại triều đại
            </button>
          )}
        </div>

        {stage === "group" && (
          <div className="grid gap-4 md:grid-cols-2">
            {groupedNodes.map((group) => (
              <button
                key={group.label}
                type="button"
                onClick={() => {
                  setCurrentGroup(group);
                  setSelectedNode(null);
                }}
                className="rounded-2xl text-left p-4 text-white hover:-translate-y-1 transition"
                style={{ backgroundImage: group.gradient }}
              >
                <p className="text-xs uppercase opacity-80">{group.rangeLabel}</p>
                <h4 className="text-xl font-semibold mt-1">{group.label}</h4>
                <p className="text-sm opacity-90 mt-2">{group.description}</p>
              </button>
            ))}
          </div>
        )}

        {stage === "dynasty" && (
          <div className="grid gap-4 md:grid-cols-2">
            {currentItems.map((node) => (
              <button
                type="button"
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className="rounded-2xl border p-4 text-left transition hover:-translate-y-1 border-slate-200"
              >
                <p className="text-[11px] uppercase text-slate-500">{node.year_range}</p>
                <h4 className="text-lg font-semibold" style={{ color: node.color }}>
                  {node.name}
                </h4>
                <p className="text-sm text-slate-600 line-clamp-3">{node.summary}</p>
                <div className="text-xs text-brand-primary mt-2 font-semibold">Xem chi tiết</div>
              </button>
            ))}
          </div>
        )}

        {stage === "detail" && selectedNode && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-sm text-slate-500">
                {selectedNode.name} · {selectedNode.year_range}
              </p>
              <button
                onClick={() =>
                  navigate(`/chat?agent=${selectedNode.agent_id}&hero=${encodeURIComponent(selectedNode.name)}`)
                }
                className="px-4 py-2 rounded-xl bg-brand-primary text-white text-sm font-semibold hover:bg-brand-primary/90 transition"
              >
                Trò chuyện với agent
              </button>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="space-y-3">
                <h4 className="font-semibold text-slate-800">Nhân vật tiêu biểu</h4>
                {selectedNode.notable_figures && selectedNode.notable_figures.length > 0 ? (
                  <div className="space-y-2 max-h-[220px] overflow-y-auto pr-2">
                    {selectedNode.notable_figures.map((figure) => (
                      <div key={figure} className="rounded-xl border border-slate-200 p-3 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-slate-800">{figure}</p>
                          <p className="text-xs text-slate-500">Gắn với giai đoạn {selectedNode.name}</p>
                        </div>
                        <button
                          onClick={() => navigate(`/chat?agent=${selectedNode.agent_id}&hero=${encodeURIComponent(figure)}`)}
                          className="text-xs font-semibold text-brand-primary hover:underline"
                        >
                          Hỏi nhân vật
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">Chưa có dữ liệu về nhân vật tiêu biểu.</p>
                )}
              </div>
              <div className="space-y-3">
                <h4 className="font-semibold text-slate-800">Sự kiện chính</h4>
                {selectedNode.key_events && selectedNode.key_events.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 max-h-[220px] overflow-y-auto pr-2">
                    {selectedNode.key_events.map((event) => (
                      <li key={event}>{event}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">Chưa có dữ liệu sự kiện.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

export default DashboardPage;

type TimelineGroup = {
  label: string;
  description: string;
  rangeLabel: string;
  items: TimelineNode[];
};

const groupByPeriod = (nodes: TimelineNode[]): TimelineGroup[] => {
  const groups: TimelineGroup[] = [
    {
      label: "Thượng cổ - Bắc thuộc",
      description: "Từ Hồng Bàng đến các cuộc khởi nghĩa Hai Bà Trưng.",
      rangeLabel: "2879 TCN - thế kỷ X",
      accent: "bg-indigo-100 text-indigo-700",
      gradient: "linear-gradient(135deg,#312e81,#6d28d9)",
      items: [],
    },
    {
      label: "Trung đại",
      description: "Từ thời tự chủ đầu tiên đến thời Trịnh-Nguyễn phân tranh.",
      rangeLabel: "Thế kỷ X - XVIII",
      accent: "bg-teal-100 text-teal-700",
      gradient: "linear-gradient(135deg,#0f766e,#14b8a6)",
      items: [],
    },
    {
      label: "Cận đại",
      description: "Từ nhà Tây Sơn, nhà Nguyễn đến Pháp thuộc.",
      rangeLabel: "Thế kỷ XVIII - XX",
      accent: "bg-amber-100 text-amber-700",
      gradient: "linear-gradient(135deg,#92400e,#f59e0b)",
      items: [],
    },
    {
      label: "Hiện đại",
      description: "Từ Cách mạng tháng Tám đến Việt Nam hiện nay.",
      rangeLabel: "1945 - nay",
      accent: "bg-rose-100 text-rose-700",
      gradient: "linear-gradient(135deg,#881337,#fb7185)",
      items: [],
    },
  ];

  nodes.forEach((node) => {
    const start = node.start_year ?? 0;
    if (start < 1000) {
      groups[0].items.push(node);
    } else if (start < 1600) {
      groups[1].items.push(node);
    } else if (start < 1900) {
      groups[2].items.push(node);
    } else {
      groups[3].items.push(node);
    }
  });

  return groups.filter((group) => group.items.length > 0);
};
