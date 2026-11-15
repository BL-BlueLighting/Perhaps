"""
doas -su mylife.root
演出人员表

写这玩意花了我很长时间。
do not copy~
"""

import sys
import time
import shutil
import unicodedata

class MemberTable:
    def wlen(self, s: str) -> int:
        return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)


    def wrap_line(self, s: str, width: int):
        if not s:
            return ['']
        out, cur, cur_w = [], '', 0
        for ch in s:
            cw = 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
            if cur_w + cw > width:
                out.append(cur)
                cur, cur_w = ch, cw
            else:
                cur += ch
                cur_w += cw
        out.append(cur)
        return out


    def center(self, s: str, width: int) -> str:
        space = width - self.wlen(s)
        return (' ' * (space // 2) + s) if space > 0 else s


    def load_lines(self, text: str, width: int):
        lines = []
        for raw in text.splitlines():
            if self.wlen(raw) <= width:
                lines.append(raw)
            else:
                lines.extend(self.wrap_line(raw, width))
        return [self.center(s, width) for s in lines]


    def scroll(self, text: str, duration: float = 60.0, fps: int = 30):
        delay = 1.0 / fps
        sys.stdout.write('\033[?25l\033[2J\033[H')
        sys.stdout.flush()

        try:
            W, H = shutil.get_terminal_size((80, 24))
            H = max(H - 1, 1)
            lines = self.load_lines(text, W)
            last_W = W

            total = H + len(lines)
            total_frames = max(int(duration * fps), 1)
            speed = total / total_frames
            offset = float(H)

            for _ in range(total_frames + 1):
                nW, nH = shutil.get_terminal_size((80, 24))
                nH = max(nH - 1, 1)
                if nW != last_W:
                    lines = self.load_lines(text, nW)
                    last_W = nW
                W, H = nW, nH

                oi = int(offset)
                buf = ['\033[H']
                for y in range(H):
                    idx = y - oi
                    if 0 <= idx < len(lines):
                        buf.append(lines[idx])
                    if y != H - 1:
                        buf.append('\033[K\n')
                    else:
                        buf.append('\033[K')
                buf.append('\033[J')
                sys.stdout.write(''.join(buf))
                sys.stdout.flush()

                time.sleep(delay)
                offset -= speed

        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write('\033[?25h\033[2J\033[H')
            sys.stdout.flush()