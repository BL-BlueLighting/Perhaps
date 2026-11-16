"""
doas -su mylife.root
演出人员表 (credits scroller)

The old implementation measured every character as one or two columns.  That
is wrong for combining marks, ZWJ emoji, variation selectors and tabs; use
``wcwidth`` when it is available (it is a dependency of ``rich`` anyway).
"""

from __future__ import annotations

import shutil
import sys
import time
import unicodedata

try:
    from wcwidth import wcwidth as _wcwidth
    from wcwidth import wcswidth as _wcswidth
except ImportError:  # pragma: no cover - fallback for minimal environments
    def _wcwidth(char: str) -> int:
        if unicodedata.combining(char):
            return 0
        return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1

    def _wcswidth(text: str) -> int:
        return sum(_wcwidth(char) for char in text)


class MemberTable:
    @staticmethod
    def wlen(s: str) -> int:
        """Terminal display width of *s* (tabs expanded to 4 columns)."""
        expanded = s.expandtabs(4)
        width = _wcswidth(expanded)
        if width >= 0:
            return width
        return sum(max(0, _wcwidth(char)) for char in expanded)

    @classmethod
    def wrap_line(cls, s: str, width: int) -> list[str]:
        if width <= 0:
            raise ValueError("wrap width must be positive")
        if not s:
            return [""]
        out: list[str] = []
        current: list[str] = []
        current_width = 0
        for char in s.expandtabs(4):
            char_width = max(0, _wcwidth(char))
            if char_width == 0:
                current.append(char)
                continue
            if current_width + char_width > width:
                out.append("".join(current))
                current = [char]
                current_width = char_width
            else:
                current.append(char)
                current_width += char_width
        out.append("".join(current))
        return out

    @classmethod
    def center(cls, s: str, width: int) -> str:
        """Pad *s* on both sides to *width* display columns."""
        space = width - cls.wlen(s)
        if space <= 0:
            return s
        left = space // 2
        return " " * left + s + " " * (space - left)

    @classmethod
    def load_lines(cls, text: str, width: int) -> list[str]:
        lines: list[str] = []
        for raw in text.splitlines():
            if cls.wlen(raw) <= width:
                lines.append(raw)
            else:
                lines.extend(cls.wrap_line(raw, width))
        return [cls.center(line, width) for line in lines]

    @staticmethod
    def scroll(text: str, duration: float = 60.0, fps: int = 30) -> None:
        """Scroll *text* upward over *duration* seconds."""
        if fps <= 0:
            raise ValueError("fps must be positive")
        if duration < 0:
            raise ValueError("duration must not be negative")
        delay = 1.0 / fps
        sys.stdout.write("\033[?25l\033[2J\033[H")
        sys.stdout.flush()

        try:
            width, height = shutil.get_terminal_size((80, 24))
            height = max(height - 1, 1)
            lines = MemberTable.load_lines(text, width)
            last_width = width

            total = height + len(lines)
            total_frames = max(int(duration * fps), 1)
            speed = total / total_frames
            offset = float(height)

            for _ in range(total_frames + 1):
                new_width, new_height = shutil.get_terminal_size((80, 24))
                new_height = max(new_height - 1, 1)
                if new_width != last_width:
                    lines = MemberTable.load_lines(text, new_width)
                    last_width = new_width
                width, height = new_width, new_height

                integer_offset = int(offset)
                buffer = ["\033[H"]
                for y in range(height):
                    index = y - integer_offset
                    if 0 <= index < len(lines):
                        buffer.append(lines[index])
                    if y != height - 1:
                        buffer.append("\033[K\n")
                    else:
                        buffer.append("\033[K")
                buffer.append("\033[J")
                sys.stdout.write("".join(buffer))
                sys.stdout.flush()

                time.sleep(delay)
                offset -= speed

        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?25h\033[2J\033[H")
            sys.stdout.flush()
