"""In-memory state manager and core game logic.

Maps room codes to Room objects. Contains functions for:
- Room creation and lookup
- Room code generation
- Vote submission and reset
- Average calculation (excluding ? and ☕)
- Auto-reveal check
- Disconnect grace period handling
- Moderator inheritance
"""
