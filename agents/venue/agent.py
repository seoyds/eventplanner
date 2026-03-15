"""Venue & Destination Planner agent."""
from shared.agent_base import BaseEventAgent
from agents.venue.tools import search_venues, score_venue


class VenuePlannerAgent(BaseEventAgent):
    agent_id = "venue"
    name = "Venue & Destination Planner"
    description = "Finds and scores event venues matching location, capacity, and accessibility requirements"
    port = 8001

    system_prompt = """You are an expert event venue researcher. Your job is to find
the best venues for an event based on the requirements provided.

PROCESS:
1. Use web search to find real venues matching the location and capacity requirements
2. Score each venue using the score_venue tool
3. Return your top 3 recommendations with full details

OUTPUT FORMAT (JSON):
{
    "result": {
        "venues": [
            {
                "name": "Venue Name",
                "address": "Full address",
                "capacity": 50,
                "estimated_rental_cost": 1500.00,
                "indoor_outdoor": "both",
                "accessibility_notes": "Wheelchair accessible",
                "contact_info": "phone/email/website",
                "score": 0.85,
                "notes": "Why this venue is a good fit"
            }
        ],
        "recommended_venue": "Name of top pick"
    },
    "estimated_cost": 1500.00,
    "warnings": []
}

Be thorough in your research. Use web search to find REAL venues."""

    def get_skills(self):
        return [
            {
                "id": "venue-search",
                "name": "Venue Search",
                "description": "Search for event venues matching location and capacity criteria",
                "tags": ["venue", "search", "location"],
                "examples": ["Find venues in Denver for 40 people"],
            },
            {
                "id": "venue-scoring",
                "name": "Venue Scoring",
                "description": "Score and compare venues on capacity, price, accessibility, and reviews",
                "tags": ["venue", "scoring", "comparison"],
                "examples": ["Score this venue against our criteria"],
            },
        ]

    def get_mcp_tools(self):
        return [search_venues, score_venue]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__venue__search_venues",
            "mcp__venue__score_venue",
        ]
