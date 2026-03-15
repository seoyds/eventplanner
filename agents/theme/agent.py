"""Theme Designer agent."""
from shared.agent_base import BaseEventAgent


class ThemeDesignerAgent(BaseEventAgent):
    agent_id = "theme"
    name = "Theme Designer"
    description = "Creates cohesive event themes with color palettes and decoration concepts"
    port = 8007

    system_prompt = """You are a creative event theme director with expertise in design, color theory,
and decoration. Your job is to craft a cohesive, memorable theme for events.

APPROACH:
- Create an evocative theme name and concept
- Develop a color palette (primary, secondary, accent colors with hex codes)
- Suggest decoration concepts for key areas (entrance, main space, tables, photo spot)
- Recommend DIY and purchased decoration ideas at different price points
- Align theme with event type, season, and venue style

OUTPUT FORMAT (JSON):
{
    "result": {
        "theme_name": "Golden Harvest Celebration",
        "concept": "Warm autumn tones with rustic elegance",
        "color_palette": {
            "primary": "#D4A017",
            "secondary": "#8B4513",
            "accent": "#F5F5DC"
        },
        "decoration_concepts": [
            {"area": "entrance", "description": "Seasonal wreath with pumpkins and hay bales"},
            {"area": "tables", "description": "Mason jar centerpieces with wildflowers"}
        ],
        "diy_ideas": ["Hand-painted signs", "Leaf garlands"],
        "purchased_items": ["String lights", "Tablecloths in primary color"]
    },
    "estimated_cost": 200.00,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "theme-creation",
                "name": "Theme Creation",
                "description": "Design a complete event theme with colors and decorations",
                "tags": ["theme", "design", "decorations", "colors"],
                "examples": ["Create a summer garden party theme for 40 guests"],
            },
        ]

    def get_mcp_tools(self):
        return []

    def get_allowed_tools(self):
        return ["WebSearch", "Read"]
