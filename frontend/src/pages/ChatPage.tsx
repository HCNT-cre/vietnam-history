import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../lib/api";
import { getHeroByAgent } from "../data/dynasties";
import trongDongBg from "../assets/trong_dong.jpg";
import userAvatar from "../assets/user.png";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ContextChunk = {
  chunk_id: number;
  text: string;
  source: string;
  excerpt?: string;
  dynasty?: string;
  entities?: string[];
  score?: number;
};

type GraphLink = {
  relation: string;
  description: string;
  chunk_id?: number;
};

interface Message {
  role: "assistant" | "user";
  content: string;
  isStreaming?: boolean;
}

interface Conversation {
  id: number;
  agent_id: string;
  hero_name: string;
  topic?: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
}

const ChatPage = () => {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [contextChunks, setContextChunks] = useState<ContextChunk[]>([]);
  const [graphLinks, setGraphLinks] = useState<GraphLink[]>([]);
  const [flagWarning, setFlagWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [isExtractingCitations, setIsExtractingCitations] = useState(false);
  const hasInitialized = useRef(false);
  const mode = params.get("mode"); // 'advisor' hoặc null
  const agentFromQuery = params.get("agent") ?? (mode === "advisor" ? "agent_general_search" : null);
  const heroFromQuery = params.get("hero");

  const heroPersona = useMemo(() => agentFromQuery ? getHeroByAgent(agentFromQuery) : null, [agentFromQuery]);

  // Load danh sách conversations
  const loadConversations = useCallback(async () => {
    try {
      const res = await api.get("/conversations");
      setConversations(res.data);
    } catch (err) {
      console.error("Không thể load conversations:", err);
    }
  }, []);

  // Load history của conversation
  const loadConversationHistory = useCallback(async (conv: Conversation) => {
    try {
      const res = await api.get(`/conversations/${conv.id}/messages`);
      setCurrentConversation(res.data.conversation);
      setMessages(res.data.messages.map((msg: any) => ({
        role: msg.role as "assistant" | "user",
        content: msg.content,
      })));
      setContextChunks([]);
      setGraphLinks([]);
      setFlagWarning(null);
    } catch (err) {
      console.error("Không thể load history:", err);
    }
  }, []);

  // Xóa conversation
  const deleteConversation = useCallback(async (convId: number) => {
    if (!confirm("Bạn có chắc muốn xóa cuộc trò chuyện này?")) return;
    try {
      await api.delete(`/conversations/${convId}`);
      await loadConversations();
      if (currentConversation?.id === convId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Không thể xóa conversation:", err);
    }
  }, [currentConversation, loadConversations]);

  // Load introduction cho conversation mới
  const loadIntroduction = useCallback(async (conv: Conversation) => {
    try {
      const res = await api.post("/agents/suggestions", {
        agent_id: conv.agent_id,
        hero_name: conv.hero_name,
      });
      setMessages([{ role: "assistant", content: res.data.greeting }]);
    } catch (err) {
      const greeting = conv.hero_name
        ? `Chào con, ta là ${conv.hero_name}. Con muốn hỏi điều chi về thời kỳ của ta?`
        : "Chào con, ta là cố vấn lịch sử. Con đang tò mò điều gì?";
      setMessages([{ role: "assistant", content: greeting }]);
    }
  }, []);

  // Tạo conversation mới (manual)
  const createConversation = useCallback(async (customAgentId?: string, customHeroName?: string) => {
    const targetAgent = customAgentId || agentFromQuery;
    const targetHero = customHeroName || heroFromQuery || heroPersona?.name || "Cố vấn lịch sử";
    
    if (!targetAgent) {
      alert("Vui lòng chọn agent để tạo cuộc trò chuyện!");
      return;
    }

    console.log("Creating conversation:", targetAgent, targetHero);

    try {
      const res = await api.post("/conversations", {
        agent_id: targetAgent,
        hero_name: targetHero,
        topic: null,
      });
      setCurrentConversation(res.data);
      setMessages([]);
      await loadConversations();
      await loadIntroduction(res.data);
    } catch (err) {
      console.error("Không thể tạo conversation:", err);
    }
  }, [agentFromQuery, heroFromQuery, heroPersona, loadConversations, loadIntroduction]);

  const askQuestion = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      if (!question) return;
      
      // Kiểm tra có conversation chưa
      if (!currentConversation) {
        alert("Vui lòng tạo cuộc trò chuyện mới trước!");
        return;
      }

      const history: Message[] = [...messages, { role: "user" as const, content: question }];
      setMessages(history);
      setInput("");
      setLoading(true);
      setError(null);
      
      // Clear context cũ
      setContextChunks([]);
      setGraphLinks([]);
      setIsExtractingCitations(false);
      
      try {
        // Tạo message streaming rỗng
        const streamingMessage: Message = { 
          role: "assistant", 
          content: "", 
          isStreaming: true 
        };
        setMessages((prev) => [...prev, streamingMessage]);
        
        // Gọi streaming API
        const baseURL = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";
        // Get token từ store thay vì localStorage
        const token = (await import("../store/auth")).useAuthStore.getState().accessToken;
        
        const response = await fetch(`${baseURL}/agents/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({
            agent_id: currentConversation.agent_id,
            query: question,
            session_id: currentConversation.id,
          }),
        });

        if (!response.ok) {
          throw new Error("Request failed");
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullAnswer = "";

        while (reader) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") break;

              try {
                const parsed = JSON.parse(data);
                
                if (parsed.type === "content") {
                  // Streaming content
                  fullAnswer += parsed.content;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      role: "assistant",
                      content: fullAnswer,
                      isStreaming: true,
                    };
                    return newMessages;
                  });
                } else if (parsed.type === "metadata") {
                  // Streaming chat xong, tắt cursor
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      role: "assistant",
                      content: fullAnswer,
                      isStreaming: false,
                    };
                    return newMessages;
                  });
                  
                  // Hiển thị loading cho citations
                  setIsExtractingCitations(true);
                  
                  // Delay một chút rồi mới hiển thị (để thấy loading animation)
                  setTimeout(() => {
                    setContextChunks(parsed.sources || []);
                    setGraphLinks(parsed.graph_links || []);
                    setIsExtractingCitations(false);
                  }, 500);
                } else if (parsed.type === "error") {
                  throw new Error(parsed.message);
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
        
        // Refresh conversation list
        await loadConversations();
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? "Không thể kết nối tới hệ thống.";
        setError(detail);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Xin lỗi, hệ thống truy vấn đang gặp sự cố. Hãy thử lại sau ít phút.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [currentConversation, messages, loadConversations],
  );

  const handleSend = () => {
    void askQuestion(input);
  };

  // Load conversations khi mount
  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  // Auto-create chỉ khi mode=advisor hoặc có agent từ timeline  
  useEffect(() => {
    // Đã init rồi thì skip
    if (hasInitialized.current) {
      return;
    }

    // Nếu vào /chat trực tiếp từ menu (không có params) → KHÔNG làm gì
    if (!mode && !agentFromQuery) {
      hasInitialized.current = true;
      return;
    }

    // Đợi load conversations xong
    if (conversations.length === 0) {
      return;
    }

    const initConversation = async () => {
      hasInitialized.current = true;
      
      // Nếu vào từ Dashboard "Chat với cố vấn" (mode=advisor)
      if (mode === "advisor") {
        const existing = conversations.find(c => c.agent_id === "agent_general_search");
        if (existing) {
          await loadConversationHistory(existing);
        } else {
          // Tạo mới conversation với cố vấn
          await createConversation("agent_general_search", "Cố vấn lịch sử");
        }
        return;
      }

      // Nếu vào từ Timeline với agent cụ thể
      if (agentFromQuery && agentFromQuery !== "agent_general_search") {
        const existing = conversations.find(c => c.agent_id === agentFromQuery);
        if (existing) {
          await loadConversationHistory(existing);
        } else {
          // Tạo conversation mới với nhân vật từ timeline
          await createConversation();
        }
        return;
      }
    };

    void initConversation();
  }, [mode, agentFromQuery, conversations, createConversation, loadConversationHistory]);

  return (
    <div className="flex gap-4">
      {/* Sidebar conversations */}
      {showSidebar && (
        <aside className="w-80 bg-white rounded-2xl shadow p-4 h-[85vh] flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg">Cuộc trò chuyện</h2>
            <button
              onClick={() => setShowSidebar(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>
          
          <button
            onClick={() => {
              // Prompt user để chọn loại conversation
              const choice = confirm("Tạo cuộc trò chuyện mới?\n\nOK = Với Cố vấn lịch sử\nCancel = Chọn từ Timeline");
              if (choice) {
                createConversation("agent_general_search", "Cố vấn lịch sử");
              } else {
                navigate('/');
              }
            }}
            className="w-full bg-brand-primary text-white py-2 px-4 rounded-xl font-semibold mb-4 hover:bg-brand-primary/90"
          >
            + Trò chuyện mới
          </button>

          <div className="flex-1 overflow-y-auto space-y-2">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <div className="text-4xl mb-2">💬</div>
                <p className="text-sm">Chưa có cuộc trò chuyện nào</p>
                <p className="text-xs mt-1">Tạo mới để bắt đầu</p>
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`p-3 rounded-xl border cursor-pointer hover:bg-slate-50 ${
                    currentConversation?.id === conv.id
                      ? "border-brand-primary bg-brand-primary/5"
                      : "border-slate-200"
                  }`}
                  onClick={() => loadConversationHistory(conv)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm">{conv.hero_name}</h3>
                      <p className="text-xs text-slate-500 mt-1">
                        {conv.message_count} tin nhắn
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="text-red-400 hover:text-red-600 text-sm"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
      )}

      {/* Main chat area */}
      <div className="flex-1 space-y-6">
        {!showSidebar && (
          <button
            onClick={() => setShowSidebar(true)}
            className="bg-white px-4 py-2 rounded-xl shadow text-sm font-semibold"
          >
            ☰ Hiện danh sách
          </button>
        )}

        {/* Empty state khi không có conversation nào được chọn */}
        {!currentConversation && (
          <section className="bg-white rounded-2xl p-12 shadow text-center">
            <div className="text-6xl mb-4">💬</div>
            <h2 className="text-2xl font-bold mb-2">Chưa có cuộc trò chuyện nào được chọn</h2>
            <p className="text-slate-600 mb-6">
              Chọn một cuộc trò chuyện từ danh sách bên trái, hoặc tạo cuộc trò chuyện mới.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => navigate('/')}
                className="bg-slate-100 text-slate-700 px-6 py-3 rounded-xl font-semibold hover:bg-slate-200"
              >
                ← Về trang chủ
              </button>
              <button
                onClick={() => createConversation("agent_general_search", "Cố vấn lịch sử")}
                className="bg-brand-primary text-white px-6 py-3 rounded-xl font-semibold hover:bg-brand-primary/90"
              >
                Chat với Cố vấn
              </button>
            </div>
          </section>
        )}

        {currentConversation && (
          <>
        <section className="rounded-2xl p-6 shadow relative overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `linear-gradient(120deg, rgba(15,23,42,.9), rgba(15,23,42,.6)), url(${trongDongBg})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="relative z-10 flex items-center gap-4 text-white">
          <img
            src={heroPersona?.image ?? userAvatar}
            alt={currentConversation?.hero_name ?? heroPersona?.name ?? "Nhân vật"}
            className="h-28 w-28 rounded-3xl object-cover border-2 border-white shadow-lg"
          />
          <div>
            <p className="text-sm uppercase tracking-wide text-slate-200">Đang trò chuyện</p>
            <h1 className="text-2xl font-semibold">
              {currentConversation?.hero_name ?? heroPersona?.name ?? "Nhân vật tương tác lịch sử"}
            </h1>
            <p className="text-slate-200 text-sm">{heroPersona?.title ?? "Cố vấn lịch sử"}</p>
          </div>
        </div>
      </section>

      <div className="space-y-4">
        <section
          className="bg-white/95 rounded-2xl shadow p-6 flex flex-col h-[60vh] relative overflow-hidden"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.9)), url(${trongDongBg})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.map((msg, index) => (
              <MessageCard
                key={`msg-${index}-${msg.role}`}
                message={msg}
                heroImage={heroPersona?.image ?? userAvatar}
              />
            ))}
            {loading && (
              <ThinkingIndicator
                heroImage={heroPersona?.image ?? userAvatar}
              />
            )}
          </div>
          <div className="mt-4 flex flex-col gap-3">
            <div className="flex gap-2">
              <textarea
                className="flex-1 border rounded-2xl p-3 bg-slate-50"
                rows={3}
                placeholder="Nhập câu hỏi của bạn..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <button
                className="bg-brand-secondary text-white px-4 rounded-2xl font-semibold disabled:opacity-50"
                onClick={handleSend}
                disabled={loading || !currentConversation}
                title={!currentConversation ? "Vui lòng tạo cuộc trò chuyện mới" : ""}
              >
                {loading ? "Đang gửi..." : "Gửi"}
              </button>
            </div>
          </div>
        </section>

        {/* Tư liệu và Mối quan hệ - 2 cột */}
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Tư liệu tham khảo */}
          <aside className="bg-white rounded-2xl shadow p-6 space-y-4">
            <div>
              <h3 className="font-semibold text-lg mb-1">📚 Tư liệu tham khảo</h3>
              <p className="text-xs text-slate-500">Các đoạn trích từ tài liệu lịch sử</p>
            </div>
            {isExtractingCitations ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin text-3xl mb-2">📖</div>
                <p className="text-sm text-brand-primary font-semibold">Đang trích dẫn tư liệu...</p>
                <p className="text-xs text-slate-400 mt-1">Phân tích nguồn từ câu trả lời</p>
              </div>
            ) : contextChunks.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <div className="text-3xl mb-2">📖</div>
                <p className="text-sm">Gửi câu hỏi để xem tư liệu</p>
              </div>
            ) : (
              <ul className="space-y-3 text-sm text-slate-700 max-h-[400px] overflow-y-auto pr-2">
                {contextChunks.map((doc, idx) => (
                  <li key={doc.chunk_id || idx} className="border-l-4 border-brand-primary pl-3 py-2 bg-slate-50 rounded-r">
                    <div className="flex items-start justify-between mb-1">
                      <span className="font-semibold text-brand-primary text-xs">
                        {doc.dynasty || "Lịch sử Việt Nam"}
                      </span>
                      {doc.score && (
                        <span className="text-xs text-emerald-600 font-semibold">
                          {(doc.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 text-sm leading-relaxed">{doc.text}</p>
                    <p className="text-xs text-slate-400 mt-1">📄 {doc.source}</p>
                  </li>
                ))}
              </ul>
            )}
            {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
          </aside>

          {/* Mối quan hệ lịch sử */}
          <aside className="bg-white rounded-2xl shadow p-6 space-y-4">
            <div>
              <h3 className="font-semibold text-lg mb-1">🔗 Mối quan hệ lịch sử</h3>
              <p className="text-xs text-slate-500">Các liên kết giữa nhân vật, sự kiện và địa điểm</p>
            </div>
            {isExtractingCitations ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin text-3xl mb-2">🔗</div>
                <p className="text-sm text-brand-secondary font-semibold">Đang phân tích đồ thị...</p>
                <p className="text-xs text-slate-400 mt-1">Xây dựng mối quan hệ</p>
              </div>
            ) : graphLinks.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <div className="text-3xl mb-2">🔗</div>
                <p className="text-sm">Gửi câu hỏi để xem mối quan hệ</p>
              </div>
            ) : (
              <ul className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                {graphLinks.map((link, idx) => (
                  <li key={`${link.relation}-${idx}`} className="border-l-4 border-brand-secondary pl-3 py-2 bg-slate-50 rounded-r">
                    <p className="font-semibold text-brand-secondary text-sm">{link.relation}</p>
                    <p className="text-sm text-slate-700 mt-1 leading-relaxed">{link.description}</p>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </div>
      </>
        )}
      </div>
    </div>
  );
};

const markdownComponents = {
  p: ({ children }: { children: React.ReactNode }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
  strong: ({ children }: { children: React.ReactNode }) => <span className="font-semibold">{children}</span>,
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul className="list-disc pl-5 space-y-1 text-sm">{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol className="list-decimal pl-5 space-y-1 text-sm">{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => <li className="leading-relaxed">{children}</li>,
};

const MessageCard = ({ message, heroImage }: { message: Message; heroImage: string }) => {
  const isAssistant = message.role === "assistant";
  const avatarSizeClass = isAssistant ? "h-16 w-16" : "h-12 w-12";
  return (
    <div className={`flex ${isAssistant ? "items-start gap-3" : "items-start gap-3 flex-row-reverse"}`}>
      <div
        className={`${avatarSizeClass} rounded-3xl overflow-hidden border ${
          isAssistant ? "border-brand-primary/40 shadow-md" : "border-slate-200"
        }`}
      >
        {isAssistant ? (
          <img src={heroImage} alt="Anh hùng" className="h-full w-full object-cover" />
        ) : (
          <div className="h-full w-full bg-brand-primary text-white flex items-center justify-center text-sm font-semibold">
            Bạn
          </div>
        )}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow ${
          isAssistant ? "bg-slate-50 border border-slate-200" : "bg-brand-primary text-white"
        } ${message.isStreaming ? "streaming-cursor" : ""}`}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={markdownComponents}
          className={isAssistant ? "text-slate-800" : "text-white"}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

const ThinkingIndicator = ({ heroImage }: { heroImage: string }) => (
  <div className="flex items-start gap-3">
    <div className="h-16 w-16 rounded-3xl overflow-hidden border border-brand-primary/40 shadow-md">
      <img src={heroImage} alt="Anh hùng" className="h-full w-full object-cover" />
    </div>
    <div className="max-w-[80%] rounded-2xl px-4 py-3 border border-slate-200 bg-gradient-to-r from-brand-primary/5 to-brand-secondary/10 shadow-inner">
      <div className="flex items-center gap-2 py-1" aria-hidden="true">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="h-2 w-2 rounded-full bg-brand-primary animate-bounce"
            style={{ animationDelay: `${dot * 0.15}s` }}
          />
        ))}
      </div>
      <span className="sr-only">Đang soạn phản hồi</span>
    </div>
  </div>
);

// GraphLinkPanel không dùng nữa - đã inline vào main layout

export default ChatPage;
