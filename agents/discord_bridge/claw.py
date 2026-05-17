"""Discord Bridge heartbeat — wraps the approval worker for NemoClaw management."""

from workers.discord_bridge import run_bot


def heartbeat() -> None:
    """Start the Discord approval worker. Blocks until the bot disconnects."""
    run_bot()
