# Đặc tả API VietSaga (v1)
Tất cả endpoint đều dùng tiền tố `/api/v1`. Trừ khi ghi chú, mọi phản hồi ở định dạng JSON và tiếng Việt.

## 1. Quy ước chung
- `Content-Type`: `application/json; charset=utf-8`.
- Xác thực: `Authorization: Bearer <JWT>` với token truy cập 1 giờ; refresh token 14 ngày. Các endpoint có biểu tượng 🔓 không yêu cầu đăng nhập.
- Mọi lỗi trả về dạng:
  ```json
  {"error":"ma_loi","detail":"Mô tả thân thiện","trace_id":"uuid"}
  ```
- Giới hạn tốc độ: 60 req/phút cho người dùng đã đăng nhập, 10 req/phút cho endpoint công khai.
- Phân trang: cursor-based `?cursor=<opaque>&limit=20`.

## 2. Xác thực & phiên
### 🔓 `POST /auth/register`
Đăng ký tài khoản mới.
```json
{
  "email": "hocvien@example.com",
  "password": "ItNhat12KyTu!",
  "display_name": "Lan Anh",
  "locale": "vi-VN"
}
```
Phản hồi 201:
```json
{"user_id":"usr_123","requires_email_verification":true}
```

### 🔓 `POST /auth/login`
```json
{"email":"hocvien@example.com","password":"..."}
```
Trả về token:
```json
{
  "access_token":"jwt...",
  "refresh_token":"rfr...",
  "expires_in":3600,
  "user":{"id":"usr_123","display_name":"Lan Anh","avatar_url":null}
}
```

### 🔓 `POST /auth/token/refresh`
```json
{"refresh_token":"rfr..."}
```
Trả cặp token mới. Nếu refresh token bị tái sử dụng → `401 token_reused`.

### 🔐 `POST /auth/logout`
Body: `{ "refresh_token": "rfr..." }` hoặc gửi header `X-Refresh-Token`. Invalidate token.

### 🔓 `POST /auth/password/reset/request`
```json
{"email":"hocvien@example.com"}
```
Luôn trả 200.

### 🔓 `POST /auth/password/reset/confirm`
```json
{"token":"reset-token","new_password":"MatKhauMoi1!"}
```

## 3. Hồ sơ người dùng
### 🔐 `GET /users/me`
Thông tin cá nhân, tuỳ chỉnh, thống kê nhanh.

### 🔐 `PATCH /users/me`
Cập nhật `display_name`, `avatar_url`, `preferences` (theme, cỡ chữ, ngôn ngữ).

### 🔐 `GET /users/me/history`
`?cursor=&limit=`. Danh sách phiên học: `{ "session_id", "agent_id", "topic", "duration_minutes", "updated_at" }`.

## 4. Timeline & thư viện
### 🔐 `GET /timeline`
Danh sách node triều đại:
```json
{"nodes":[{"id":"dyn_ly","name":"Nhà Lý","year_range":"1009-1225","agent_id":"agent_ly","summary":"...","color":"#6B7280"}]}
```

### 🔐 `GET /library/topics`
Tham số: `?period=Tran&type=event&cursor=...`.

### 🔐 `GET /library/topics/{topic_id}`
Trả markdown, metadata, danh sách document con, agent gợi ý.

### 🔐 `GET /library/documents/{doc_id}`
Dùng để map `used_docs` → nguồn hiển thị ở FE.

## 5. Search & RAG
### 🔐 `POST /search`
```json
{"query":"Chiếu dời đô","top_k":4,"filters":{"period":["Ly"],"type":["event"]}}
```
Trả danh sách `docs` (id, text, source, period, type, tags).

## 6. Hội thoại multi-agent
### 🔐 `POST /router`
```json
{
  "messages":[{"role":"user","content":"Ai dời đô về Thăng Long?"}],
  "user_context":{"current_agent":"agent_general_search","language":"vi"}
}
```
Phản hồi:
```json
{"call_agent":"agent_ly","query_to_agent":"Chiếu dời đô và Lý Công Uẩn"}
```

### 🔐 `POST /agents/chat`
```json
{
  "agent_id":"agent_ly",
  "query":"Chiếu dời đô diễn ra thế nào?",
  "history":[{"role":"user","content":"..."}],
  "metadata":{"session_id":"ses_abc"}
}
```
Kết quả:
```json
{
  "answer":"...",
  "used_docs":[12,34],
  "session_id":"ses_abc",
  "tokens":{"prompt":1200,"completion":350}
}
```

### 🔐 `POST /agents/feedback`
```json
{"session_id":"ses_abc","message_id":"msg_3","rating":1,"notes":"Thiếu nguồn"}
```

## 7. Quest, badge & tiến độ
### 🔐 `GET /quests`
Trả các quest theo nhóm `daily`, `dynasty`, `story_arc`. Mỗi quest gồm `id`, `title`, `description`, `status`, `reward_badge_id`.

### 🔐 `POST /quests/{quest_id}/progress`
```json
{"status":"completed","evidence":"ses_abc"}
```
Hoàn thành quest, có thể unlock badge.

### 🔐 `GET /badges`
`{"earned":[...],"available":[...]}`.

### 🔐 `GET /progress/summary`
Thông kê cho dashboard/profile (phút học theo triều đại, streak, quest). Endpoint cũ `/progress/quests/check` vẫn hỗ trợ cho tới khi FE cập nhật.

## 8. Memory & gợi ý tiếp tục
### 🔐 `GET /memory/last`
```json
{"agent_id":"agent_tran","topic":"Kháng chiến chống Nguyên Mông","updated_at":"2025-01-20T10:30:00Z"}
```

### 🔐 `PUT /memory/last`
```json
{"agent_id":"agent_tran","topic":"Trần Hưng Đạo","session_id":"ses_abc"}
```

## 9. Thông báo
### 🔐 `GET /notifications`
Trả danh sách thông báo chưa đọc + đã đọc (có phân trang).

### 🔐 `POST /notifications/{id}/read`
Đánh dấu đã đọc.

## 10. Admin / vận hành
### 🔐 `GET /admin/rag/health`
Yêu cầu header `X-Admin-Token`. Phản hồi tình trạng index/meta/manifest.

### 🔐 `POST /admin/rag/reindex`
Trigger job tái tạo chỉ mục (trả về trạng thái hàng đợi).

### 🔐 `GET /admin/analytics/usage`
Thống kê sử dụng (chỉ nội bộ).

## 11. Bảng mã lỗi
| Mã | HTTP | Diễn giải | Hướng xử lý |
| --- | --- | --- | --- |
| `invalid_payload` | 422 | Dữ liệu thiếu/hỏng | Kiểm tra body trước khi gửi |
| `invalid_credentials` | 401 | Sai email/mật khẩu | Nhắc người dùng nhập lại |
| `token_expired` | 401 | Access token hết hạn | Gọi `/auth/token/refresh` |
| `token_reused` | 401 | Refresh token tái sử dụng | Buộc đăng nhập lại |
| `rate_limited` | 429 | Vượt giới hạn | Hiện thông báo chờ |
| `rag_unavailable` | 503 | Chưa tải được FAISS/meta | Đội vận hành khôi phục |
| `agent_not_found` | 404 | Agent không hợp lệ | Đồng bộ lại enum FE |
| `openai_router_failure` | 502 | Router không parse được JSON | Tự retry + báo dev nếu lặp |
| `openai_agent_timeout` | 504 | OpenAI trả lời quá chậm | Hiện toast xin thử lại |
| `internal_error` | 500 | Lỗi không xác định | Ghi `trace_id`, báo dev |

## 12. Hành trình chuẩn (E2E)
1. Người dùng đăng ký, xác minh email, đăng nhập.
2. FE tải `/users/me`, `/timeline`, `/quests`, `/badges` song song.
3. Người dùng chọn triều đại → FE gọi `/memory/last` (nếu có) để hiển thị “tiếp tục”.
4. Gửi câu hỏi: `/router` → `/agents/chat` → nhận câu trả lời + citation.
5. FE gọi `/quests/{id}/progress` và `PUT /memory/last`.
6. Người dùng xem profile `/progress/summary`, lịch sử `/users/me/history`.
7. Khi có thông báo mới, FE poll `/notifications` hoặc dùng SSE (tuỳ roadmap).
8. Logout hoặc hết phiên → gọi `/auth/logout` để vô hiệu token.

## 13. Kiểm soát bảo mật
- Token ký HMAC SHA256 (`JWT_ALG=HS256`), secret tối thiểu 32 ký tự.
- Password hash Argon2id, kiểm tra độ mạnh trước khi lưu.
- Ghi log mọi thao tác quan trọng kèm `trace_id`, `user_id`.
- CORS chỉ cho phép domain cấu hình.
