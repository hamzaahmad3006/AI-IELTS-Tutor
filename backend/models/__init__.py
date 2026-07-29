"""ORM models package. Importing this registers all tables on Base.metadata."""

from .ai_interaction import AIInteraction
from .attempt import WritingAttempt
from .audit import AuditLog
from .content import AudioClip, ListeningQuestion, Passage, Question
from .cue_card import CueCard
from .grammar import GrammarLesson
from .listening import ListeningAttempt
from .profile import LearnerProfile
from .reading import ReadingAttempt
from .speaking import SpeakingAttempt
from .user import RefreshToken, User
from .vocabulary import VocabItem, VocabReview
from .weakness import Weakness
from .writing_prompt import WritingPrompt

__all__ = [
    "User",
    "RefreshToken",
    "LearnerProfile",
    "WritingAttempt",
    "Passage",
    "Question",
    "ReadingAttempt",
    "AudioClip",
    "ListeningQuestion",
    "ListeningAttempt",
    "SpeakingAttempt",
    "AIInteraction",
    "AuditLog",
    "Weakness",
    "WritingPrompt",
    "CueCard",
    "GrammarLesson",
    "VocabItem",
    "VocabReview",
]
