"""Supplies Estimator agent."""
from shared.agent_base import BaseEventAgent
from agents.supplies.tools import estimate_supply_cost


class SuppliesEstimatorAgent(BaseEventAgent):
    agent_id = "supplies"
    name = "Supplies Estimator"
    description = "Estimates costs for event supplies including decorations, favors, rentals, and consumables"
    port = 8010

    system_prompt = """You are an expert event supplies planner. Your job is to compile
a comprehensive supplies list and estimate total costs for the event.

PROCESS:
1. Identify all supply categories needed: decorations, favors, rentals, consumables
2. Use estimate_supply_cost for each category to calculate costs
3. Return a complete supplies manifest with cost breakdown

OUTPUT FORMAT (JSON):
{
    "result": {
        "supplies": [
            {"category": "decoration", "item": "Table centerpieces", "quantity": 10, "unit_cost": 3.00, "total": 30.00},
            {"category": "favor", "item": "Thank you bags", "quantity": 40, "unit_cost": 5.00, "total": 200.00},
            {"category": "rental", "item": "Folding chairs", "quantity": 40, "unit_cost": 15.00, "total": 600.00},
            {"category": "consumable", "item": "Paper plates", "quantity": 80, "unit_cost": 2.00, "total": 160.00}
        ],
        "total_supplies_cost": 990.00,
        "shopping_list": ["Table centerpieces x10", "Thank you bags x40"]
    },
    "estimated_cost": 990.00,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "supplies-estimation",
                "name": "Supplies Estimation",
                "description": "Estimate costs for all event supply categories",
                "tags": ["supplies", "decorations", "favors", "rentals", "cost"],
                "examples": ["Estimate supplies needed for a 40-person birthday party"],
            },
        ]

    def get_mcp_tools(self):
        return [estimate_supply_cost]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__supplies__estimate_supply_cost",
        ]
