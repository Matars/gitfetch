from typing import Dict, Any, List, Tuple
from .constants import API_TIMEOUT_MEDIUM


def calculate_current_streak(contrib_graph: List[Dict[str, Any]]) -> int:
    """
    Calculate the current contribution streak from contribution graph.

    Args:
        contrib_graph: List of weeks with contribution data

    Returns:
        Current streak of consecutive days with contributions
    """
    try:
        all_contributions = []
        for week in contrib_graph:
            for day in week.get("contributionDays", []):
                all_contributions.append(day.get("contributionCount", 0))

        all_contributions.reverse()
        streak = 0
        for contrib in all_contributions:
            if contrib > 0:
                streak += 1
            else:
                break
        return streak
    except Exception:
        return 0


def calculate_max_streak(contrib_graph: List[Dict[str, Any]]) -> int:
    """
    Calculate the maximum (best) contribution streak from contribution graph.

    Args:
        contrib_graph: List of weeks with contribution data

    Returns:
        Maximum streak of consecutive days with contributions
    """
    try:
        all_contributions = []
        for week in contrib_graph:
            for day in week.get("contributionDays", []):
                all_contributions.append(day.get("contributionCount", 0))

        max_streak = 0
        temp_streak = 0
        for contrib in all_contributions:
            if contrib > 0:
                temp_streak += 1
                if temp_streak > max_streak:
                    max_streak = temp_streak
            else:
                temp_streak = 0
        return max_streak
    except Exception:
        return 0


def calculate_total_contributions(contrib_graph: List[Dict[str, Any]]) -> int:
    """
    Calculate total contributions from contribution graph.

    Args:
        contrib_graph: List of weeks with contribution data

    Returns:
        Total contributions across all weeks
    """
    try:
        total = 0
        for week in contrib_graph:
            for day in week.get("contributionDays", []):
                total += day.get("contributionCount", 0)
        return total
    except Exception:
        return 0


def calculate_streaks(weeks_data: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Calculate both current and max contribution streaks from weeks data.

    Args:
        weeks_data: List of weeks with contribution data

    Returns:
        Tuple of (current_streak, max_streak)
    """
    if not weeks_data:
        return 0, 0

    all_contributions = []
    for week in weeks_data:
        for day in week.get("contributionDays", []):
            all_contributions.append(day.get("contributionCount", 0))

    all_contributions.reverse()

    current_streak = 0
    max_streak = 0
    temp_streak = 0

    for contrib in all_contributions:
        if contrib > 0:
            current_streak += 1
            temp_streak += 1
            if temp_streak > max_streak:
                max_streak = temp_streak
        else:
            break

    return current_streak, max_streak
