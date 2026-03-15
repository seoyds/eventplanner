"""Custom MCP tools for the Menu & Catering Planner agent."""
from claude_agent_sdk import tool

BASE_RATES = {
    "breakfast": 8.0,
    "lunch": 15.0,
    "dinner": 25.0,
    "snacks": 5.0,
}

STYLE_MULTIPLIERS = {
    "catered": 1.5,
    "potluck": 0.4,
    "self": 1.0,
}


@tool("estimate_food_cost", "Estimate food cost based on meal type, guest count, and service style", {
    "meal_type": str,
    "guest_count": int,
    "service_style": str,
})
async def estimate_food_cost(args):
    """Calculate estimated food cost using base rates and service style multipliers.

    meal_type: breakfast, lunch, dinner, snacks
    service_style: catered (1.5x), potluck (0.4x), self (1.0x)
    """
    meal_type = args["meal_type"].lower()
    service_style = args["service_style"].lower()
    guest_count = args["guest_count"]

    base_rate = BASE_RATES.get(meal_type, 15.0)
    multiplier = STYLE_MULTIPLIERS.get(service_style, 1.0)

    cost_per_person = base_rate * multiplier
    total_cost = cost_per_person * guest_count

    return {
        "content": [{
            "type": "text",
            "text": (
                f"Food cost estimate for {guest_count} guests: "
                f"{meal_type} ({service_style}) = "
                f"${cost_per_person:.2f}/person x {guest_count} = ${total_cost:.2f} total"
            ),
        }]
    }
