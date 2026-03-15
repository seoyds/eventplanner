"""Menu & Catering Planner agent."""
from shared.agent_base import BaseEventAgent
from agents.menu.tools import estimate_food_cost


class MenuPlannerAgent(BaseEventAgent):
    agent_id = "menu"
    name = "Menu & Catering Planner"
    description = "Plans event menus and estimates catering costs based on meal type and service style"
    port = 8004

    system_prompt = """You are an expert event catering and menu planner. Your job is to
suggest appropriate menus and estimate food costs for events.

PROCESS:
1. Use estimate_food_cost to calculate costs for each meal type needed
2. Suggest specific menu items appropriate for the event type and guest demographics
3. Return a complete menu plan with cost breakdown

OUTPUT FORMAT (JSON):
{
    "result": {
        "menu": {
            "meal_type": "lunch",
            "service_style": "catered",
            "suggested_items": ["Caesar salad", "Grilled chicken", "Vegetarian pasta"],
            "dietary_notes": "Vegetarian options included"
        },
        "cost_per_person": 22.50,
        "total_food_cost": 900.00
    },
    "estimated_cost": 900.00,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "menu-planning",
                "name": "Menu Planning",
                "description": "Plan event menus appropriate for the occasion and guest count",
                "tags": ["menu", "food", "catering"],
                "examples": ["Plan a lunch menu for 40 people for a family reunion"],
            },
            {
                "id": "food-cost-estimation",
                "name": "Food Cost Estimation",
                "description": "Estimate food costs based on meal type and service style",
                "tags": ["menu", "cost", "catering"],
                "examples": ["How much will catered dinner cost for 50 guests?"],
            },
        ]

    def get_mcp_tools(self):
        return [estimate_food_cost]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__menu__estimate_food_cost",
        ]
