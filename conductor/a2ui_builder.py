"""A2UI payload builder — converts agent results into A2UI component messages.

Generates A2UI JSONL messages (createSurface, updateComponents, updateDataModel)
from structured AgentResult data returned by specialist agents.
"""
import json
from typing import Any


def build_a2ui_surface(agent_id: str, agent_result: dict) -> list[dict]:
    """Build A2UI messages for an agent's result.

    Args:
        agent_id: The agent that produced this result.
        agent_result: The full agent result dict (with agent_id, status, result, etc.)

    Returns:
        List of A2UI JSONL message dicts.
    """
    surface_id = f"agent-{agent_id}"
    status = agent_result.get("status", "completed")
    result = agent_result.get("result", {})
    estimated_cost = agent_result.get("estimated_cost", 0)
    warnings = agent_result.get("warnings", [])

    # Build components based on agent type
    builder = _AGENT_BUILDERS.get(agent_id, _build_generic_result)
    components = builder(surface_id, result, estimated_cost, warnings)

    messages = [
        {"createSurface": {"surfaceId": surface_id}},
        {"updateComponents": {"surfaceId": surface_id, "components": components}},
    ]

    # Add data model if there's structured data
    if result:
        messages.append({
            "updateDataModel": {
                "surfaceId": surface_id,
                "contents": {agent_id: result},
            }
        })

    return messages


def _id(surface_id: str, suffix: str) -> str:
    return f"{surface_id}-{suffix}"


# ── Venue Agent ──────────────────────────────────────────────────────────────

def _build_venue_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    venues = result.get("venues", [])
    recommended = result.get("recommended_venue", "")

    # Title
    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Venue Recommendations"},
        "style": "h2",
    })

    if recommended:
        components.append({
            "id": _id(surface_id, "pick"),
            "component": "Text",
            "text": {"literalString": f"Top pick: {recommended}"},
            "style": "caption",
        })

    # Venue cards
    for i, venue in enumerate(venues):
        card_id = _id(surface_id, f"venue-{i}")
        is_top = venue.get("name", "") == recommended

        components.append({
            "id": card_id,
            "component": "Card",
            "title": {"literalString": venue.get("name", f"Venue {i + 1}")},
            "subtitle": {"literalString": venue.get("address", "")},
        })

        # Details inside card
        details = [
            ("Capacity", str(venue.get("capacity", "N/A"))),
            ("Type", venue.get("indoor_outdoor", "N/A")),
            ("Estimated Cost", f"${venue.get('estimated_rental_cost', 0):,.0f}"),
        ]
        if venue.get("score"):
            details.append(("Score", f"{venue['score']:.0%}"))

        for j, (label, value) in enumerate(details):
            components.append({
                "id": _id(card_id, f"kv-{j}"),
                "component": "KeyValue",
                "parent": card_id,
                "label": {"literalString": label},
                "value": {"literalString": value},
            })

        if venue.get("accessibility_notes"):
            components.append({
                "id": _id(card_id, "access"),
                "component": "Badge",
                "parent": card_id,
                "text": {"literalString": venue["accessibility_notes"]},
                "color": "green",
            })

        if is_top:
            components.append({
                "id": _id(card_id, "badge"),
                "component": "Badge",
                "parent": card_id,
                "text": {"literalString": "Recommended"},
                "color": "blue",
            })

        if venue.get("notes"):
            components.append({
                "id": _id(card_id, "notes"),
                "component": "Text",
                "parent": card_id,
                "text": {"literalString": venue["notes"]},
                "style": "body",
            })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Menu / Catering Agent ────────────────────────────────────────────────────

def _build_menu_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Menu & Catering Plan"},
        "style": "h2",
    })

    # Menu sections (appetizers, mains, desserts, etc.)
    menu = result.get("menu", result.get("menu_items", {}))
    if isinstance(menu, dict):
        for section_name, items in menu.items():
            sec_id = _id(surface_id, f"sec-{section_name}")
            components.append({
                "id": sec_id,
                "component": "Card",
                "title": {"literalString": section_name.replace("_", " ").title()},
            })
            if isinstance(items, list):
                for k, item in enumerate(items):
                    item_text = item if isinstance(item, str) else item.get("name", str(item))
                    components.append({
                        "id": _id(sec_id, f"item-{k}"),
                        "component": "Text",
                        "parent": sec_id,
                        "text": {"literalString": f"• {item_text}"},
                        "style": "body",
                    })

    # Dietary accommodations
    dietary = result.get("dietary_accommodations", result.get("dietary_notes", []))
    if dietary:
        components.append({
            "id": _id(surface_id, "dietary-title"),
            "component": "Text",
            "text": {"literalString": "Dietary Accommodations"},
            "style": "h3",
        })
        items = dietary if isinstance(dietary, list) else [dietary]
        row_id = _id(surface_id, "dietary-row")
        components.append({
            "id": row_id,
            "component": "Row",
            "wrap": True,
        })
        for k, d in enumerate(items):
            components.append({
                "id": _id(row_id, f"badge-{k}"),
                "component": "Badge",
                "parent": row_id,
                "text": {"literalString": str(d)},
                "color": "green",
            })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Budget Agent ─────────────────────────────────────────────────────────────

def _build_budget_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Budget Breakdown"},
        "style": "h2",
    })

    # Build table from breakdown items
    breakdown = result.get("breakdown", result.get("cost_breakdown", {}))
    if isinstance(breakdown, dict) and breakdown:
        rows = []
        for category, amount in breakdown.items():
            rows.append({
                "category": category.replace("_", " ").title(),
                "amount": f"${float(amount):,.0f}" if isinstance(amount, (int, float)) else str(amount),
            })
        components.append({
            "id": _id(surface_id, "table"),
            "component": "DataTable",
            "columns": [
                {"key": "category", "label": "Category"},
                {"key": "amount", "label": "Amount", "align": "right"},
            ],
            "rows": rows,
        })

    # Total and budget progress
    total = result.get("total_estimated_cost", result.get("total", cost))
    budget_limit = result.get("budget_limit", result.get("total_budget", 0))

    if total:
        components.append({
            "id": _id(surface_id, "total"),
            "component": "KeyValue",
            "label": {"literalString": "Total Estimated Cost"},
            "value": {"literalString": f"${float(total):,.0f}"},
        })

    if budget_limit and total:
        components.append({
            "id": _id(surface_id, "progress"),
            "component": "ProgressBar",
            "value": total,
            "max": budget_limit,
            "label": {"literalString": "Budget Usage"},
        })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Weather Agent ────────────────────────────────────────────────────────────

def _build_weather_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Weather Forecast"},
        "style": "h2",
    })

    forecast = result.get("forecast", result.get("weather", {}))
    if isinstance(forecast, dict):
        card_id = _id(surface_id, "forecast-card")
        components.append({
            "id": card_id,
            "component": "Card",
        })
        for k, (key, val) in enumerate(forecast.items()):
            components.append({
                "id": _id(card_id, f"kv-{k}"),
                "component": "KeyValue",
                "parent": card_id,
                "label": {"literalString": key.replace("_", " ").title()},
                "value": {"literalString": str(val)},
            })

    recommendations = result.get("recommendations", result.get("suggestions", []))
    if recommendations:
        components.append({
            "id": _id(surface_id, "recs-title"),
            "component": "Text",
            "text": {"literalString": "Recommendations"},
            "style": "h3",
        })
        for k, rec in enumerate(recommendations if isinstance(recommendations, list) else [recommendations]):
            components.append({
                "id": _id(surface_id, f"rec-{k}"),
                "component": "Text",
                "text": {"literalString": f"• {rec}"},
                "style": "body",
            })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Generic Fallback ─────────────────────────────────────────────────────────

def _build_generic_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    """Render any agent result as a set of key-value pairs inside a card."""
    components: list[dict] = []

    # Title from agent_id
    agent_label = surface_id.replace("agent-", "").replace("_", " ").title()
    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": f"{agent_label} Results"},
        "style": "h2",
    })

    card_id = _id(surface_id, "card")
    components.append({
        "id": card_id,
        "component": "Card",
    })

    # Flatten the result into key-value pairs
    kv_index = 0
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            # Nested structures — render as sub-cards or lists
            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                components.append({
                    "id": _id(card_id, f"label-{kv_index}"),
                    "component": "Text",
                    "parent": card_id,
                    "text": {"literalString": key.replace("_", " ").title()},
                    "style": "label",
                })
                for li, item in enumerate(value):
                    components.append({
                        "id": _id(card_id, f"item-{kv_index}-{li}"),
                        "component": "Text",
                        "parent": card_id,
                        "text": {"literalString": f"• {item}"},
                        "style": "body",
                    })
            elif isinstance(value, dict):
                sub_card_id = _id(card_id, f"sub-{kv_index}")
                components.append({
                    "id": sub_card_id,
                    "component": "Card",
                    "parent": card_id,
                    "title": {"literalString": key.replace("_", " ").title()},
                })
                for sk, (sub_key, sub_val) in enumerate(value.items()):
                    if isinstance(sub_val, (str, int, float, bool)):
                        components.append({
                            "id": _id(sub_card_id, f"kv-{sk}"),
                            "component": "KeyValue",
                            "parent": sub_card_id,
                            "label": {"literalString": sub_key.replace("_", " ").title()},
                            "value": {"literalString": str(sub_val)},
                        })
            else:
                # Mixed list — render as text items
                components.append({
                    "id": _id(card_id, f"label-{kv_index}"),
                    "component": "Text",
                    "parent": card_id,
                    "text": {"literalString": key.replace("_", " ").title()},
                    "style": "label",
                })
                for li, item in enumerate(value):
                    components.append({
                        "id": _id(card_id, f"item-{kv_index}-{li}"),
                        "component": "Text",
                        "parent": card_id,
                        "text": {"literalString": f"• {json.dumps(item, default=str) if isinstance(item, dict) else str(item)}"},
                        "style": "body",
                    })
        else:
            components.append({
                "id": _id(card_id, f"kv-{kv_index}"),
                "component": "KeyValue",
                "parent": card_id,
                "label": {"literalString": key.replace("_", " ").title()},
                "value": {"literalString": str(value)},
            })
        kv_index += 1

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Shared Helpers ───────────────────────────────────────────────────────────

def _append_cost_and_warnings(
    components: list[dict], surface_id: str, cost: float, warnings: list[str]
) -> None:
    if cost > 0:
        components.append({
            "id": _id(surface_id, "cost"),
            "component": "KeyValue",
            "label": {"literalString": "Estimated Cost"},
            "value": {"literalString": f"${cost:,.0f}"},
        })
    if warnings:
        for i, w in enumerate(warnings):
            components.append({
                "id": _id(surface_id, f"warn-{i}"),
                "component": "Badge",
                "text": {"literalString": w},
                "color": "yellow",
            })


# ── Builder Registry ─────────────────────────────────────────────────────────

_AGENT_BUILDERS = {
    "venue": _build_venue_result,
    "menu": _build_menu_result,
    "budget": _build_budget_result,
    "weather": _build_weather_result,
}


def build_blueprint_surface(blueprint: dict, agent_results: dict) -> list[dict]:
    """Build an A2UI surface for the final compiled event blueprint.

    Called after all agents complete to render the summary view.
    """
    surface_id = "blueprint"
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Event Blueprint"},
        "style": "h1",
    })

    # Summary card
    summary_card = _id(surface_id, "summary")
    components.append({
        "id": summary_card,
        "component": "Card",
        "title": {"literalString": "Event Summary"},
    })

    summary_fields = ["event_type", "event_name", "date", "location", "guest_count", "total_budget"]
    kv_idx = 0
    for field in summary_fields:
        val = blueprint.get(field)
        if val is not None:
            components.append({
                "id": _id(summary_card, f"kv-{kv_idx}"),
                "component": "KeyValue",
                "parent": summary_card,
                "label": {"literalString": field.replace("_", " ").title()},
                "value": {"literalString": str(val)},
            })
            kv_idx += 1

    # Add divider before agent sections
    components.append({
        "id": _id(surface_id, "divider"),
        "component": "Divider",
    })

    # Individual agent result surfaces
    for agent_id, result_data in agent_results.items():
        if isinstance(result_data, dict):
            agent_components = build_a2ui_surface(agent_id, result_data)
            for msg in agent_components:
                if "updateComponents" in msg:
                    components.extend(msg["updateComponents"]["components"])

    messages = [
        {"createSurface": {"surfaceId": surface_id}},
        {"updateComponents": {"surfaceId": surface_id, "components": components}},
    ]

    if blueprint:
        messages.append({
            "updateDataModel": {
                "surfaceId": surface_id,
                "contents": {"blueprint": blueprint},
            }
        })

    return messages
