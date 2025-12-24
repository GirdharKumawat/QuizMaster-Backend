from enum import Enum

# MongoDB field paths
PARTICIPANTS_USER_ID = "participants.user_id"

# Error messages
SESSION_NOT_FOUND = "Session not found."
UNAUTHORIZED = "Unauthorized."

class QuizStatus(Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"