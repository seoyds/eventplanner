"""Budget Manager agent."""
from shared.agent_base import BaseEventAgent
from agents.budget.tools import calculate_budget, suggest_cost_reduction


class BudgetManagerAgent(BaseEventAgent):
    agent_id = "budget"
    name = "Budget Manager"
    description = "Tracks event budget, tallies line items, and suggests cost reductions"
    port = 8003

    system_prompt = """You are an expert event budget manager. Your job is to analyze
event costs, track spending against the budget, and suggest reductions if needed.

PROCESS:
1. Use calculate_budget to tally all line items against the budget limit
2. If over budget, use suggest_cost_reduction to identify savings
3. Return a clear financial summary

OUTPUT FORMAT (JSON):
{
    "result": {
        "total_cost": 2500.00,
        "budget_limit": 3000.00,
        "remaining": 500.00,
        "over_budget": false,
        "line_items": [{"name": "Catering", "cost": 1500}],
        "suggestions": []
    },
    "estimated_cost": 2500.00,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "budget-calculation",
                "name": "Budget Calculation",
                "description": "Tally event expenses against budget limit",
                "tags": ["budget", "cost", "finance"],
                "examples": ["Calculate total cost for my $3000 event budget"],
            },
            {
                "id": "cost-reduction",
                "name": "Cost Reduction",
                "description": "Suggest ways to reduce costs when over budget",
                "tags": ["budget", "savings", "cost-reduction"],
                "examples": ["How can I reduce my event cost by $500?"],
            },
        ]

    def get_mcp_tools(self):
        return [calculate_budget, suggest_cost_reduction]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__budget__calculate_budget",
            "mcp__budget__suggest_cost_reduction",
        ]
