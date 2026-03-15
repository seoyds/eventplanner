"""Custom MCP tools for the Venue & Destination Planner agent."""
from claude_agent_sdk import tool


@tool("search_venues", "Search for event venues matching criteria", {
    "location": str,
    "guest_count": int,
    "event_type": str,
    "indoor_required": bool,
})
async def search_venues(args):
    """Structure a venue search query for Claude to use with web search."""
    indoor_note = "Must have indoor option." if args["indoor_required"] else ""
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Search for {args['event_type']} venues near {args['location']} "
                f"that can hold {args['guest_count']} people. {indoor_note} "
                f"Find at least 3 options with: name, address, capacity, "
                f"estimated rental cost, indoor/outdoor, accessibility notes."
            ),
        }]
    }


@tool("score_venue", "Score a venue on multiple criteria", {
    "venue_name": str,
    "capacity_match": float,
    "price_per_person": float,
    "accessibility_score": float,
    "review_rating": float,
})
async def score_venue(args):
    """Calculate a weighted score for venue comparison."""
    score = (
        args["capacity_match"] * 0.25
        + (1 - min(args["price_per_person"] / 100, 1)) * 0.25
        + args["accessibility_score"] * 0.25
        + (args["review_rating"] / 5) * 0.25
    )
    return {
        "content": [{
            "type": "text",
            "text": f"Venue '{args['venue_name']}' scored {score:.2f}/1.0",
        }]
    }
