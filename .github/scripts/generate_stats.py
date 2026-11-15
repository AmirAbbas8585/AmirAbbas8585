import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "AmirAbbas8585")

LANG_COLORS = {
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "Shell": "#89e051",
    "Kotlin": "#A97BFF",
}


def gh_graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def build_stats_svg(stars, repos, commits, prs, issues, total_contribs, days_30):
    max_c = max((d["contributionCount"] for d in days_30), default=1) or 1
    bars = []
    bar_w = 10
    gap = 4
    chart_x = 30
    chart_y = 148
    chart_h = 46
    for i, d in enumerate(days_30):
        cnt = d["contributionCount"]
        h = max(3, int((cnt / max_c) * chart_h)) if cnt > 0 else 2
        x = chart_x + i * (bar_w + gap)
        y = chart_y + (chart_h - h)
        fill = "#1bd96a" if cnt > 0 else "#21262d"
        opacity = "1" if cnt > 0 else "0.6"
        bars.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="2" fill="{fill}" opacity="{opacity}"/>')

    return f'''<svg width="470" height="215" viewBox="0 0 470 215" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="469" height="214" rx="12" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="34" fill="#1bd96a" font-family="Segoe UI, Ubuntu, sans-serif" font-size="16" font-weight="700">{USER}'s GitHub Stats</text>
  <text x="24" y="64" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">★ Total Stars: <tspan fill="#ffffff" font-weight="600">{stars}</tspan></text>
  <text x="245" y="64" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">📦 Repositories: <tspan fill="#ffffff" font-weight="600">{repos}</tspan></text>
  <text x="24" y="90" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">⚡ Commits (1y): <tspan fill="#ffffff" font-weight="600">{commits}</tspan></text>
  <text x="245" y="90" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">🔀 PRs / Issues: <tspan fill="#ffffff" font-weight="600">{prs} / {issues}</tspan></text>
  <line x1="24" y1="110" x2="446" y2="110" stroke="#21262d"/>
  <text x="24" y="132" fill="#8b949e" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12">Last 30 Days Activity ({total_contribs} contributions this year)</text>
  {"".join(bars)}
</svg>'''


def build_langs_svg(lang_totals):
    total_bytes = sum(v["size"] for v in lang_totals.values()) or 1
    top = sorted(lang_totals.items(), key=lambda kv: kv[1]["size"], reverse=True)[:6]

    bar_x = 24
    bar_y = 52
    bar_total_w = 422
    segments = []
    cur_x = bar_x
    for idx, (name, info) in enumerate(top):
        w = (info["size"] / total_bytes) * bar_total_w
        if idx == len(top) - 1:
            w = (bar_x + bar_total_w) - cur_x
        color = info["color"] or LANG_COLORS.get(name, "#1bd96a")
        segments.append(f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{max(2, w):.1f}" height="10" fill="{color}"/>')
        cur_x += w

    items = []
    for i, (name, info) in enumerate(top):
        col = i % 2
        row = i // 2
        x = 24 + col * 215
        y = 92 + row * 34
        pct = (info["size"] / total_bytes) * 100
        color = info["color"] or LANG_COLORS.get(name, "#1bd96a")
        items.append(
            f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>'
            f'<text x="{x + 16}" y="{y}" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">{name} <tspan fill="#8b949e">{pct:.1f}%</tspan></text>'
        )

    return f'''<svg width="470" height="215" viewBox="0 0 470 215" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="469" height="214" rx="12" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="34" fill="#1bd96a" font-family="Segoe UI, Ubuntu, sans-serif" font-size="16" font-weight="700">Most Used Languages</text>
  <clipPath id="bar-clip"><rect x="{bar_x}" y="{bar_y}" width="{bar_total_w}" height="10" rx="5"/></clipPath>
  <g clip-path="url(#bar-clip)">{"".join(segments)}</g>
  {"".join(items)}
</svg>'''


def main():
    res = gh_graphql(QUERY, {"login": USER})
    u = res["data"]["user"]
    repos_node = u["repositories"]
    repos = repos_node["totalCount"]
    stars = sum(r["stargazerCount"] for r in repos_node["nodes"])

    lang_totals = {}
    for r in repos_node["nodes"]:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"]
            if name not in lang_totals:
                lang_totals[name] = {"size": 0, "color": color}
            lang_totals[name]["size"] += edge["size"]

    cc = u["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    cal = cc["contributionCalendar"]
    total_contribs = cal["totalContributions"]
    all_days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days_30 = all_days[-30:]

    os.makedirs("dist", exist_ok=True)
    with open("dist/stats.svg", "w", encoding="utf-8") as f:
        f.write(build_stats_svg(stars, repos, commits, prs, issues, total_contribs, days_30))
    with open("dist/langs.svg", "w", encoding="utf-8") as f:
        f.write(build_langs_svg(lang_totals))


if __name__ == "__main__":
    main()
