# CONTRIBUTING.md

## Quy trình làm việc
1. Tạo nhánh từ `main`: `feat/<feature>` hoặc `fix/<issue>`.
2. Nếu thay đổi database, tạo migration (`alembic revision --autogenerate`) và mô tả rõ trong PR.
3. Cập nhật tài liệu `/docs` khi API/prompt/spec thay đổi.
4. Chạy test + lint trước khi commit.
5. Tạo PR với template: mô tả, thay đổi chính, test đã chạy, ảnh chụp màn hình (nếu UI).

## Quy ước commit
- Sử dụng prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`.
- Một commit chỉ nên chứa 1 chủ đề.
- Đảm bảo commit chạy được (không phá build/test).

## Checklist PR
- [ ] Đã đọc lại `PROJECT_OVERVIEW.md` để đảm bảo không lệch tầm nhìn.
- [ ] API thay đổi? → cập nhật `API_SPEC.md` + thông báo cho FE/BE.
- [ ] Database thay đổi? → kèm migration + cập nhật `README`/docs liên quan.
- [ ] Prompt thay đổi? → cập nhật file `.prompt` + nêu rõ lý do.
- [ ] Đã chạy `pnpm lint && pnpm test` (FE) hoặc `pytest` (BE) và đính kèm kết quả.
- [ ] Không commit secret/config nhạy cảm.
- [ ] Logging không chứa dữ liệu cá nhân.

## Code review guidelines
- Ưu tiên kiểm tra đúng spec/API contract, bảo mật (auth, token), và chất lượng RAG integration.
- Đảm bảo có test tương ứng với bug/feature.
- Các nhận xét nhỏ (nit) nên gợi ý thay đổi cụ thể.
- Sẵn sàng hỏi lại khi spec chưa rõ thay vì đoán.

## Issues & support
- Dùng template issue (Bug / Feature). Ghi rõ môi trường, logs, steps to reproduce.
- Sử dụng labels `area:frontend`, `area:backend`, `area:rag`, `priority:p0/p1`.
- Kênh nhanh: Slack `#vietsaga-dev`, ưu tiên nêu trace_id khi báo lỗi hệ thống.
