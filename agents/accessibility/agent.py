"""Accessibility Checker agent."""
from shared.agent_base import BaseEventAgent
from agents.accessibility.tools import check_accessibility


class AccessibilityCheckerAgent(BaseEventAgent):
    agent_id = "accessibility"
    name = "Accessibility Checker"
    description = "Evaluates venue accessibility for wheelchair users, elderly, and children"
    port = 8006

    system_prompt = """You are an expert accessibility consultant for events. Your job is to
assess venue accessibility and provide recommendations to ensure all guests can participate fully.

PROCESS:
1. Use check_accessibility to score the venue on key accessibility criteria
2. Identify any gaps and suggest accommodations
3. Return a clear accessibility report

OUTPUT FORMAT (JSON):
{
    "result": {
        "accessibility_score": 0.8,
        "rating": "Good",
        "features": {
            "wheelchair_access": true,
            "elevator": true,
            "stairs_only": false,
            "elderly_suitable": true,
            "children_suitable": true
        },
        "recommendations": ["Provide reserved seating near entrance for mobility-impaired guests"],
        "required_accommodations": []
    },
    "estimated_cost": 0,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "accessibility-check",
                "name": "Accessibility Check",
                "description": "Score and report on venue accessibility features",
                "tags": ["accessibility", "wheelchair", "ADA", "inclusion"],
                "examples": ["Check if this venue is accessible for elderly guests"],
            },
        ]

    def get_mcp_tools(self):
        return [check_accessibility]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__accessibility__check_accessibility",
        ]
