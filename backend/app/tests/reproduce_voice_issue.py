import json
import os
import sys
from dataclasses import dataclass
import unicodedata

# Mock classes to match app structure
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

# --- COPY OF CURRENT LOGIC FROM chat.py ---
ANCESTRAL_KEYWORDS = (
    "hồng bàng", "hùng vương", "lạc long quân", "âu lạc",
)
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

def _normalize_space(text: str | None) -> str:
    if not text: return ""
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.split())

def _select_voice_setting(profile: AgentProfile) -> VoiceSetting:
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

# --- LOAD REAL DATA ---
def load_profiles():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_path, "data", "timeline_seed.json")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    profiles = []
    for item in data:
        # Create a profile for the main agent
        p = AgentProfile(
            agent_id=item["agent_id"],
            persona_name=item["notable_figures"][0] if item["notable_figures"] else item["name"],
            period_label=item["name"],
            year_range=item["year_range"],
            summary=item["summary"],
            notable_figures=tuple(item.get("notable_figures", [])),
            key_events=tuple(item.get("key_events", [])),
        )
        profiles.append(p)
        
        # Also create profiles for specific notable figures if we want to test them individually
        # (In the app, the agent_id is the same, but the persona_name changes in the session)
        # But _select_voice_setting uses the *profile* which comes from the agent_id.
        # Wait! The profile is static per agent_id.
        # If the user selects "Ngô Đình Diệm", the agent_id is "agent_hien_dai_chia_cat" (or similar).
        # The profile loaded is for that agent.
        # The `hero_name` passed to `_compose_system_prompt` overrides the name,
        # BUT `_select_voice_setting` uses the `profile` object!
        #
        # CRITICAL FINDING: `_select_voice_setting` uses the static `profile`!
        # It does NOT know about the `hero_name` from the session!
        # So if "Ngô Đình Diệm" is just a name in `notable_figures`, but the profile itself
        # triggers "Revolutionary" (because of Ho Chi Minh in the same list), 
        # then Ngô Đình Diệm will get "Revolutionary" voice!
        #
        # Let's verify this hypothesis.
        pass
        
    return profiles

def test_specific_heroes():
    # We need to simulate what happens when we have a specific hero name
    # But currently _select_voice_setting ONLY takes profile.
    # This confirms the bug: Voice setting is tied to the AGENT, not the HERO.
    
    print("Loading profiles...")
    profiles = load_profiles()
    
    # Find the agent for Modern Era
    modern_agent = next((p for p in profiles if "Hiện đại" in p.period_label), None)
    if modern_agent:
        print(f"\nAnalyzing Agent: {modern_agent.agent_id} ({modern_agent.period_label})")
        print(f"Notable Figures: {modern_agent.notable_figures}")
        voice = _select_voice_setting(modern_agent)
        print(f"-> Voice: {voice.pronoun} / {voice.audience} ({voice.tone_hint})")
        
        # Check if this voice fits Ngô Đình Diệm
        print(f"Does this fit Ngô Đình Diệm? {'No' if voice.audience == 'các đồng chí' else 'Maybe'}")

if __name__ == "__main__":
    test_specific_heroes()
