# Kiến Trúc Hệ Thống VietSaga

## 1. Các thành phần chính
| Lớp | Vai trò | Công nghệ |
| --- | --- | --- |
| SPA Frontend | Giao diện học tập, quản lý token, gọi REST API, render timeline/chat/quests/profile | React + Vite + TS + Tailwind |
| API Gateway | FastAPI xử lý `/api/v1/*`, middleware xác thực, rate limit, error envelope | FastAPI + Uvicorn |
| Auth Service | Đăng ký, đăng nhập, refresh, quên mật khẩu, email verify (stub), token rotation | FastAPI module + Postgres + Redis |
| Learning Service | Timeline, library, quests, badges, notifications, memory | FastAPI routers + Postgres |
| Multi-Agent Service | `/router`, `/agents/chat`, `/agents/feedback` – tải prompt, ghép context, gọi OpenAI | OpenAI SDK |
| RAG Service | Quản lý FAISS `faiss.index`, `meta.json`, manifest, cung cấp API search/retrieve | Python + FAISS |
| Background Jobs | Gửi email, cron cập nhật dữ liệu, reindex RAG | Celery + Redis hoặc APScheduler |
| Observability | Logging JSON, metrics Prometheus, tracing OpenTelemetry | Stack tuỳ môi trường |

## 2. Luồng dữ liệu (mô tả chữ)
```
Trình duyệt → (Auth) → /auth/login → Postgres users + Redis token
Trình duyệt (đã auth) → /timeline /library /quests → cache Redis → Postgres
Chat: FE gửi POST /router → Router Service + OpenAI → JSON agent
       FE gửi POST /agents/chat (agent_id, query, history)
            → RAG.retrieve(query) → FAISS/meta
            → OpenAI Chat (persona + [CONTEXT])
            → Lưu session & used_docs vào Postgres
Sau trả lời → FE gọi /quests/{id}/progress + PUT /memory/last + hiển thị citation.
Thông báo → /notifications (đọc) /notifications/{id}/read
```

## 3. Biên giới module
- `routers/auth.py`: register, login, refresh, logout, reset password.
- `routers/users.py`: me, update profile, history.
- `routers/timeline.py`: danh sách triều đại, hành trình gợi ý.
- `routers/library.py`: topics, documents, markdown, search proxy.
- `routers/chat.py`: router, agents/chat, feedback.
- `routers/quests.py`, `routers/badges.py`.
- `routers/memory.py`, `routers/notifications.py`.
- `routers/admin.py`: health RAG, trigger reindex (đòi API key riêng).

## 4. Lưu trữ dữ liệu
- **Postgres**: `users`, `sessions`, `messages`, `quests`, `user_quests`, `badges`, `user_badges`, `notifications`, `user_notifications`, `memory`, `timeline_nodes`, `library_topics`, `library_docs`.
- **Redis**: cache timeline/library, lưu refresh token JTI, rate limit.
- **RAG folder/S3**: `faiss.index`, `meta.json`, `rag_manifest.json`.

## 5. Xác thực & phân quyền
1. `/auth/login` trả `access_token` (1h) + `refresh_token` (14 ngày).
2. Middleware đọc header `Authorization: Bearer ...`, giải JWT, nạp `current_user`.
3. Refresh rotation: mỗi lần refresh tạo token mới, đánh dấu token cũ đã dùng.
4. Các route yêu cầu role admin (ví dụ `/admin`) kiểm tra `user.role` hoặc API key.

## 6. Multi-agent orchestration
- Prompt master/agent load từ `/docs` khi khởi động (dev) hoặc bundle chung (prod).
- `[CONTEXT]` ghép tối đa 4 đoạn, mỗi đoạn kèm metadata `(doc#id | period | tiêu đề)`.
- Kết quả, token usage, `used_docs` được ghi lại để hiển thị citation + phân tích.
- Feedback endpoint ghi lại đánh giá người dùng cho từng message.

## 7. Chiến lược lỗi & độ bền
| Tình huống | Ứng xử |
| --- | --- |
| OpenAI router trả text lỗi | Parse JSON, nếu thất bại retry 1 lần; cuối cùng fallback `agent_general_search` và log cảnh báo |
| RAG thiếu file | Trả 503 `rag_unavailable`; FE hiển thị banner; DevOps khôi phục từ backup |
| Token hết hạn | 401 `token_expired`; FE tự gọi `/auth/token/refresh` |
| Rate limit | 429 + header `Retry-After` |
| DB lỗi | Circuit breaker + thông báo maintenance |

## 8. Triển khai (mô tả chữ)
```
[CDN/Nginx]
   ↳ phục vụ static FE (VietSaga SPA)
   ↳ reverse proxy tới [FastAPI pods]
          |--> Postgres (primary + replica)
          |--> Redis cluster
          |--> RAG volume (read-only)
          |--> OpenAI API
Background jobs chạy tách container (Celery worker) dùng chung Redis.
```

## 9. Quan sát
- Log JSON: `{ts, trace_id, user_id, route, status, duration_ms, agent_id, rag_hits}`.
- Metrics: `http_requests_total`, `openai_latency_ms`, `rag_hits_ratio`, `auth_login_failures`.
- Tracing: Router span → Agent span để dễ debug.

## 10. Bảo mật
- HTTPS, HSTS, CSP nghiêm ngặt.
- Hash Argon2id + salt; không lưu mật khẩu gốc.
- Không log nội dung đầy đủ người dùng (chỉ snippets cần thiết cho debug, đã mask).
- Quản lý secret qua secret manager, rotate 60 ngày/lần.
- Backup Postgres hàng ngày, RAG manifest version.

## 11. Khả năng mở rộng
- FastAPI pods stateless → scale ngang.
- RAG interface chuẩn bị chuyển sang pgvector khi chunk > 20k.
- Timeline/quests cache TTL 10 phút để giảm truy vấn.
- Task dài (reindex, email) chuyển sang background jobs.

## 12. Checklist trước release
- [ ] Alembic migration apply thành công.
- [ ] Seed timeline/quests/badges đúng phiên bản.
- [ ] RAG artefact + manifest được mount và `admin/rag/health` báo OK.
- [ ] OpenAI key cấu hình + giám sát usage.
- [ ] CI chạy test FE/BE + build Docker.
- [ ] Monitoring/alert đã cấu hình.
