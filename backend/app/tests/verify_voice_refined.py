from dataclasses import dataclass
import unicodedata

# --- Copied from chat.py (simplified & updated) ---

@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    persona_name: str
    period_label: str
    year_range: str | None
    summary: str
    notable_figures: tuple[str, ...]
    key_events: tuple[str, ...]

@dataclass(frozen=True)
class VoiceSetting:
    pronoun: str
    audience: str
    tone_hint: str
    greeting_template: str

VOICE_DEFAULT = VoiceSetting(
    pronoun="ta",
    audience="con",
    tone_hint="giọng kể điềm đạm",
    greeting_template="Chào {audience}, ta là {persona}.",
)

ANCESTRAL_KEYWORDS = ("hồng bàng", "hùng vương", "lạc long quân", "âu lạc")
ROYAL_TOKENS = ("hoàng đế", "vua", "đại vương", "thái tổ", "thái tông", "nhân tông", "thánh tông", "minh mạng", "tự đức")
COMMANDER_KEYWORDS = ("tướng", "khởi nghĩa", "nghĩa quân", "quốc công", "trận", "chiến", "đạo", "tiết chế")
REVOLUTION_KEYWORDS = (
    "cách mạng", "chủ tịch", "việt minh", "độc lập", 
    "xã hội chủ nghĩa", "kháng chiến chống pháp", "kháng chiến chống mỹ", 
    "kháng chiến chống thực dân", "kháng chiến chống đế quốc",
    "giải phóng", "đảng cộng sản"
)
MODERN_KEYWORDS = (
    "hiện đại", "thế kỷ 20", "thế kỷ 21", "cộng hòa", "tổng thống", "thủ tướng", "đổi mới"
)
SCHOLAR_KEYWORDS = ("sĩ phu", "nhà nho", "khoa bảng", "văn hiến", "học giả", "thi cử", "nho học", "công thần")
ELDER_KEYWORDS = ("hồ chí minh", "bác hồ", "nguyễn ái quốc")
CONTROVERSIAL_KEYWORDS = ("ngô đình diệm", "nguyễn văn thiệu", "bảo đại")

def _normalize_space(text: str | None) -> str:
    if not text: return ""
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.split())

def _select_voice_setting(profile: AgentProfile, hero_name: str | None = None) -> VoiceSetting:
    # 1. Check hero_name specific overrides first
    if hero_name:
        lower_hero = hero_name.lower()
        if any(k in lower_hero for k in ELDER_KEYWORDS):
            return VoiceSetting(
                pronoun="Bác",
                audience="các cháu",
                tone_hint="giọng ấm áp, ân cần",
                greeting_template="Chào {audience}, {pronoun} là {persona}.",
            )
        if any(k in lower_hero for k in CONTROVERSIAL_KEYWORDS):
            return VoiceSetting(
                pronoun="tôi",
                audience="quý vị",
                tone_hint="giọng trang trọng, lịch sự nhưng có phần xa cách",
                greeting_template="Chào {audience}, {pronoun} là {persona}.",
            )

    blob_parts = [
        profile.persona_name or "",
        profile.period_label or "",
        profile.summary or "",
        " ".join(profile.notable_figures),
        " ".join(profile.key_events),
    ]
    blob = " ".join(part for part in blob_parts if part).lower()
    normalized_period = _normalize_space(profile.period_label)
    
    if any(keyword in blob for keyword in REVOLUTION_KEYWORDS):
        return VoiceSetting(pronoun="tôi", audience="các đồng chí", tone_hint="revolution", greeting_template="")
    
    if any(keyword in blob for keyword in MODERN_KEYWORDS):
        return VoiceSetting(pronoun="tôi", audience="các bạn", tone_hint="modern", greeting_template="")
        
    if any(keyword in blob for keyword in ANCESTRAL_KEYWORDS):
        return VoiceSetting(pronoun="ta", audience="con cháu", tone_hint="ancestral", greeting_template="")
        
    if any(token in blob for token in ROYAL_TOKENS):
        return VoiceSetting(pronoun="trẫm", audience="các khanh", tone_hint="royal", greeting_template="")
        
    if any(keyword in blob for keyword in COMMANDER_KEYWORDS):
        return VoiceSetting(pronoun="ta", audience="các tráng sĩ", tone_hint="commander", greeting_template="")
        
    if any(keyword in blob for keyword in SCHOLAR_KEYWORDS):
        return VoiceSetting(pronoun="ta", audience="các hữu", tone_hint="scholar", greeting_template="")
        
    return VOICE_DEFAULT

# --- Test Cases ---

def test_voice_settings():
    # Profile for Modern Era (contains Ho Chi Minh, so it triggers Revolution by default)
    modern_profile = AgentProfile(
        "id", "Võ Nguyên Giáp", "Thời hiện đại", None, "Đại tướng tổng tư lệnh", 
        ("Hồ Chí Minh", "Võ Nguyên Giáp", "Ngô Đình Diệm"), 
        ("Điện Biên Phủ", "Kháng chiến chống Pháp")
    )
    
    test_cases = [
        (modern_profile, "Hồ Chí Minh", "Bác", "các cháu", "Elder (Ho Chi Minh)"),
        (modern_profile, "Ngô Đình Diệm", "tôi", "quý vị", "Controversial (Ngo Dinh Diem)"),
        (modern_profile, "Võ Nguyên Giáp", "tôi", "các đồng chí", "Revolutionary (Vo Nguyen Giap)"),
        
        (AgentProfile("id", "Lý Thái Tổ", "Nhà Lý", None, "Vua", (), ("Dời đô",)), "Lý Thái Tổ", "trẫm", "các khanh", "Royal (Ly Thai To)"),
    ]

    failures = []
    for profile, hero_name, expected_pronoun, expected_audience, desc in test_cases:
        voice = _select_voice_setting(profile, hero_name)
        print(f"Testing {desc}...")
        print(f"  -> Got: {voice.pronoun}/{voice.audience}, Expected: {expected_pronoun}/{expected_audience}")
        
        if voice.pronoun.lower() != expected_pronoun.lower() or voice.audience.lower() != expected_audience.lower():
            failures.append(f"{desc}: Expected '{expected_pronoun}/{expected_audience}', got '{voice.pronoun}/{voice.audience}'")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"- {f}")
        import sys
        sys.exit(1)
    else:
        print("\nSUCCESS: All refined voice settings match expectations.")

if __name__ == "__main__":
    test_voice_settings()
