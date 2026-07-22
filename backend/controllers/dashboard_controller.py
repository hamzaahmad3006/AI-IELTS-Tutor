"""Dashboard controller: assembles the home overview payload."""

from __future__ import annotations

from .base import CamelModel


class BandPrediction(CamelModel):
    predicted_band: float
    confidence: float
    distance_to_target: float
    based_on_sessions: int
    progress_to_target: float


class DailyCoachMessage(CamelModel):
    id: str
    title: str
    message: str


class ModuleProgress(CamelModel):
    module: str
    current_level: float
    is_active: bool


class ChecklistItem(CamelModel):
    id: str
    title: str
    subtitle: str
    is_completed: bool
    completed_at: str | None
    priority: str | None


class DashboardData(CamelModel):
    greeting_name: str
    streak_days: int
    prediction: BandPrediction
    coach: DailyCoachMessage
    modules: list[ModuleProgress]
    checklist: list[ChecklistItem]
    checklist_completion_pct: int


class DashboardController:
    @staticmethod
    def overview(user_id: str) -> DashboardData:
        # TODO: derive from real attempts, scores, weaknesses and predictions.
        return DashboardData(
            greeting_name="Sarah",
            streak_days=5,
            prediction=BandPrediction(
                predicted_band=7.0,
                confidence=0.72,
                distance_to_target=0.5,
                based_on_sessions=3,
                progress_to_target=0.78,
            ),
            coach=DailyCoachMessage(
                id="coach_1",
                title="Daily Coach",
                message="You're doing great in Lexical Resource!",
            ),
            modules=[
                ModuleProgress(module="speaking", current_level=7.5, is_active=True),
                ModuleProgress(module="writing", current_level=6.5, is_active=False),
                ModuleProgress(module="reading", current_level=7.0, is_active=False),
                ModuleProgress(module="listening", current_level=7.5, is_active=False),
            ],
            checklist=[
                ChecklistItem(
                    id="task_1",
                    title="Speaking Drill - Part 2 Topics",
                    subtitle="Completed 10:30 AM",
                    is_completed=True,
                    completed_at="2026-07-22T10:30:00Z",
                    priority=None,
                ),
                ChecklistItem(
                    id="task_2",
                    title="1 Writing Task 1 Essay",
                    subtitle="Priority: High",
                    is_completed=False,
                    completed_at=None,
                    priority="high",
                ),
                ChecklistItem(
                    id="task_3",
                    title='Vocabulary: Synonyms for "Important"',
                    subtitle="15 min session",
                    is_completed=False,
                    completed_at=None,
                    priority=None,
                ),
            ],
            checklist_completion_pct=50,
        )
