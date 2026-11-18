import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


OWNER = "paul-tian"
ASSETS = Path(__file__).resolve().parents[1] / "assets"


@dataclass(frozen=True)
class Palette:
    paper: str
    ink: str
    muted: str
    rule: str
    teal: str
    amber: str


THEMES = {
    "light": Palette("#f8f6ef", "#111c26", "#465963", "#cbd3ce", "#28786e", "#a3651a"),
    "dark": Palette("#111c26", "#f8f6ef", "#adbec3", "#344953", "#72c8b7", "#edb567"),
}


def fetch_projects():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{OWNER}-public-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]

    projects = {}
    page = 1
    while True:
        url = f"https://api.github.com/users/{OWNER}/repos?type=owner&sort=full_name&direction=asc&per_page=100&page={page}"
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            repositories = json.load(response)
        for repository in repositories:
            if (
                repository["visibility"] == "public"
                and not repository["private"]
                and not repository["fork"]
                and repository["owner"]["login"].casefold() == OWNER
                and repository["name"].casefold() != OWNER
            ):
                projects[repository["id"]] = repository
        if len(repositories) < 100:
            return projects.values()
        page += 1


def year_chart(creations, colors):
    if not creations:
        return f'<text x="344" y="102" fill="{colors.muted}" font-size="16">No repository history yet.</text>'

    last_year = max(creations)
    first_year = max(min(creations), last_year - 8)
    years = range(first_year, last_year + 1)
    peak = max(creations[year] for year in years)
    slot = 440 / len(years)
    baseline = 137
    lines = [f'<path d="M344 {baseline}h440" stroke="{colors.rule}"/>']
    for index, year in enumerate(years):
        center = 344 + slot * (index + 0.5)
        count = creations[year]
        if count:
            height = 58 * count / peak
            top = baseline - height
            fill = colors.amber if year == last_year else colors.teal
            lines.append(f'<rect x="{center - 10:.1f}" y="{top:.1f}" width="20" height="{height:.1f}" rx="2" fill="{fill}"/>')
            lines.append(f'<text x="{center:.1f}" y="{top - 7:.1f}" fill="{colors.ink}" font-size="13">{count:,}</text>')
        else:
            lines.append(f'<path d="M{center - 4:.1f} {baseline}h8" stroke="{colors.muted}" stroke-width="2"/>')
        lines.append(f'<text x="{center:.1f}" y="160" fill="{colors.muted}" font-size="13">{year}</text>')
    return '<g text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Consolas, monospace">\n    ' + '\n    '.join(lines) + '\n  </g>'


def activity_card(projects, colors):
    total = len(projects)
    stars = sum(project["stargazers_count"] for project in projects)
    languages = len({project["language"] for project in projects if project["language"]})
    creations = Counter(int(project["created_at"][:4]) for project in projects)
    history = ", ".join(f"{year}: {creations[year]}" for year in sorted(creations))
    star_label = "star" if stars == 1 else "stars"
    language_label = "primary language" if languages == 1 else "primary languages"
    history_description = f" Repositories created by year: {history}." if history else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="816" height="184" viewBox="0 0 816 184" role="img" aria-labelledby="title description">
  <title id="title">Public repository activity for {OWNER}</title>
  <desc id="description">{total:,} public repositories excluding forks and this profile, {stars:,} {star_label}, {languages} distinct GitHub primary languages.{history_description}</desc>
  <rect x="0.5" y="0.5" width="815" height="183" rx="12" fill="{colors.paper}" stroke="{colors.rule}"/>
  <g font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif" fill="{colors.ink}">
    <text x="28" y="42" font-size="19" font-weight="600">Public repositories</text>
    <text x="26" y="122" font-family="Georgia, 'Times New Roman', serif" font-size="86">{total:,}</text>
    <path d="m35 145.5 2.1 4.3 4.8.7-3.5 3.4.8 4.8-4.2-2.3-4.3 2.3.8-4.8-3.4-3.4 4.8-.7z" fill="none" stroke="{colors.amber}" stroke-width="1.6" stroke-linejoin="round"/>
    <text x="49" y="158" font-size="16" fill="{colors.muted}">{stars:,} {star_label} · {languages} {language_label}</text>
    <path d="M316 27v130" stroke="{colors.rule}"/>
    <text x="344" y="42" font-size="19" font-weight="600">Repositories created by year</text>
    {year_chart(creations, colors)}
  </g>
</svg>
'''


def main():
    projects = fetch_projects()
    ASSETS.mkdir(exist_ok=True)
    for name, colors in THEMES.items():
        destination = ASSETS / f"activity-{name}.svg"
        card = activity_card(projects, colors)
        if not destination.exists() or destination.read_text(encoding="utf-8") != card:
            destination.write_text(card, encoding="utf-8")


if __name__ == "__main__":
    main()
