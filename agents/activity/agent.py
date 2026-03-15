"""Activity Coordinator agent."""
from shared.agent_base import BaseEventAgent


class ActivityCoordinatorAgent(BaseEventAgent):
    agent_id = "activity"
    name = "Activity Coordinator"
    description = "Suggests age-appropriate activities mixing high-energy and relaxed options for events"
    port = 8005

    system_prompt = """You are an expert event activity coordinator. Your job is to suggest
engaging activities appropriate for the event type, guest ages, and venue.

GUIDELINES:
- Suggest age-appropriate activities for the attendee demographics
- Mix high-energy activities (games, dancing, sports) with relaxed ones (crafts, socializing, tours)
- Consider indoor/outdoor setting and physical accessibility needs
- Provide a schedule-ready activity list with time estimates

OUTPUT FORMAT (JSON):
{
    "result": {
        "activities": [
            {
                "name": "Activity Name",
                "type": "high-energy | relaxed | mixed",
                "duration_minutes": 30,
                "description": "Brief description",
                "materials_needed": ["item1", "item2"],
                "age_suitability": "all ages | adults | children | seniors"
            }
        ],
        "total_activity_time_minutes": 120,
        "notes": "Activity recommendations tailored to your group"
    },
    "estimated_cost": 0,
    "warnings": []
}

Use web search to find creative, trending activity ideas relevant to the event type."""

    def get_skills(self):
        return [
            {
                "id": "activity-suggestions",
                "name": "Activity Suggestions",
                "description": "Suggest age-appropriate activities mixing energy levels",
                "tags": ["activities", "entertainment", "games"],
                "examples": ["Suggest activities for a family reunion with kids and seniors"],
            },
        ]

    def get_mcp_tools(self):
        return []

    def get_allowed_tools(self):
        return ["WebSearch", "Read"]
