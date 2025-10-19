"""
Display formatter for GitHub statistics in neofetch style
"""

from typing import Dict, Any, Optional
import shutil
import sys
import re
import unicodedata
from datetime import datetime


class DisplayFormatter:
    """Formats and displays GitHub stats in a neofetch-style layout."""

    def __init__(self):
        """Initialize the display formatter."""
        self.terminal_width = shutil.get_terminal_size().columns
        self.enable_color = sys.stdout.isatty()

    def display(self, username: str, user_data: Dict[str, Any],
                stats: Dict[str, Any]) -> None:
        """
        Display GitHub statistics in neofetch style.

        Args:
            username: GitHub username
            user_data: User profile data
            stats: User statistics data
        """
        # Determine layout based on terminal width
        layout = self._determine_layout()

        if layout == 'minimal':
            # Only show contribution graph
            self._display_minimal(username, stats)
        elif layout == 'compact':
            # Show graph and key info
            self._display_compact(username, user_data, stats)
        else:
            # Full layout with all sections
            self._display_full(username, user_data, stats)

        print()  # Empty line at the end

    def _determine_layout(self) -> str:
        """Determine layout based on terminal width."""
        if self.terminal_width < 80:
            return 'minimal'
        elif self.terminal_width < 140:
            return 'compact'
        else:
            return 'full'

    def _display_minimal(self, username: str, stats: Dict[str, Any]) -> None:
        """Display only contribution graph for narrow terminals."""
        contrib_graph = stats.get('contribution_graph', [])
        graph_lines = self._get_contribution_graph_lines(
            contrib_graph,
            username,
            width_constraint=self.terminal_width - 4,
            include_sections=False
        )
        for line in graph_lines:
            print(line)

    def _display_compact(self, username: str, user_data: Dict[str, Any],
                         stats: Dict[str, Any]) -> None:
        """Display graph and minimal info side-by-side."""
        contrib_graph = stats.get('contribution_graph', [])
        graph_width = max(40, (self.terminal_width - 10) // 2)
        graph_lines = self._get_contribution_graph_lines(
            contrib_graph,
            username,
            width_constraint=graph_width,
            include_sections=False
        )

        info_lines = self._format_user_info_compact(user_data, stats)

        # Display side-by-side
        max_lines = max(len(graph_lines), len(info_lines))
        for i in range(max_lines):
            graph_part = (graph_lines[i] if i < len(graph_lines) else "")
            graph_len = self._display_width(graph_part)
            padding = " " * max(0, graph_width - graph_len)

            info_part = (info_lines[i] if i < len(info_lines) else "")
            print(f"{graph_part}{padding}  {info_part}")

    def _display_full(self, username: str, user_data: Dict[str, Any],
                      stats: Dict[str, Any]) -> None:
        """Display full layout with graph and all info sections."""
        contrib_graph = stats.get('contribution_graph', [])
        recent_weeks = self._get_recent_weeks(contrib_graph)
        graph_width = max(50, (self.terminal_width - 10) // 2)
        left_side = self._get_contribution_graph_lines(
            contrib_graph,
            username,
            width_constraint=graph_width,
            include_sections=False
        )

        achievements = self._build_achievements(recent_weeks)
        overview_lines = self._format_overview(stats)
        pull_request_lines = self._format_pull_requests(stats)
        issue_lines = self._format_issues(stats)

        section_columns = [
            achievements,
            overview_lines,
            pull_request_lines,
            issue_lines,
        ]

        combined_sections = self._combine_section_grid(
            section_columns, width_limit=graph_width
        )
        if combined_sections:
            left_side.append("")
            left_side.extend(combined_sections)

        info_lines = self._format_user_info(user_data, stats)
        language_lines = self._format_languages(stats)

        right_side = list(info_lines)
        if language_lines:
            right_side.append("")
            right_side.extend(language_lines)

        # Display side-by-side
        max_left_width = max(
            self._display_width(line) for line in left_side
        ) if left_side else 0

        for i in range(max(len(left_side), len(right_side))):
            if i < len(left_side):
                left_raw = left_side[i]
            else:
                left_raw = ""

            raw_length = self._display_width(left_raw)
            padding = " " * max(0, max_left_width - raw_length)
            left_part = f"{left_raw}{padding}"

            info_part = right_side[i] if i < len(right_side) else ""
            print(f"{left_part}  {info_part}")

    def _get_contribution_graph_lines(self, weeks_data: list,
                                      username: str,
                                      width_constraint: int = None,
                                      include_sections: bool = True) -> list:
        """
        Get contribution graph as lines for display.

        Args:
            weeks_data: List of weeks with contribution data
            username: GitHub username
            width_constraint: Maximum width in characters (None for auto)

        Returns:
            List of strings representing graph lines
        """
        recent_weeks = self._get_recent_weeks(weeks_data)
        total_contribs = self._calculate_total_contributions(recent_weeks)

        header_lines = self._graph_header(username, total_contribs)

        if not recent_weeks:
            return [*header_lines, *self._empty_graph_placeholder()]

        # Calculate how many weeks we can fit
        if width_constraint is None:
            width_constraint = self.terminal_width - 8

        max_weeks = self._calculate_max_weeks(width_constraint)
        display_weeks = recent_weeks[-max_weeks:] if len(
            recent_weeks) > max_weeks else recent_weeks

        # Prepare rows for each day of the week (Sun-Sat)
        day_rows = [[] for _ in range(7)]
        for week in display_weeks:
            days = week.get('contributionDays', [])
            for idx in range(7):
                day = days[idx] if idx < len(days) else {}
                count = day.get('contributionCount', 0)
                block = self._get_contribution_block_spaced(count)
                day_rows[idx].append(block)

        lines = [*header_lines]

        month_line = self._build_month_line_spaced(display_weeks)
        if month_line.strip():
            lines.append(month_line)

        # Add grid rows (no vertical spacing between rows)
        for row_idx, row in enumerate(day_rows):
            lines.append(f"    {''.join(row)}")

        # Add achievements section
        if include_sections:
            achievements = self._build_achievements(recent_weeks)
            if achievements:
                lines.append("")
                lines.extend(achievements)

        return lines

    def _format_user_info_compact(self, user_data: Dict[str, Any],
                                  stats: Dict[str, Any]) -> list:
        """Format minimal user info for compact layout."""
        lines = []

        name = user_data.get('name') or user_data.get('login', 'unknown')
        total_contributions = stats.get('total_contributions')
        if total_contributions is None:
            total_contributions = self._calculate_total_contributions(
                stats.get('contribution_graph', [])
            )

        headline = f"{name} - {total_contributions:,} contributions this year"
        lines.append(self._colorize(headline, "accent"))

        bio = user_data.get('bio')
        if bio:
            trimmed = bio.strip().replace('\n', ' ')[:60]
            lines.append(self._colorize(trimmed, 'muted'))

        lines.append(f"Repos: {stats.get('total_repos', 0)}")
        lines.append(f"Stars: {stats.get('total_stars', 0)}")

        return lines

    def _format_user_info(self, user_data: Dict[str, Any],
                          stats: Dict[str, Any]) -> list:
        """
        Format user information lines.

        Args:
            user_data: User profile data
            stats: User statistics data

        Returns:
            List of formatted info strings
        """
        lines = []

        name = user_data.get('name') or user_data.get('login', 'unknown')
        total_contributions = stats.get('total_contributions')
        if total_contributions is None:
            total_contributions = self._calculate_total_contributions(
                stats.get('contribution_graph', [])
            )

        # Format user line with colored segments
        contrib_str = self._colorize(f"{total_contributions:,}", 'orange')
        name_str = self._colorize(name, 'header')
        phrase_str = self._colorize('contributions this year', 'header')
        user_line = f"{name_str} - {contrib_str} {phrase_str}"
        lines.append(user_line)

        plain_line = (
            f"{name} - {total_contributions:,} contributions this year"
        )
        lines.append(
            self._colorize("─" * len(plain_line), "muted")
        )

        def add_line(label: str, value: str) -> None:
            if value:
                lines.append(f"{self._label(label)} {value}")

        bio = user_data.get('bio', '')
        if bio:
            trimmed_bio = bio.strip().replace('\n', ' ')
            lines.append(f"{self._label('Bio')} {trimmed_bio[:80]}")

        add_line('Company', user_data.get('company'))
        add_line('Website', user_data.get('blog'))

        return lines

    def _format_overview(self, stats: Dict[str, Any]) -> list:
        """Format overview statistics for left column."""
        lines = []
        lines.extend(self._section_header("Overview"))

        total_repos = stats.get('total_repos', 0)
        total_stars = stats.get('total_stars', 0)
        total_forks = stats.get('total_forks', 0)

        lines.append(self._format_stat_line('Repositories', total_repos))
        lines.append(self._format_stat_line('Stars', total_stars))
        lines.append(self._format_stat_line('Forks', total_forks))

        return lines

    def _format_languages(self, stats: Dict[str, Any]) -> list:
        """Format language distribution for right column."""
        languages = stats.get('languages', {})
        if not languages:
            return []

        lines = []
        lines.extend(self._section_header("Top Languages"))

        sorted_langs = sorted(
            languages.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]

        for lang, percentage in sorted_langs:
            lines.append(self._format_language_line(lang, percentage))

        return lines

    def _format_pull_requests(self, stats: Dict[str, Any]) -> list:
        """Format pull request dashboard section."""
        pr_data = stats.get('pull_requests') or {}
        groups = [
            ('Awaiting Review', pr_data.get('awaiting_review', {})),
            ('Your Open PRs', pr_data.get('open', {})),
            ('Mentions', pr_data.get('mentions', {})),
        ]
        return self._format_dashboard_section('Pull Requests', groups)

    def _format_issues(self, stats: Dict[str, Any]) -> list:
        """Format issues dashboard section."""
        issue_data = stats.get('issues') or {}
        groups = [
            ('Assigned', issue_data.get('assigned', {})),
            ('Created (open)', issue_data.get('created', {})),
            ('Mentions', issue_data.get('mentions', {})),
        ]
        return self._format_dashboard_section('Issues', groups)

    def _render_progress_bar(self, percentage: float,
                             width: int = 24) -> str:
        """Render a progress bar for percentage values."""
        width = max(width, 1)
        capped_percentage = max(0.0, min(percentage, 100.0))
        filled = int(round((capped_percentage / 100) * width))
        filled = min(filled, width)
        empty = width - filled

        filled_segment = "█" * filled
        empty_segment = "░" * empty

        if self.enable_color and filled_segment:
            filled_segment = self._colorize(filled_segment, 'green')

        return f"[{filled_segment}{empty_segment}]"

    def _render_progress_bar_no_brackets(self, percentage: float,
                                         width: int = 24) -> str:
        """Render a progress bar without brackets for percentage values."""
        width = max(width, 1)
        capped_percentage = max(0.0, min(percentage, 100.0))
        filled = int(round((capped_percentage / 100) * width))
        filled = min(filled, width)
        empty = width - filled

        filled_segment = "█" * filled
        empty_segment = "░" * empty

        if self.enable_color and filled_segment:
            filled_segment = self._colorize(filled_segment, 'green')

        return f"{filled_segment}{empty_segment}"

    def _section_header(self, title: str) -> list:
        """Create a stylized section header."""
        heading = title.upper()
        underline = "─" * len(heading)
        return [
            self._colorize(heading, 'header'),
            self._colorize(underline, 'muted')
        ]

    def _label(self, text: str) -> str:
        """Format labels with consistent padding."""
        label = f"{text}:"
        padded = f"{label:<12}"
        if self.enable_color:
            return self._colorize(padded, 'bold')
        return padded

    def _format_stat_line(self, label: str, value: Any) -> str:
        """Format a single statistics line."""
        return f"{self._label(label)} {value}"

    def _format_language_line(self, language: str,
                              percentage: float) -> str:
        """Format language entry with progress bar."""
        # Use consistent padding without relying on label() which adds colors
        lang_label = f"{language}:"
        padded_label = f"{lang_label:<12}"
        if self.enable_color:
            padded_label = self._colorize(padded_label, 'bold')

        bar = self._render_progress_bar_no_brackets(percentage)
        return f"{padded_label} {bar} {percentage:5.1f}%"

    def _format_dashboard_section(self, title: str,
                                  groups: list) -> list:
        """Format a dashboard section with grouped items."""
        if not groups:
            return []

        lines = []
        lines.extend(self._section_header(title))

        label_width = max((len(label) for label, _ in groups), default=0) + 2

        for idx, (label, data) in enumerate(groups):
            total = (data or {}).get('total_count', 0)
            label_text = self._dashboard_label(label, label_width)
            lines.append(f"{label_text} {total}")

            items = (data or {}).get('items', [])[:3]
            if not items:
                lines.append("  • None")
            else:
                for item in items:
                    lines.append(self._format_dashboard_item(item))

            if idx < len(groups) - 1:
                lines.append("")

        return lines

    def _dashboard_label(self, text: str, width: int = 20) -> str:
        label = f"{text}:"
        padded = f"{label:<{width}}"
        if self.enable_color:
            return self._colorize(padded, 'bold')
        return padded

    def _format_dashboard_item(self, item: Dict[str, Any],
                               title_width: int = 24,
                               repo_width: int = 16) -> str:
        title = self._truncate_text(item.get('title', ''), title_width)
        repo = item.get('repo', '')
        repo_part = ''
        if repo:
            repo_part = f" ({self._truncate_text(repo, repo_width)})"

        bullet = f"• {title}{repo_part}"
        return f"  {bullet}"

    def _truncate_text(self, text: str, max_width: int) -> str:
        if self._display_width(text) <= max_width:
            return text

        ellipsis = '…'
        truncated = ''
        for char in text:
            if self._display_width(truncated + char + ellipsis) > max_width:
                break
            truncated += char
        return truncated + ellipsis

    def _graph_header(self, username: str, total_contributions: int) -> list:
        """Return standardized header lines for the contribution graph."""
        # Header intentionally blank; graph should start with month labels.
        return []

    def _calculate_max_weeks(self, width_available: int) -> int:
        """Calculate how many weeks fit in available width."""
        # Each week is 2 chars wide (■ )
        block_width = 2
        header_margin = 4
        available_for_graph = width_available - header_margin
        max_weeks = max(13, available_for_graph // block_width)
        return min(52, max_weeks)

    def _build_month_line(self, weeks_data: list) -> str:
        """Build a month label line aligned with contribution weeks."""
        if not weeks_data:
            return ""

        month_chars = []
        last_month = None

        for week in weeks_data:
            days = week.get('contributionDays', [])
            if not days:
                continue

            first_day = days[0].get('date')
            if not first_day:
                continue

            try:
                date_obj = datetime.fromisoformat(first_day)
            except ValueError:
                continue

            month_abbr = date_obj.strftime('%b')
            if month_abbr != last_month:
                month_chars.append(month_abbr)
                last_month = month_abbr
            else:
                month_chars.append("   ")

        month_string = ' '.join(month_chars)
        return f"    {month_string}" if month_string else ""

    def _build_month_line_spaced(self, weeks_data: list) -> str:
        """Build month labels aligned with contribution grid (Kusa style)."""
        if not weeks_data:
            return ""

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                  "Sep", "Oct", "Nov", "Dec"]

        # Build month string with proper spacing (each week = 2 chars wide)
        month_line = ""

        for idx, week in enumerate(weeks_data):
            days = week.get('contributionDays', [])
            if not days:
                continue

            first_day = days[0].get('date')
            if not first_day:
                continue

            try:
                date_obj = datetime.fromisoformat(first_day)
                current_month = date_obj.month
            except ValueError:
                continue

            # Check if this is a new month
            if idx == 0:
                month_line += months[current_month - 1]
            else:
                prev_week = weeks_data[idx - 1]
                prev_days = prev_week.get('contributionDays', [])
                if prev_days:
                    prev_first_day = prev_days[0].get('date')
                    if prev_first_day:
                        try:
                            prev_date_obj = datetime.fromisoformat(
                                prev_first_day
                            )
                            prev_month = prev_date_obj.month
                            if current_month != prev_month:
                                # New month - add spacing and month name
                                target_width = (idx + 1) * 2
                                current_width = len(month_line)
                                needed_space = target_width - current_width
                                if needed_space > 0:
                                    month_line += " " * (
                                        needed_space - len(months[
                                            current_month - 1
                                        ])
                                    )
                                month_line += months[current_month - 1]
                        except ValueError:
                            pass

        return f"    {month_line}"

    def _build_legend(self) -> str:
        """Create contribution intensity legend."""
        buckets = [0, 1, 4, 8, 16]
        blocks = ' '.join(
            self._get_contribution_block_spaced(b) for b in buckets
        )
        less = self._colorize('Less', 'muted') if self.enable_color else 'Less'
        more = self._colorize('More', 'muted') if self.enable_color else 'More'
        return f"    {less} {blocks} {more}"

    def _build_legend_spaced(self) -> str:
        """Build legend with GitHub's actual color palette (Kusa style)."""
        # Color palette matching GitHub
        colors = [
            (0, '\033[38;2;235;237;240m'),      # #ebedf0 - Less
            (1, '\033[38;2;155;233;168m'),      # #9be9a8
            (4, '\033[38;2;64;196;99m'),        # #40c463
            (8, '\033[38;2;48;161;78m'),        # #30a14e
            (16, '\033[38;2;33;110;57m'),       # #216e39 - More
        ]

        reset = '\033[0m'

        if not self.enable_color:
            blocks = ' '.join(['■'] * 5)
            return f"    Less {blocks} More"

        blocks_str = ""
        for count, color in colors:
            blocks_str += f"{color}■{reset} "

        return f"    Less {blocks_str}More"

    def _build_achievements(self, weeks_data: list) -> list:
        """Build achievements section with streaks and stats."""
        if not weeks_data:
            return []

        lines = []

        # Calculate streaks
        current_streak, max_streak = self._calculate_streaks(weeks_data)

        # Calculate total contributions
        total_contribs = self._calculate_total_contributions(weeks_data)

        # Determine achievements
        achievements_list = self._get_achievement_entries(
            current_streak, max_streak, total_contribs
        )

        if achievements_list:
            title = 'ACHIEVEMENTS'
            lines.append(self._colorize(title, 'header'))
            lines.append(self._colorize('─' * len(title), 'muted'))

            label_width = max(
                self._display_width(f"{entry['icon']} {entry['label']}")
                for entry in achievements_list
            )

            for entry in achievements_list:
                icon_label = f"{entry['icon']} {entry['label']}"
                stripped_len = self._display_width(icon_label)
                padding = " " * max(0, label_width - stripped_len)
                value = entry['value']
                lines.append(f"{icon_label}{padding}  {value}")

        return lines

    def _calculate_streaks(self, weeks_data: list) -> tuple:
        """Calculate current and max contribution streaks."""
        if not weeks_data:
            return 0, 0

        # Flatten all contribution counts in reverse chronological order
        all_contributions = []
        for week in weeks_data:
            for day in week.get('contributionDays', []):
                all_contributions.append(day.get('contributionCount', 0))

        all_contributions.reverse()

        current_streak = 0
        max_streak = 0
        temp_streak = 0

        for contrib in all_contributions:
            if contrib > 0:
                temp_streak += 1
                current_streak = temp_streak
            else:
                if temp_streak > max_streak:
                    max_streak = temp_streak
                temp_streak = 0

        if temp_streak > max_streak:
            max_streak = temp_streak

        return current_streak, max_streak

    def _get_achievement_entries(self, current_streak: int, max_streak: int,
                                 total_contribs: int) -> list:
        """Generate structured achievement entries for display."""
        entries = []

        def color_icon(icon: str, color: str) -> str:
            if not self.enable_color:
                return icon
            return self._colorize(icon, color)

        # Streak achievements
        if current_streak > 0:
            entries.append({
                'icon': color_icon("🔥", 'red'),
                'label': 'Current Streak',
                'value': (
                    f"{current_streak} day"
                    f"{'s' if current_streak != 1 else ''}"
                )
            })

        if max_streak > 0:
            entries.append({
                'icon': color_icon("⭐", 'yellow'),
                'label': 'Best Streak',
                'value': (
                    f"{max_streak} day"
                    f"{'s' if max_streak != 1 else ''}"
                )
            })

        # Contribution milestones (shortened values for consistent width)
        if total_contribs >= 10000:
            entries.append({
                'icon': color_icon("💎", 'magenta'),
                'label': 'Contributions',
                'value': '10k+'
            })
        elif total_contribs >= 5000:
            entries.append({
                'icon': color_icon("👑", 'yellow'),
                'label': 'Contributions',
                'value': '5k+'
            })
        elif total_contribs >= 1000:
            entries.append({
                'icon': color_icon("🎖️", 'cyan'),
                'label': 'Contributions',
                'value': '1k+'
            })
        elif total_contribs >= 100:
            entries.append({
                'icon': color_icon("🏆", 'yellow'),
                'label': 'Contributions',
                'value': '100+'
            })

        return entries

    def _get_recent_weeks(self, weeks_data: list, limit: int = 52) -> list:
        """Return the most recent weeks up to the specified limit."""
        if not weeks_data:
            return []
        return weeks_data[-limit:] if len(weeks_data) > limit else weeks_data

    def _combine_section_grid(self, columns: list,
                              width_limit: Optional[int] = None) -> list:
        """Combine multiple sections into aligned columns."""
        active_columns = [col for col in columns if col]
        if not active_columns:
            return []

        indent = "    "
        gap = "   "
        gap_width = len(gap)
        indent_width = len(indent)

        column_info = [
            (col, max((self._display_width(line) for line in col), default=0))
            for col in active_columns
        ]

        rows = []
        current_row = []
        current_width = indent_width

        for col, width in column_info:
            projected = width if not current_row else width + gap_width
            if (width_limit is not None and current_row and
                    current_width + projected > width_limit):
                rows.append(current_row)
                current_row = []
                current_width = indent_width

            if current_row:
                current_width += gap_width + width
            else:
                current_width += width

            current_row.append((col, width))

        if current_row:
            rows.append(current_row)

        combined = []
        for row_idx, row in enumerate(rows):
            max_lines = max(len(col) for col, _ in row)
            for line_idx in range(max_lines):
                parts = []
                for col_idx, (col, width) in enumerate(row):
                    text = col[line_idx] if line_idx < len(col) else ""
                    pad_width = width - self._display_width(text)
                    pad = " " * max(0, pad_width)
                    spacer = gap if col_idx < len(row) - 1 else ""
                    parts.append(f"{text}{pad}{spacer}")

                combined.append(indent + "".join(parts).rstrip())

            if row_idx < len(rows) - 1:
                combined.append("")

        return combined

    def _calculate_total_contributions(self, weeks_data: list) -> int:
        """Sum total contributions across all provided weeks."""
        total = 0
        for week in weeks_data:
            for day in week.get('contributionDays', []):
                total += day.get('contributionCount', 0)
        return total

    def _empty_graph_placeholder(self) -> list:
        """Placeholder lines when contribution data is missing."""
        message = "No contribution data yet"
        if self.enable_color:
            text = self._colorize(message, 'muted')
        else:
            text = message
        return [f"    {text}", ""]

    def _colorize(self, text: str, color: str) -> str:
        """
        Apply ANSI color codes to text.

        Args:
            text: Text to colorize
            color: Color name or code

        Returns:
            Colorized text string
        """
        if not text:
            return text

        colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'dim': '\033[2m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'orange': '\033[38;2;255;165;0m',
            'accent': '\033[1m',
            'header': '\033[38;2;118;215;161m',
            'muted': '\033[2m'
        }

        color_code = colors.get(color.lower())
        reset = colors['reset']

        if not self.enable_color or not color_code:
            return text

        return f"{color_code}{text}{reset}"

    def _format_date(self, date_string: str) -> str:
        """
        Format ISO date string to human-readable format.

        Args:
            date_string: ISO format date string

        Returns:
            Human-readable date string
        """
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y')
        except (ValueError, AttributeError):
            return date_string

    def _get_contribution_block(self, count: int) -> str:
        """Return a fixed-width block representing contribution intensity."""
        if not self.enable_color:
            if count == 0:
                return '░ '
            elif count < 3:
                return '▒ '
            elif count < 7:
                return '▓ '
            elif count < 13:
                return '█ '
            else:
                return '██'

        reset = '\033[0m'
        if count == 0:
            color = '\033[48;5;238m'
        elif count < 3:
            color = '\033[48;5;28m'
        elif count < 7:
            color = '\033[48;5;34m'
        elif count < 13:
            color = '\033[48;5;40m'
        else:
            color = '\033[48;5;82m'

        return f"{color}  {reset}"

    def _get_contribution_block_spaced(self, count: int) -> str:
        """
        Return a contribution block matching Kusa design.
        Uses a solid square (■) followed by a space: "■ "
        Color intensity based on contribution count.
        """
        if not self.enable_color:
            return '■ '

        reset = '\033[0m'
        # Map contributions to GitHub's color palette
        if count == 0:
            # #ebedf0 - very light gray
            color = '\033[38;2;235;237;240m'
        elif count < 3:
            # #9be9a8 - light green
            color = '\033[38;2;155;233;168m'
        elif count < 7:
            # #40c463 - medium green
            color = '\033[38;2;64;196;99m'
        elif count < 13:
            # #30a14e - darker green
            color = '\033[38;2;48;161;78m'
        else:
            # #216e39 - darkest green
            color = '\033[38;2;33;110;57m'

        # Use solid square block + space = 2 chars wide
        return f"{color}■{reset} "

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        if not text:
            return ''

        ansi_pattern = re.compile(r'\033\[[0-9;]*m')
        return ansi_pattern.sub('', text)

    def _display_width(self, text: str) -> int:
        """Calculate display width accounting for wide characters."""
        if not text:
            return 0

        clean = self._strip_ansi(text)
        width = 0
        for char in clean:
            if unicodedata.combining(char):
                continue

            east_asian = unicodedata.east_asian_width(char)
            if east_asian in ('F', 'W'):
                width += 2
            elif east_asian == 'A':
                width += 1  # Treat ambiguous width as narrow for western fonts
            else:
                width += 1
        return width
