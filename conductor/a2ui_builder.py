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


# ── Theme Designer Agent ────────────────────────────────────────────────────

def _build_theme_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Theme Design"},
        "style": "h2",
    })

    # Theme name and concept
    theme_name = result.get("theme_name", "")
    concept = result.get("concept", "")
    if theme_name:
        components.append({
            "id": _id(surface_id, "name"),
            "component": "Text",
            "text": {"literalString": theme_name},
            "style": "h3",
        })
    if concept:
        components.append({
            "id": _id(surface_id, "concept"),
            "component": "Text",
            "text": {"literalString": concept},
            "style": "caption",
        })

    # Color palette as colored Badges
    palette = result.get("color_palette", {})
    if palette:
        row_id = _id(surface_id, "palette-row")
        components.append({
            "id": _id(surface_id, "palette-label"),
            "component": "Text",
            "text": {"literalString": "Color Palette"},
            "style": "label",
        })
        components.append({
            "id": row_id,
            "component": "Row",
            "wrap": True,
        })
        color_map = {"primary": "blue", "secondary": "purple", "accent": "green"}
        for k, (role, hex_val) in enumerate(palette.items()):
            components.append({
                "id": _id(row_id, f"color-{k}"),
                "component": "Badge",
                "parent": row_id,
                "text": {"literalString": f"{role.title()}: {hex_val}"},
                "color": color_map.get(role, "blue"),
            })

    # Decoration concepts as Cards
    concepts = result.get("decoration_concepts", [])
    if concepts:
        components.append({
            "id": _id(surface_id, "decor-title"),
            "component": "Text",
            "text": {"literalString": "Decoration Concepts"},
            "style": "h3",
        })
        for i, dec in enumerate(concepts):
            card_id = _id(surface_id, f"decor-{i}")
            area = dec.get("area", f"Area {i + 1}") if isinstance(dec, dict) else f"Area {i + 1}"
            desc = dec.get("description", str(dec)) if isinstance(dec, dict) else str(dec)
            components.append({
                "id": card_id,
                "component": "Card",
                "title": {"literalString": area.replace("_", " ").title()},
            })
            components.append({
                "id": _id(card_id, "desc"),
                "component": "Text",
                "parent": card_id,
                "text": {"literalString": desc},
                "style": "body",
            })

    # DIY ideas
    diy = result.get("diy_ideas", [])
    if diy:
        components.append({
            "id": _id(surface_id, "diy-title"),
            "component": "Text",
            "text": {"literalString": "DIY Ideas"},
            "style": "h3",
        })
        for i, idea in enumerate(diy):
            if isinstance(idea, dict):
                card_id = _id(surface_id, f"diy-{i}")
                components.append({
                    "id": card_id,
                    "component": "Card",
                    "title": {"literalString": idea.get("item", idea.get("name", f"DIY {i+1}"))},
                })
                desc = idea.get("description", "")
                if desc:
                    components.append({
                        "id": _id(card_id, "desc"),
                        "component": "Text",
                        "parent": card_id,
                        "text": {"literalString": desc},
                        "style": "body",
                    })
                idea_cost = idea.get("estimated_cost", 0)
                if idea_cost:
                    components.append({
                        "id": _id(card_id, "cost"),
                        "component": "KeyValue",
                        "parent": card_id,
                        "label": {"literalString": "Est. Cost"},
                        "value": {"literalString": f"${float(idea_cost):,.0f}"},
                    })
            else:
                components.append({
                    "id": _id(surface_id, f"diy-{i}"),
                    "component": "Text",
                    "text": {"literalString": f"• {idea}"},
                    "style": "body",
                })

    # Purchased items
    purchased = result.get("purchased_items", [])
    if purchased:
        components.append({
            "id": _id(surface_id, "purchased-title"),
            "component": "Text",
            "text": {"literalString": "Items to Purchase"},
            "style": "h3",
        })
        # Render as DataTable if items are dicts
        if purchased and isinstance(purchased[0], dict):
            rows = []
            for item in purchased:
                rows.append({
                    "item": item.get("item", item.get("name", "")),
                    "cost": f"${float(item.get('estimated_cost', item.get('cost', 0))):,.0f}",
                })
            components.append({
                "id": _id(surface_id, "purchased-table"),
                "component": "DataTable",
                "columns": [
                    {"key": "item", "label": "Item"},
                    {"key": "cost", "label": "Cost", "align": "right"},
                ],
                "rows": rows,
            })
        else:
            for i, item in enumerate(purchased):
                components.append({
                    "id": _id(surface_id, f"purchased-{i}"),
                    "component": "Text",
                    "text": {"literalString": f"• {item}"},
                    "style": "body",
                })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Activity Coordinator Agent ──────────────────────────────────────────────

def _build_activity_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Activity Plan"},
        "style": "h2",
    })

    activities = result.get("activities", [])
    total_time = result.get("total_activity_time_minutes", 0)
    notes = result.get("notes", "")

    for i, act in enumerate(activities):
        card_id = _id(surface_id, f"act-{i}")
        act_name = act.get("name", f"Activity {i + 1}") if isinstance(act, dict) else str(act)
        components.append({
            "id": card_id,
            "component": "Card",
            "title": {"literalString": act_name},
        })

        if isinstance(act, dict):
            # Type badge with color coding
            act_type = act.get("type", "")
            if act_type:
                type_color = {"high-energy": "red", "relaxed": "green", "mixed": "blue"}.get(act_type, "blue")
                components.append({
                    "id": _id(card_id, "type"),
                    "component": "Badge",
                    "parent": card_id,
                    "text": {"literalString": act_type.replace("-", " ").title()},
                    "color": type_color,
                })

            # Age suitability badge
            age = act.get("age_suitability", "")
            if age:
                components.append({
                    "id": _id(card_id, "age"),
                    "component": "Badge",
                    "parent": card_id,
                    "text": {"literalString": age.title()},
                    "color": "purple",
                })

            # Description
            desc = act.get("description", "")
            if desc:
                components.append({
                    "id": _id(card_id, "desc"),
                    "component": "Text",
                    "parent": card_id,
                    "text": {"literalString": desc},
                    "style": "body",
                })

            # Duration
            duration = act.get("duration_minutes", 0)
            if duration:
                components.append({
                    "id": _id(card_id, "duration"),
                    "component": "KeyValue",
                    "parent": card_id,
                    "label": {"literalString": "Duration"},
                    "value": {"literalString": f"{duration} min"},
                })

            # Materials needed
            materials = act.get("materials_needed", [])
            if materials:
                components.append({
                    "id": _id(card_id, "materials"),
                    "component": "KeyValue",
                    "parent": card_id,
                    "label": {"literalString": "Materials"},
                    "value": {"literalString": ", ".join(materials)},
                })

    if total_time:
        components.append({
            "id": _id(surface_id, "total-time"),
            "component": "KeyValue",
            "label": {"literalString": "Total Activity Time"},
            "value": {"literalString": f"{total_time} minutes"},
        })

    if notes:
        components.append({
            "id": _id(surface_id, "notes"),
            "component": "Text",
            "text": {"literalString": notes},
            "style": "caption",
        })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Supplies Estimator Agent ────────────────────────────────────────────────

def _build_supplies_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Supplies Estimate"},
        "style": "h2",
    })

    supplies = result.get("supplies", [])
    if supplies:
        rows = []
        for item in supplies:
            if isinstance(item, dict):
                rows.append({
                    "category": item.get("category", "").title(),
                    "item": item.get("item", ""),
                    "qty": str(item.get("quantity", "")),
                    "unit_cost": f"${float(item.get('unit_cost', 0)):,.2f}",
                    "total": f"${float(item.get('total', 0)):,.2f}",
                })
        if rows:
            components.append({
                "id": _id(surface_id, "table"),
                "component": "DataTable",
                "columns": [
                    {"key": "category", "label": "Category"},
                    {"key": "item", "label": "Item"},
                    {"key": "qty", "label": "Qty", "align": "right"},
                    {"key": "unit_cost", "label": "Unit Cost", "align": "right"},
                    {"key": "total", "label": "Total", "align": "right"},
                ],
                "rows": rows,
            })

    total_cost = result.get("total_supplies_cost", 0)
    if total_cost:
        components.append({
            "id": _id(surface_id, "total-cost"),
            "component": "KeyValue",
            "label": {"literalString": "Total Supplies Cost"},
            "value": {"literalString": f"${float(total_cost):,.2f}"},
        })

    shopping_list = result.get("shopping_list", [])
    if shopping_list:
        components.append({
            "id": _id(surface_id, "shopping-title"),
            "component": "Text",
            "text": {"literalString": "Shopping List"},
            "style": "h3",
        })
        for i, item in enumerate(shopping_list):
            item_text = _format_list_item(item)
            components.append({
                "id": _id(surface_id, f"shop-{i}"),
                "component": "Text",
                "text": {"literalString": f"• {item_text}"},
                "style": "body",
            })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Accessibility Checker Agent ─────────────────────────────────────────────

def _build_accessibility_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Accessibility Report"},
        "style": "h2",
    })

    # Score and rating
    score = result.get("accessibility_score", 0)
    rating = result.get("rating", "")
    if score or rating:
        card_id = _id(surface_id, "score-card")
        components.append({
            "id": card_id,
            "component": "Card",
            "title": {"literalString": "Overall Assessment"},
        })
        if score:
            score_color = "green" if score >= 0.7 else ("yellow" if score >= 0.4 else "red")
            components.append({
                "id": _id(card_id, "score"),
                "component": "KeyValue",
                "parent": card_id,
                "label": {"literalString": "Score"},
                "value": {"literalString": f"{score:.0%}"},
            })
            components.append({
                "id": _id(card_id, "score-badge"),
                "component": "Badge",
                "parent": card_id,
                "text": {"literalString": rating or ("Pass" if score >= 0.7 else ("Warning" if score >= 0.4 else "Fail"))},
                "color": score_color,
            })

    # Features checklist with pass/warn/fail badges
    features = result.get("features", {})
    if features:
        components.append({
            "id": _id(surface_id, "features-title"),
            "component": "Text",
            "text": {"literalString": "Accessibility Features"},
            "style": "h3",
        })
        for i, (feature, value) in enumerate(features.items()):
            feat_id = _id(surface_id, f"feat-{i}")
            label = feature.replace("_", " ").title()

            # Determine status: True = pass (green), False = fail (red), special cases
            if feature == "stairs_only":
                # stairs_only: False is good, True is bad
                badge_color = "red" if value else "green"
                badge_text = "Yes" if value else "No"
            elif isinstance(value, bool):
                badge_color = "green" if value else "red"
                badge_text = "Pass" if value else "Fail"
            else:
                badge_color = "yellow"
                badge_text = str(value)

            row_id = _id(surface_id, f"feat-row-{i}")
            components.append({
                "id": row_id,
                "component": "Row",
            })
            components.append({
                "id": _id(row_id, "label"),
                "component": "Text",
                "parent": row_id,
                "text": {"literalString": label},
                "style": "body",
            })
            components.append({
                "id": _id(row_id, "badge"),
                "component": "Badge",
                "parent": row_id,
                "text": {"literalString": badge_text},
                "color": badge_color,
            })

    # Recommendations
    recs = result.get("recommendations", [])
    if recs:
        components.append({
            "id": _id(surface_id, "recs-title"),
            "component": "Text",
            "text": {"literalString": "Recommendations"},
            "style": "h3",
        })
        for i, rec in enumerate(recs):
            components.append({
                "id": _id(surface_id, f"rec-{i}"),
                "component": "Text",
                "text": {"literalString": f"• {rec}"},
                "style": "body",
            })

    # Required accommodations
    accommodations = result.get("required_accommodations", result.get("accommodations", []))
    if accommodations:
        components.append({
            "id": _id(surface_id, "accom-title"),
            "component": "Text",
            "text": {"literalString": "Required Accommodations"},
            "style": "h3",
        })
        for i, acc in enumerate(accommodations):
            if isinstance(acc, dict):
                # Structured accommodation: {accommodation, priority, reason, estimated_cost}
                acc_name = acc.get("accommodation", acc.get("name", f"Item {i+1}"))
                priority = acc.get("priority", "")
                reason = acc.get("reason", "")
                acc_cost = acc.get("estimated_cost", 0)
                card_id = _id(surface_id, f"accom-{i}")
                priority_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue"}.get(priority, "gray")
                components.append({
                    "id": card_id,
                    "component": "Card",
                    "title": {"literalString": acc_name},
                })
                if priority:
                    components.append({
                        "id": _id(card_id, "priority"),
                        "component": "Badge",
                        "parent": card_id,
                        "text": {"literalString": priority},
                        "color": priority_color,
                    })
                if reason:
                    components.append({
                        "id": _id(card_id, "reason"),
                        "component": "Text",
                        "parent": card_id,
                        "text": {"literalString": reason},
                        "style": "body",
                    })
                if acc_cost:
                    components.append({
                        "id": _id(card_id, "cost"),
                        "component": "KeyValue",
                        "parent": card_id,
                        "label": {"literalString": "Est. Cost"},
                        "value": {"literalString": f"${float(acc_cost):,.0f}" if isinstance(acc_cost, (int, float)) else str(acc_cost)},
                    })
            else:
                components.append({
                    "id": _id(surface_id, f"accom-{i}"),
                    "component": "Badge",
                    "text": {"literalString": str(acc)},
                    "color": "red",
                })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Logistics Coordinator Agent ─────────────────────────────────────────────

def _build_logistics_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Event Logistics"},
        "style": "h2",
    })

    # Timeline as DataTable
    timeline = result.get("timeline", [])
    if timeline:
        rows = []
        for slot in timeline:
            if isinstance(slot, dict):
                time_range = slot.get("time", "")
                end_time = slot.get("end_time", "")
                if end_time:
                    time_range = f"{time_range} - {end_time}"
                rows.append({
                    "time": time_range,
                    "activity": slot.get("activity", ""),
                    "responsible": slot.get("responsible", ""),
                })
        if rows:
            components.append({
                "id": _id(surface_id, "timeline-table"),
                "component": "DataTable",
                "columns": [
                    {"key": "time", "label": "Time"},
                    {"key": "activity", "label": "Activity"},
                    {"key": "responsible", "label": "Responsible"},
                ],
                "rows": rows,
            })

    # Key logistics info
    total_dur = result.get("total_duration_hours", 0)
    setup_time = result.get("setup_time_required", "")
    teardown_time = result.get("teardown_time_required", "")

    info_items = []
    if total_dur:
        info_items.append(("Total Duration", f"{total_dur} hours"))
    if setup_time:
        info_items.append(("Setup Time", str(setup_time)))
    if teardown_time:
        info_items.append(("Teardown Time", str(teardown_time)))

    if info_items:
        card_id = _id(surface_id, "info-card")
        components.append({
            "id": card_id,
            "component": "Card",
            "title": {"literalString": "Key Details"},
        })
        for i, (label, value) in enumerate(info_items):
            components.append({
                "id": _id(card_id, f"kv-{i}"),
                "component": "KeyValue",
                "parent": card_id,
                "label": {"literalString": label},
                "value": {"literalString": value},
            })

    _append_cost_and_warnings(components, surface_id, cost, warnings)
    return components


# ── Communication Writer Agent ──────────────────────────────────────────────

def _build_communication_result(
    surface_id: str, result: dict, cost: float, warnings: list[str]
) -> list[dict]:
    components: list[dict] = []

    components.append({
        "id": _id(surface_id, "title"),
        "component": "Text",
        "text": {"literalString": "Event Communications"},
        "style": "h2",
    })

    # Each communication type as a Card
    comm_types = [
        ("save_the_date", "Save the Date"),
        ("invitation", "Invitation"),
        ("reminder", "Reminder"),
        ("day_of_instructions", "Day-of Instructions"),
        ("rsvp_tracking", "RSVP Tracking"),
    ]

    for key, label in comm_types:
        content = result.get(key, "")
        if not content:
            continue
        card_id = _id(surface_id, f"comm-{key}")
        components.append({
            "id": card_id,
            "component": "Card",
            "title": {"literalString": label},
        })

        if isinstance(content, dict):
            # Structured communication: {subject, body, send_date, channel, etc.}
            for j, (field, val) in enumerate(content.items()):
                if field in ("body", "template", "text", "message"):
                    # Truncate long text to first 300 chars
                    text_val = str(val)[:300]
                    if len(str(val)) > 300:
                        text_val += "..."
                    components.append({
                        "id": _id(card_id, f"body-{j}"),
                        "component": "Text",
                        "parent": card_id,
                        "text": {"literalString": text_val},
                        "style": "body",
                    })
                else:
                    components.append({
                        "id": _id(card_id, f"kv-{j}"),
                        "component": "KeyValue",
                        "parent": card_id,
                        "label": {"literalString": field.replace("_", " ").title()},
                        "value": {"literalString": str(val)[:100]},
                    })
        else:
            # Plain string — truncate for display
            text_val = str(content)[:500]
            if len(str(content)) > 500:
                text_val += "\n\n*[Full text available in event plan]*"
            components.append({
                "id": _id(card_id, "text"),
                "component": "Text",
                "parent": card_id,
                "text": {"literalString": text_val},
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
                        "text": {"literalString": f"• {_format_list_item(item)}"},
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

def _format_list_item(item: Any) -> str:
    """Format a list item for display — extract name/description from dicts."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Try common name fields
        name = item.get("item", item.get("name", item.get("title", "")))
        desc = item.get("description", "")
        cost = item.get("estimated_cost", item.get("cost", 0))
        parts = []
        if name:
            parts.append(str(name))
        if desc:
            parts.append(str(desc)[:150])
        if cost:
            parts.append(f"(${float(cost):,.0f})")
        return " — ".join(parts) if parts else str(item)
    return str(item)


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
    "theme": _build_theme_result,
    "activity": _build_activity_result,
    "supplies": _build_supplies_result,
    "accessibility": _build_accessibility_result,
    "logistics": _build_logistics_result,
    "communication": _build_communication_result,
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
