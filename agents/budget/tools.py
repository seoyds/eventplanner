"""Custom MCP tools for the Budget Manager agent."""
from claude_agent_sdk import tool


@tool("calculate_budget", "Tally line items against a budget limit", {
    "line_items": str,
    "budget_limit": float,
})
async def calculate_budget(args):
    """Calculate total spend from line items JSON and compare to budget limit.

    line_items should be a JSON string like: '[{"name": "Catering", "cost": 500}, ...]'
    """
    import json
    try:
        items = json.loads(args["line_items"])
    except (json.JSONDecodeError, TypeError):
        return {
            "content": [{
                "type": "text",
                "text": "Error: line_items must be a valid JSON array of {name, cost} objects.",
            }]
        }

    total = sum(item.get("cost", 0) for item in items)
    budget_limit = args["budget_limit"]
    remaining = budget_limit - total
    over_budget = total > budget_limit

    summary_lines = [f"  {item.get('name', 'Unknown')}: ${item.get('cost', 0):.2f}" for item in items]
    summary = "\n".join(summary_lines)

    status = "OVER BUDGET" if over_budget else "within budget"
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Budget Summary:\n{summary}\n"
                f"Total: ${total:.2f} / ${budget_limit:.2f} ({status}). "
                f"Remaining: ${remaining:.2f}"
            ),
        }]
    }


@tool("suggest_cost_reduction", "Suggest cost reduction strategies", {
    "total_cost": float,
    "budget_limit": float,
    "line_items": str,
})
async def suggest_cost_reduction(args):
    """Generate cost reduction suggestions when over budget."""
    import json
    total_cost = args["total_cost"]
    budget_limit = args["budget_limit"]
    reduction_needed = total_cost - budget_limit

    if reduction_needed <= 0:
        return {
            "content": [{
                "type": "text",
                "text": f"No cost reduction needed. Currently ${abs(reduction_needed):.2f} under budget.",
            }]
        }

    try:
        items = json.loads(args["line_items"])
        sorted_items = sorted(items, key=lambda x: x.get("cost", 0), reverse=True)
        top_items = sorted_items[:3]
        suggestions = [
            f"  - Reduce '{item.get('name', 'Unknown')}' (${item.get('cost', 0):.2f}) by 10-20%"
            for item in top_items
        ]
    except (json.JSONDecodeError, TypeError):
        suggestions = ["  - Review largest expense categories for savings"]

    suggestion_text = "\n".join(suggestions)
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Cost reduction needed: ${reduction_needed:.2f}\n"
                f"Top suggestions:\n{suggestion_text}"
            ),
        }]
    }
