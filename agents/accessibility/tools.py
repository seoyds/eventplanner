"""Custom MCP tools for the Accessibility Checker agent."""
from claude_agent_sdk import tool


@tool("check_accessibility", "Score venue accessibility for various needs", {
    "wheelchair_access": bool,
    "has_elevator": bool,
    "has_stairs_only": bool,
    "suitable_for_elderly": bool,
    "suitable_for_children": bool,
})
async def check_accessibility(args):
    """Calculate an accessibility score based on venue features."""
    score = 0.0
    max_score = 5.0
    details = []

    if args["wheelchair_access"]:
        score += 1.0
        details.append("wheelchair accessible")
    else:
        details.append("NOT wheelchair accessible")

    if args["has_elevator"]:
        score += 1.0
        details.append("elevator available")
    else:
        details.append("no elevator")

    if not args["has_stairs_only"]:
        score += 1.0
        details.append("no stairs-only access")
    else:
        details.append("stairs-only sections present")

    if args["suitable_for_elderly"]:
        score += 1.0
        details.append("suitable for elderly")
    else:
        details.append("may not suit elderly guests")

    if args["suitable_for_children"]:
        score += 1.0
        details.append("suitable for children")
    else:
        details.append("not ideal for children")

    normalized_score = score / max_score
    detail_text = ", ".join(details)

    if normalized_score >= 0.8:
        rating = "Excellent"
    elif normalized_score >= 0.6:
        rating = "Good"
    elif normalized_score >= 0.4:
        rating = "Fair"
    else:
        rating = "Poor"

    return {
        "content": [{
            "type": "text",
            "text": (
                f"Accessibility score: {normalized_score:.2f}/1.0 ({rating}). "
                f"Details: {detail_text}"
            ),
        }]
    }
