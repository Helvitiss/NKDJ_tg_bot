from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScoreResult:
    mood_color: str
    campaigns_color: str
    geo_color: str
    creatives_color: str
    accounts_color: str
    average: float
    final_color: str
    message: str


class ScoringEngine:
    WEIGHTS = {"🟢": 2, "🟡": 1, "🔴": 0}

    def score(self, mood: str, campaigns: int, geo: int, creatives: int, accounts: int) -> ScoreResult:
        campaigns_color = "🟢" if campaigns >= 20 else "🟡" if campaigns >= 10 else "🔴"
        geo_color = "🟢" if geo >= 4 else "🟡" if geo >= 2 else "🔴"
        creatives_color = "🟢" if creatives >= 3 else "🟡" if creatives >= 1 else "🔴"
        accounts_color = "🟢" if accounts >= 4 else "🟡" if accounts >= 2 else "🔴"

        # Настроение считается отдельной метрикой и не влияет на итоговую эффективность.
        performance_colors = [campaigns_color, geo_color, creatives_color, accounts_color]
        average = sum(self.WEIGHTS[color] for color in performance_colors) / len(performance_colors)

        if average >= 1.5:
            final_color = "🟢"
            message = "молодец - так держать"
        elif average >= 0.75:
            final_color = "🟡"
            message = "сегодня передышка ?"
        else:
            final_color = "🔴"
            message = "ты в зоне риска."

        return ScoreResult(
            mood_color=mood,
            campaigns_color=campaigns_color,
            geo_color=geo_color,
            creatives_color=creatives_color,
            accounts_color=accounts_color,
            average=average,
            final_color=final_color,
            message=message,
        )
