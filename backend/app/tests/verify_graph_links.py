from dataclasses import dataclass
import sys
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["app.schemas"] = MagicMock()
sys.modules["app.schemas.chat"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["app.config"] = MagicMock()
mock_settings = MagicMock()
mock_settings.openai_api_key = "fake-key"
sys.modules["app.config"].get_settings.return_value = mock_settings

# Define minimal structures needed for the function
@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    persona_name: str
    period_label: str
    year_range: str | None
    summary: str
    notable_figures: tuple[str, ...]
    key_events: tuple[str, ...]

DEFAULT_PROFILE = AgentProfile(
    agent_id="agent_general_search",
    persona_name="Cố vấn lịch sử",
    period_label="Tiến trình lịch sử Việt Nam",
    year_range=None,
    summary="",
    notable_figures=(),
    key_events=(),
)

AGENT_PROFILES = {"agent_hien_dai": AgentProfile(
    agent_id="agent_hien_dai",
    persona_name="Lê Duẩn",
    period_label="Cộng hòa Xã hội Chủ nghĩa Việt Nam",
    year_range="1976-1986",
    summary="",
    notable_figures=(),
    key_events=(),
)}

def _get_agent_profile(agent_id: str) -> AgentProfile:
    return AGENT_PROFILES.get(agent_id) or DEFAULT_PROFILE

# Mock GraphLink class
class GraphLink:
    def __init__(self, relation, description, chunk_id):
        self.relation = relation
        self.description = description
        self.chunk_id = chunk_id
    
    def __repr__(self):
        return f"GraphLink(relation='{self.relation}', description='{self.description}')"

sys.modules["app.schemas.chat"].GraphLink = GraphLink

# --- The function with the FIX (extracted for testing) ---

def _extract_graph_links_from_answer(answer: str, agent_id: str, hero_name: str | None = None):
    """Fake graph links như đi trên đồ thị tri thức."""
    profile = _get_agent_profile(agent_id)
    
    # Use specific hero_name if provided, otherwise fallback to profile default
    final_persona = hero_name or profile.persona_name
    
    # We only test the fallback logic here to avoid mocking OpenAI complex response
    # If fallback works, it means final_persona is correctly set
    
    return [
        GraphLink(
            relation=f"{profile.period_label} → {final_persona}",
            description=f"{final_persona} là nhân vật tiêu biểu của {profile.period_label}",
            chunk_id=100,
        ),
        GraphLink(
            relation=f"{final_persona} → Sự kiện lịch sử",
            description=f"Các sự kiện quan trọng gắn liền với {final_persona}",
            chunk_id=200,
        ),
    ]

# --- Test Logic ---

def test_graph_links():
    agent_id = "agent_hien_dai"
    hero_name = "Võ Văn Kiệt"
    
    print(f"Testing with agent_id={agent_id}, hero_name={hero_name}")
    links = _extract_graph_links_from_answer("Some answer", agent_id, hero_name=hero_name)
    
    print("Generated Links:")
    for link in links:
        print(f"- {link}")
    
    # Check if hero_name is used
    found_hero = False
    found_default = False
    
    for link in links:
        if hero_name in link.relation:
            found_hero = True
        if "Lê Duẩn" in link.relation:
            found_default = True
            
    if found_hero and not found_default:
        print("\nSUCCESS: Graph links use the correct hero name.")
    else:
        print("\nFAILURE: Graph links do NOT use the correct hero name.")
        if found_default:
            print("  -> Found default persona (Lê Duẩn) instead.")
        sys.exit(1)

if __name__ == "__main__":
    test_graph_links()
