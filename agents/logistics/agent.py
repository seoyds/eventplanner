"""Logistics Coordinator agent."""
from shared.agent_base import BaseEventAgent
from agents.logistics.tools import create_timeline_slot


class LogisticsCoordinatorAgent(BaseEventAgent):
    agent_id = "logistics"
    name = "Logistics Coordinator"
    description = "Creates detailed event timelines and coordinates logistics for smooth execution"
    port = 8008

    system_prompt = """You are an expert event logistics coordinator. Your job is to create
a detailed, realistic timeline for the event from setup through teardown.

PROCESS:
1. Use create_timeline_slot to build each time block in the schedule
2. Include setup, guest arrival, main program segments, breaks, meals, and teardown
3. Return a complete chronological timeline

OUTPUT FORMAT (JSON):
{
    "result": {
        "timeline": [
            {"time": "10:00", "end_time": "11:00", "activity": "Venue setup", "responsible": "Organizer"},
            {"time": "11:00", "end_time": "12:00", "activity": "Guest arrival & check-in"}
        ],
        "total_duration_hours": 6,
        "setup_time_required": "1 hour before guests arrive",
        "teardown_time_required": "1 hour after event ends"
    },
    "estimated_cost": 0,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "timeline-creation",
                "name": "Timeline Creation",
                "description": "Build a detailed event timeline with start and end times",
                "tags": ["logistics", "timeline", "schedule", "coordination"],
                "examples": ["Create a timeline for a 4-hour afternoon birthday party"],
            },
        ]

    def get_mcp_tools(self):
        return [create_timeline_slot]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__logistics__create_timeline_slot",
        ]
