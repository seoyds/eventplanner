"""Communication Writer agent."""
from shared.agent_base import BaseEventAgent


class CommunicationWriterAgent(BaseEventAgent):
    agent_id = "communication"
    name = "Communication Writer"
    description = "Drafts save-the-date notices, invitations, and event communication templates"
    port = 8009

    system_prompt = """You are an expert event copywriter specializing in invitations and
guest communications. Your job is to craft warm, clear, and compelling event communications.

DELIVERABLES:
- Save-the-date notice (brief, friendly, key details only)
- Formal invitation (complete details, RSVP instructions)
- Reminder message (brief, sent 1 week before)
- Day-of instructions (venue directions, parking, what to bring)

WRITING STYLE:
- Warm and welcoming tone matching the event type
- Clear formatting with all essential details (who, what, when, where, RSVP)
- Appropriate formality level (casual for family reunion, formal for gala)

OUTPUT FORMAT (JSON):
{
    "result": {
        "save_the_date": "Save the Date! Join us for...",
        "invitation": "You are cordially invited to...",
        "reminder": "Just a reminder — our event is one week away!",
        "day_of_instructions": "We look forward to seeing you! Here's everything you need..."
    },
    "estimated_cost": 0,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "invitation-drafting",
                "name": "Invitation Drafting",
                "description": "Draft save-the-date and invitation templates for events",
                "tags": ["communication", "invitation", "copywriting"],
                "examples": ["Write an invitation for a 50th birthday party"],
            },
            {
                "id": "event-communications",
                "name": "Event Communications",
                "description": "Create reminders and day-of instructions for guests",
                "tags": ["communication", "reminder", "instructions"],
                "examples": ["Write a reminder email for our family reunion"],
            },
        ]

    def get_mcp_tools(self):
        return []

    def get_allowed_tools(self):
        return ["WebSearch", "Read"]
