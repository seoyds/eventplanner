"""Custom MCP tools for the Logistics Coordinator agent."""
from claude_agent_sdk import tool


@tool("create_timeline_slot", "Compute start and end times for a schedule slot", {
    "start_time": str,
    "duration_minutes": int,
    "label": str,
})
async def create_timeline_slot(args):
    """Calculate end time from HH:MM start time and duration in minutes."""
    from datetime import datetime, timedelta

    start_str = args["start_time"]
    duration = args["duration_minutes"]
    label = args["label"]

    try:
        start_dt = datetime.strptime(start_str, "%H:%M")
        end_dt = start_dt + timedelta(minutes=duration)
        end_str = end_dt.strftime("%H:%M")

        return {
            "content": [{
                "type": "text",
                "text": (
                    f"Timeline slot '{label}': {start_str} - {end_str} "
                    f"({duration} minutes)"
                ),
            }]
        }
    except ValueError as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error parsing time '{start_str}': {e}. Use HH:MM format (e.g. 14:30).",
            }]
        }
