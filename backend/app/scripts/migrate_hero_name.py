"""
Migration script: Thêm hero_name vào ChatSession cũ
Chạy: python -m app.scripts.migrate_hero_name
"""
from sqlmodel import Session, select

from app.db import engine
from app.models.core import ChatSession


AGENT_TO_HERO_MAP = {
    "agent_hong_bang": "Hùng Vương",
    "agent_bac_thuoc": "Hai Bà Trưng",
    "agent_bac_thuoc_2": "Hai Bà Trưng",
    "agent_ly": "Lý Công Uẩn",
    "agent_tran": "Trần Hưng Đạo",
    "agent_le": "Lê Lợi",
    "agent_hau_le_so": "Lê Lợi",
    "agent_le_so": "Lê Lợi",
    "agent_tay_son": "Quang Trung",
    "agent_nguyen": "Gia Long",
    "agent_can_dai": "Phan Bội Châu",
    "agent_phap_thuoc": "Phan Bội Châu",
    "agent_hien_dai": "Hồ Chí Minh",
    "agent_chxhcn_vn": "Hồ Chí Minh",
    "agent_general_search": "Cố vấn lịch sử",
}


def migrate_hero_names():
    """Update hero_name cho các session cũ."""
    with Session(engine) as session:
        # Lấy tất cả sessions
        sessions = session.exec(select(ChatSession)).all()
        
        updated_count = 0
        for chat_session in sessions:
            # Nếu hero_name đã có và không phải default, bỏ qua
            if chat_session.hero_name and chat_session.hero_name != "Cố vấn lịch sử":
                continue
            
            # Map từ agent_id sang hero name
            hero_name = AGENT_TO_HERO_MAP.get(
                chat_session.agent_id,
                "Cố vấn lịch sử"
            )
            
            # Nếu có topic, dùng topic làm tên
            if chat_session.topic:
                hero_name = chat_session.topic
            
            chat_session.hero_name = hero_name
            session.add(chat_session)
            updated_count += 1
        
        session.commit()
        print(f"✅ Đã cập nhật {updated_count} conversations với hero_name")


if __name__ == "__main__":
    print("🔄 Bắt đầu migration hero_name...")
    migrate_hero_names()
    print("✨ Migration hoàn tất!")

