# VietSaga – Học Lịch Sử Việt Nam Bằng Hội Thoại (Multi-Agent + RAG)

> *Tagline:* "Du hành qua các triều đại – Trò chuyện với nhân vật lịch sử."

Toàn bộ giao diện và nội dung người dùng đều bằng tiếng Việt, được thiết kế cho người học Việt Nam.

## 1. Chức năng nổi bật
- **Đăng ký/đăng nhập an toàn** với JWT, quên mật khẩu, refresh token.
- **Timeline hub** hiển thị các triều đại, gợi ý hành trình cá nhân hoá.
- **Chat đa agent**: router chọn agent phù hợp, expert agent trả lời theo persona và citation RAG.
- **Quests & badges** để gamification, theo dõi tiến độ học tập.
- **Library & Search** tra cứu tư liệu markdown đã chuẩn hoá, nhảy thẳng vào chat.
- **Memory & Notifications** giúp tiếp tục bài học và nhận thông báo khi có nội dung mới.

## 2. Công nghệ chính
| Tầng | Công nghệ |
| --- | --- |
| Frontend | React + Vite + TypeScript + Tailwind, React Router, Zustand/TanStack Query |
| Backend | FastAPI + SQLModel/SQLAlchemy, Postgres, Redis, OpenAI SDK |
| AI | OpenAI Chat GPT-4o/mini, embeddings `text-embedding-3-large` |
| RAG | Milvus (vector DB) + Neo4j (knowledge graph) + PDF ingestion script |
| DevOps | Docker Compose, GitHub Actions, logging JSON, backup Postgres/RAG |

## 3. Yêu cầu hệ thống
- Node.js ≥ 20 + pnpm
- Python ≥ 3.11
- Postgres 14+, Redis 6+
- OpenAI API key hợp lệ
- (Tùy chọn) Docker & Docker Compose

## 4. Cài đặt & chạy thử
### 4.1. Sử dụng Docker Compose (khuyến nghị)
1. Sao chép `.env.example` (sẽ cập nhật sau) thành `backend/.env` và `frontend/.env.local`, khai báo biến theo `docs/DEVOPS.prompt`.
2. Bổ sung `OPENAI_API_KEY` (nếu muốn gọi OpenAI thật) và tạo thư mục `rag/` với `meta.json`, `rag_manifest.json` mẫu đã có.
3. Chạy:
   ```bash
   docker compose up --build
   ```
4. API: `http://localhost:8000/api/v1`, Frontend: `http://localhost:5173`.

### 4.2. Chạy thủ công (dev)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

cd ../frontend
pnpm install
pnpm dev -- --open
```
Đảm bảo Postgres & Redis đang chạy, các biến môi trường đã cấu hình.

## 5. Tải dữ liệu RAG & xây đồ thị tri thức
1. Đảm bảo `docker compose up milvus neo4j etcd minio` (hoặc `docker compose up` toàn bộ) đã chạy và sẵn sàng.
2. Chuẩn bị file `rag/viet_nam_su_luoc.pdf` (đã có sẵn trong repo). Các biến môi trường liên quan: `OPENAI_API_KEY`, `MILVUS_HOST`, `GRAPH_URI`, … đã được cấu hình trong `backend/.env`.
3. Từ thư mục `backend`, kích hoạt virtualenv rồi chạy:
   ```bash
   python -m app.scripts.build_rag
   ```
   Script sẽ:
   - Trích xuất và chunk nội dung PDF (`rag_chunk_size`, `rag_chunk_overlap` có thể chỉnh trong `.env`).
   - Gọi OpenAI embedding để tạo vector và đẩy vào Milvus collection `vnhistory_chunks`.
   - Sinh metadata, dựng các node/edge vào Neo4j (Dynasty, Entity, Chunk).
   - Lưu `rag/meta.json` phục vụ debug.
4. Khởi động backend, truy vấn `/api/v1/chat/router` sẽ trả về context thật + đường dẫn suy luận graph. Có thể kiểm tra sức khỏe bằng `/api/v1/admin/rag/health`.

## 6. Quy trình sử dụng web (góc nhìn người dùng)
1. **Đăng ký / đăng nhập**: nhập email, mật khẩu, hoàn tất onboarding.
2. **Trang chủ**: xem lời chào + nút “Tiếp tục học” (dựa trên `/memory/last`), kéo timeline để chọn triều đại.
3. **Bắt đầu chat**:
   - Chọn triều đại → chuyển sang trang Chat với agent tương ứng.
   - Nhập câu hỏi → hệ thống gọi `/router` rồi `/agents/chat`, hiển thị câu trả lời + nguồn tham khảo.
   - Dùng chip gợi ý để đặt câu tiếp theo, đánh giá câu trả lời nếu cần.
4. **Hoàn thành quest**:
   - Vào trang Quests để xem nhiệm vụ hằng ngày, theo triều đại.
   - Khi hoàn thành, nhấn “Đánh dấu hoàn thành” → hệ thống kiểm tra và mở khoá badge.
5. **Tra cứu Library**:
   - Chọn danh mục, đọc markdown, nhấn “Chat với nhân vật này” để chuyển xuống chat.
   - Dùng ô tìm kiếm (search) để tìm tư liệu theo từ khoá.
6. **Xem hồ sơ & thông báo**:
   - Trang Profile hiển thị thời gian học, badge, lịch sử phiên chat.
   - Tại Notifications, xem các thông báo mới về quest, nội dung, bảo trì.
7. **Tiếp tục lần sau**: khi quay lại, thẻ “Tiếp tục với {agent/topic}” giúp trở lại bài dở dang.

Các thông báo, nút, mô tả đều hiển thị tiếng Việt để phù hợp người dùng trong nước.

## 7. Kiểm thử
- Frontend: `pnpm lint && pnpm test` (Vitest + RTL).
- Backend: `pytest --maxfail=1 --cov=app` (unit + integration) theo `docs/TESTING.prompt`.
- Có thể chạy thêm Playwright/K6 nếu muốn E2E & load test.

## 8. Đóng góp
Xem `docs/CONTRIBUTING.md` để nắm quy trình nhánh, commit, review, template PR. Luôn cập nhật tài liệu trong `/docs` khi thay đổi API/prompt.

## 9. Bản quyền & dữ liệu
- Tất cả tư liệu lịch sử phải ghi rõ nguồn, tuân thủ giấy phép. Khi nghi ngờ bản quyền, không đưa vào index.
- Thương hiệu VietSaga có thể được điều chỉnh theo nhu cầu đội sản phẩm.
