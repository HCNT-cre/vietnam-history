# Tổng Quan VietSaga

## 1. Tầm nhìn & định vị
VietSaga là nền tảng học lịch sử Việt Nam bằng hội thoại đa nhân vật. Người dùng đăng nhập bằng tài khoản riêng, lựa chọn lộ trình theo triều đại, trò chuyện với agent persona, nhận quest/badge, và tiếp tục hành trình ở bất kỳ thiết bị nào. Sản phẩm hướng tới trải nghiệm hoàn chỉnh: mở rộng được, bảo mật, vận hành ổn định chứ không còn là MVP.

## 2. Giá trị cốt lõi
1. **Nhập vai lịch sử** – Timeline trực quan + persona theo từng triều đại giúp người học “sống trong bối cảnh”.
2. **Đáng tin cậy** – Mọi câu trả lời đều gắn citation từ thư viện RAG đã chuẩn hoá.
3. **Cá nhân hoá** – Bộ nhớ học tập, quest/badge, gợi ý tiếp tục đảm bảo giữ chân người học.
4. **Vận hành chuẩn** – Có auth, phân quyền, logging, monitoring, backup đầy đủ.

## 3. Persona & hành trình
| Persona | Nhu cầu | Trải nghiệm điển hình |
| --- | --- | --- |
| Học sinh THPT | Ôn thi, nhớ sự kiện | Đăng ký → chọn timeline → chat với agent → nhận quest → xem tiến độ |
| Giáo viên | Chuẩn bị tư liệu minh hoạ | Đăng nhập → tìm kiếm Library → lưu/đánh dấu → chia sẻ link |
| Người yêu lịch sử | Đào sâu chủ đề | Nhận thông báo Library mới → đọc → nhảy vào chat ngay |
| Phụ huynh | Theo dõi con học | Xem dashboard profile, tiến độ và badge |

## 4. Phạm vi chức năng phiên bản v1
- Auth: đăng ký, đăng nhập, refresh token, quên mật khẩu, logout.
- Hồ sơ & tuỳ chỉnh: avatar, ngôn ngữ, theme, thống kê, lịch sử học.
- Timeline Hub: danh sách triều đại, hành trình gợi ý, CTA nhảy sang chat/library.
- Multi-agent chat: Router → Expert agent + RAG context, hiển thị citation, cho phép đánh giá câu trả lời.
- Quest & badge: danh mục nhiệm vụ, tracking tiến độ, thông báo unlock.
- Library & search: duyệt markdown chuẩn hoá, lọc, CTA “Chat với nhân vật này”.
- Memory: lưu agent/topic gần nhất, hiển thị ở dashboard & profile.
- Notifications: quest mới, nội dung mới, thông báo hệ thống.

## 5. Công nghệ cốt lõi
| Tầng | Công nghệ | Ghi chú |
| --- | --- | --- |
| Frontend | React + Vite + TypeScript + Tailwind, React Router, Zustand/Context, TanStack Query | Toàn bộ UI hiển thị tiếng Việt |
| Backend | FastAPI + Pydantic + SQLAlchemy/SQLModel, Postgres, Redis, Celery/APS Scheduler | JWT Bearer, logging JSON |
| AI | OpenAI Chat (GPT-4o/mini), Embedding `text-embedding-3-large` | Một model chung, khác prompt/context |
| RAG | FAISS local + `meta.json`, manifest version | Chuẩn bị interface chuyển sang pgvector |
| DevOps | Docker Compose, GitHub Actions CI, logging tập trung, backup | Env quản lý qua `.env` và secret manager |

## 6. Chỉ số thành công
- ≥ 90% người dùng hoàn thành onboarding < 3 phút.
- ≥ 80% câu trả lời kèm citation hợp lệ.
- Tỷ lệ quay lại 7 ngày ≥ 40% nhờ quest/memory.
- Tỷ lệ lỗi backend < 0.5%/ngày.

## 7. Roadmap đề xuất
1. **Sprint 1** – Auth + hồ sơ + timeline/library API.
2. **Sprint 2** – Multi-agent chat + RAG + session logging.
3. **Sprint 3** – Quest/badge + notifications + feedback.
4. **Sprint 4** – Hardening (test, monitoring, Docker release, backup).

## 8. Rủi ro & phương án
| Rủi ro | Ứng phó |
| --- | --- |
| Dữ liệu lịch sử thiếu | Tuân thủ `RAG_DATA_GUIDE.md`, cập nhật manifest định kỳ |
| Chi phí OpenAI cao | Giới hạn top-k, cắt bớt history, cache câu phổ biến |
| Latency cao | Chạy router và RAG chuẩn bị song song, log để tối ưu |
| Bảo mật | Hash Argon2, refresh rotation, rate limit, giám sát log |

## 9. Nguyên tắc trải nghiệm
- Giao diện, copywriting, thông báo đều bằng tiếng Việt.
- Luôn hiển thị nguồn tham khảo rõ ràng, mô tả trích dẫn ngắn gọn.
- Bất kỳ khi nào thiếu context, agent phải thừa nhận và gợi ý câu hỏi khác.
