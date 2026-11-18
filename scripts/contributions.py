"""Draw Paul's contribution trail from GitHub's public, signed-out calendar."""

import sys
from collections import defaultdict
from datetime import date, timedelta
from html.parser import HTMLParser
from http.client import HTTPException
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen


SOURCE = "https://github.com/users/paul-tian/contributions"
ASSETS = Path(__file__).resolve().parents[1] / "assets"
THEMES = {
    "light": ("#f8f6ef", "#d2d8cf", "#182731", "#4f6863", "#ce893a",
              ("#e0e5dc", "#9dcebc", "#60b29a", "#328c78", "#126658")),
    "dark": ("#111c26", "#36484f", "#f5f0e5", "#a2b8b4", "#f0b76d",
             ("#273944", "#345d56", "#398374", "#66b59c", "#9ae2c6")),
}
LEFT, TOP, PITCH, SIZE = 63, 77, 14, 10
SPEED, HEAD_START = 49, 1.15


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        cell = dict(attrs)
        if tag != "td" or "data-date" not in cell:
            return
        day = date.fromisoformat(cell["data-date"])
        level = int(cell.get("data-level", "-1"))
        if day in self.days or level not in range(5):
            raise ValueError("unexpected calendar cell")
        self.days[day] = level


def fetch_days():
    request = Request(SOURCE, headers={"User-Agent": "paul-tian-profile", "Accept": "text/html"})
    parser = CalendarParser()
    with urlopen(request, timeout=20) as response:
        parser.feed(response.read().decode("utf-8"))
    parser.close()
    days = dict(sorted(parser.days.items()))
    if not 364 <= len(days) <= 371 or (max(days) - min(days)).days + 1 != len(days):
        raise ValueError("incomplete public calendar")
    return days


def text(x, y, value, extra=""):
    return f'<text x="{x}" y="{y}" {extra}>{value}</text>'


def render(days, theme):
    paper, edge, ink, muted, amber, levels = THEMES[theme]
    first, last = min(days), max(days)
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    rows = defaultdict(list)
    active, months = [], []
    for day, level in days.items():
        week, weekday = divmod((day - sunday).days, 7)
        center = (LEFT + week * PITCH, TOP + weekday * PITCH)
        rows[center[1]].append(center[0])
        if level:
            active.append((day, level, center))
        if day.day == 1 or day == first:
            months.append((center[0], day.strftime("%b")))
    if len(months) > 1 and months[1][0] - months[0][0] < 2 * PITCH:
        months.pop(0)

    right = max(max(row) for row in rows.values())
    first_y, last_y = (active[0][2][1], active[-1][2][1]) if active else (TOP, TOP)
    route = [(LEFT - 42, first_y), *(center for _, _, center in active), (right + 42, last_y)]
    times = [0.0]
    for start, end in zip(route, route[1:]):
        times.append(times[-1] + dist(start, end) / SPEED)
    duration = times[-1]
    path = "M" + " L".join(f"{x} {y}" for x, y in route)
    date_range = f"{first:%b} {first.day}, {first.year} – {last:%b} {last.day}, {last.year}"
    count_label = f"{len(active)} active {'day' if len(active) == 1 else 'days'}"
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="840" height="204" viewBox="0 0 840 204" role="img" aria-labelledby="title desc">
<title id="title">Paul's contribution trail</title>
<desc id="desc">GitHub's public calendar from {first} to {last}, with {count_label}. An amber snake follows the active dates. Darker teal on paper and brighter teal in dark mode indicate more activity.</desc>
<defs>
  <pattern id="grid" patternUnits="userSpaceOnUse" x="{LEFT - SIZE // 2}" y="{TOP - SIZE // 2}" width="{PITCH}" height="{PITCH}"><rect width="{SIZE}" height="{SIZE}" rx="2.5" fill="{levels[0]}"/></pattern>
  <clipPath id="plot"><rect x="{LEFT - 7}" y="{TOP - 7}" width="{right - LEFT + 14}" height="{6 * PITCH + 14}"/></clipPath>
  <path id="route" d="{path}"/>
</defs>
<style>
  text {{ fill:{muted}; font:11px 'IBM Plex Mono',Menlo,Consolas,monospace; }}
  .heading {{ fill:{ink}; font:600 22px 'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .motion {{ display:none; }}
  @keyframes nibble {{ 0%,9%,100% {{ opacity:1; }} 1%,4% {{ opacity:0; }} }}
  @media (prefers-reduced-motion:no-preference) {{
    .motion {{ display:inline; }}
    .food {{ animation:nibble {duration:.3f}s linear infinite; }}
  }}
</style>
<rect x=".5" y=".5" width="839" height="203" rx="12" fill="{paper}" stroke="{edge}"/>
<g transform="translate(27 27)" fill="{amber}"><path d="M0 6h4q4 0 4-5t5-5h4q4 0 4 4t4 4h3" fill="none" stroke="{amber}" stroke-width="4" stroke-linecap="round"/><ellipse cx="29" cy="4" rx="4" ry="3.2"/><circle cx="30" cy="3" r=".8" fill="#182731"/></g>''',
             text(69, 36, "Contribution trail", 'class="heading"'),
             text(812, 34, count_label, 'text-anchor="end"'),
             *(text(x - SIZE // 2, 61, name) for x, name in months)]

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(text(48, TOP + weekday * PITCH + 4, label, 'text-anchor="end"'))
    for y, row in sorted(rows.items()):
        parts.append(f'<rect x="{min(row) - SIZE // 2}" y="{y - SIZE // 2}" width="{max(row) - min(row) + SIZE}" height="{SIZE}" fill="url(#grid)"/>')
    for (day, level, (x, y)), arrival in zip(active, times[1:]):
        delay = -((HEAD_START - arrival) % duration)
        parts.append(f'<rect class="food" x="{x - SIZE // 2}" y="{y - SIZE // 2}" width="{SIZE}" height="{SIZE}" rx="2.5" fill="{levels[level]}" style="animation-delay:{delay:.3f}s"><title>{day}: activity level {level} of 4</title></rect>')

    if active:
        parts.append(f'<g class="motion" clip-path="url(#plot)" fill="{amber}">')
        body = ['<path d="M-5-2.7Q-1-5.4 4-3.5Q8-2.4 8 0T4 3.5Q-1 5.4-5 2.7Z"/><path d="M7 0h3l2-1.6m-2 1.6 2 1.6" fill="none" stroke="currentColor" stroke-width="1.2"/><g fill="#182731"><circle cx="3.2" cy="-2" r="1"/><circle cx="3.2" cy="2" r="1"/></g>']
        body.extend(f'<circle r="{radius}"/>' for radius in (4.1, 4, 3.8, 3.5, 3.1, 2.6, 1.9))
        for index in reversed(range(len(body))):
            begin = index * 4 / SPEED - HEAD_START
            parts.append(f'<g color="{amber}">{body[index]}<animateMotion dur="{duration:.3f}s" begin="{begin:.3f}s" rotate="auto" repeatCount="indefinite"><mpath xlink:href="#route"/></animateMotion></g>')
        parts.append('</g>')

    parts.extend([text(27, 189, date_range), text(665, 189, "Less")])
    for index, color in enumerate(levels):
        parts.append(f'<rect x="{700 + index * 14}" y="180" width="10" height="10" rx="2.5" fill="{color}"/>')
    parts.extend([text(812, 189, "More", 'text-anchor="end"'), '</svg>'])
    return "\n".join(parts) + "\n"


def main():
    targets = {theme: ASSETS / f"contributions-{theme}.svg" for theme in THEMES}
    try:
        days = fetch_days()
    except (OSError, HTTPException, ValueError) as error:
        cached = all(target.is_file() for target in targets.values())
        print(f"Public calendar unavailable ({error}); {'keeping existing SVGs' if cached else 'no complete cache'}.", file=sys.stderr)
        return 0 if cached else 1
    ASSETS.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ASSETS) as staging:
        for theme, target in targets.items():
            output = Path(staging) / target.name
            output.write_text(render(days, theme), encoding="utf-8")
        for target in targets.values():
            output = Path(staging) / target.name
            if not target.exists() or output.read_bytes() != target.read_bytes():
                output.replace(target)
    print(f"Public calendar: {min(days)} to {max(days)}, {sum(level > 0 for level in days.values())} active days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
