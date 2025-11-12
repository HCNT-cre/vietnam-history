# Hướng dẫn Deploy VietSaga

## 📦 Ports mới (tránh conflict)
- Backend: **8001** (thay vì 8000)
- Frontend: **5174** (thay vì 5173)
- Postgres: **5433** (thay vì 5432)
- Redis: **6380** (thay vì 6379)

## 🚀 Deploy trên server

### 1. Clone repo
```bash
git clone <your-repo-url>
cd LeHongPhong
```

### 2. Tạo file .env

**backend/.env:**
```bash
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql://viet:password@postgres:5432/vietsaga
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<generate-random-32-chars>
ACCESS_TOKEN_EXPIRES=3600
REFRESH_TOKEN_EXPIRES=1209600
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=gpt-4o-mini
TEMPERATURE=0.3
ALLOWED_ORIGINS=http://your-domain.com,https://your-domain.com
LOG_LEVEL=info
EOF
```

**frontend/.env.local:**
```bash
cat > frontend/.env.local << 'EOF'
VITE_API_BASE=http://localhost:8001/api/v1
VITE_APP_VERSION=production
EOF
```

### 3. Chạy Docker
```bash
docker compose up -d
```

### 4. Migration database
```bash
# Chờ services khởi động
sleep 10

# Thêm columns mới
docker compose exec postgres psql -U viet -d vietsaga -c \
  "ALTER TABLE chatsession ADD COLUMN IF NOT EXISTS hero_name VARCHAR(255) DEFAULT 'Cố vấn lịch sử';"

docker compose exec postgres psql -U viet -d vietsaga -c \
  "ALTER TABLE chatsession ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"

# Update hero_name cho data cũ (nếu có)
docker compose exec backend python -m app.scripts.migrate_hero_name
```

### 5. Kiểm tra
```bash
# Check services
docker compose ps

# Test health
curl http://localhost:8001/healthz

# Check logs
docker compose logs -f
```

### 6. Truy cập
- Frontend: http://localhost:5174
- Backend API: http://localhost:8001/api/v1
- Postgres: localhost:5433
- Redis: localhost:6380

## 🔧 Services cần thiết

✅ **Chỉ cần 4 services:**
- backend (FastAPI + OpenAI)
- frontend (React + Vite)
- postgres (Database)
- redis (Cache + tokens)

❌ **KHÔNG cần:**
- milvus, neo4j, etcd, minio (đã fake bằng LLM)

## 🔒 Production checklist

- [ ] Đổi JWT_SECRET thành random string
- [ ] Đổi Postgres password
- [ ] Update ALLOWED_ORIGINS với domain thật
- [ ] Setup HTTPS (nginx + Let's Encrypt)
- [ ] Set LOG_LEVEL=warning
- [ ] Backup database định kỳ

