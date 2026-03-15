"""Custom MCP tools for the Supplies Estimator agent."""
from claude_agent_sdk import tool

BASE_PRICES = {
    "decoration": 3.0,
    "favor": 5.0,
    "rental": 15.0,
    "consumable": 2.0,
}


@tool("estimate_supply_cost", "Estimate cost for event supplies", {
    "supply_type": str,
    "quantity": int,
    "unit_override": float,
})
async def estimate_supply_cost(args):
    """Calculate supply cost using base prices per unit.

    supply_type: decoration ($3), favor ($5), rental ($15), consumable ($2)
    unit_override: if > 0, use this price instead of base price
    """
    supply_type = args["supply_type"].lower()
    quantity = args["quantity"]
    unit_override = args.get("unit_override", 0.0)

    if unit_override and unit_override > 0:
        unit_price = unit_override
        price_source = f"custom price ${unit_override:.2f}"
    else:
        unit_price = BASE_PRICES.get(supply_type, 3.0)
        price_source = f"base price for '{supply_type}'"

    total_cost = unit_price * quantity

    return {
        "content": [{
            "type": "text",
            "text": (
                f"Supply estimate: {quantity}x {supply_type} @ ${unit_price:.2f} each "
                f"({price_source}) = ${total_cost:.2f} total"
            ),
        }]
    }
