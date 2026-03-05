"""
generate_stats.py — NICONVE™
Fetches real GitHub data (including private repos) and writes stats.svg + activity.svg
"""

import os, requests
from datetime import datetime, timezone

TOKEN    = os.environ["GH_TOKEN"]
USERNAME = os.environ.get("GH_USERNAME", "Niconve")
HEADERS  = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        isPrivate
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount date }
        }
      }
    }
  }
}
"""

def fetch():
    r = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={"query": QUERY, "variables": {"login": USERNAME}},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]["user"]

def lang_totals(repos):
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            n = edge["node"]["name"]
            totals[n] = totals.get(n, 0) + edge["size"]
    return dict(sorted(totals.items(), key=lambda x: -x[1]))

def calc_streak(weeks):
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda x: x[0])
    # current streak
    cur = 0
    for _, c in reversed(days):
        if c > 0: cur += 1
        else: break
    # longest streak
    lon = run = 0
    for _, c in days:
        if c > 0:
            run += 1
            lon = max(lon, run)
        else:
            run = 0
    return cur, lon

def mini_bars(weeks):
    buckets = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks[-24:]]
    if not buckets: return ""
    mx = max(buckets) or 1
    bars = []
    for i, v in enumerate(buckets):
        h  = max(2, int(v / mx * 20))
        x  = 28 + i * 11
        op = round(0.25 + 0.75 * (v / mx), 2)
        bars.append(f'<rect x="{x}" y="{145-h}" width="8" height="{h}" fill="#e8290b" opacity="{op}" rx="1"/>')
    return "\n  ".join(bars)

def lang_bars(langs):
    total = sum(langs.values()) or 1
    items = list(langs.items())[:5]
    out, y = [], 55
    for name, size in items:
        pct = size / total
        w   = int(pct * 220)
        out.append(f"""  <text x="604" y="{y}" font-family="'Courier New',monospace" font-size="9" fill="#888">{name}</text>
  <rect x="604" y="{y+6}" width="220" height="5" rx="2" fill="#1a1a1a"/>
  <rect x="604" y="{y+6}" width="{w}" height="5" rx="2" fill="#e8290b" opacity=".85"/>
  <text x="828" y="{y+12}" font-family="'Courier New',monospace" font-size="8" fill="#555" text-anchor="end">{pct*100:.1f}%</text>""")
        y += 32
    return "\n".join(out)

def write_stats(user):
    cc    = user["contributionsCollection"]
    weeks = cc["contributionCalendar"]["weeks"]
    cur_s, lon_s = calc_streak(weeks)
    langs = lang_totals(user["repositories"]["nodes"])
    year  = datetime.now(timezone.utc).year
    commits_yr = sum(
        d["contributionCount"] for w in weeks
        for d in w["contributionDays"] if d["date"].startswith(str(year))
    )

    svg = f"""<svg width="860" height="210" viewBox="0 0 860 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="860" y2="210" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0a0a0a"/><stop offset="100%" stop-color="#0f0a0a"/>
    </linearGradient>
  </defs>
  <rect width="860" height="210" fill="url(#bg)" rx="4"/>
  <rect width="860" height="210" fill="none" stroke="#1a1a1a" stroke-width="1" rx="4"/>
  <line x1="290" y1="16" x2="290" y2="194" stroke="#1a1a1a" stroke-width="1"/>
  <line x1="580" y1="16" x2="580" y2="194" stroke="#1a1a1a" stroke-width="1"/>

  <!-- BLOCK 1: Contributions -->
  <text x="28" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">CONTRIBUTIONS</text>
  <text x="28" y="96" font-family="Georgia,serif" font-size="62" fill="#f4f3ef" font-weight="700">{cc["contributionCalendar"]["totalContributions"]}</text>
  <text x="28" y="116" font-family="'Courier New',monospace" font-size="8" fill="#555">all time · incl. private</text>
  {mini_bars(weeks)}
  <text x="28" y="168" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">REPOS (incl. private)</text>
  <text x="262" y="168" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{user["repositories"]["totalCount"]}</text>
  <text x="28" y="184" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">COMMITS {year}</text>
  <text x="262" y="184" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{commits_yr}</text>
  <text x="28" y="200" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">FOLLOWERS</text>
  <text x="262" y="200" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{user["followers"]["totalCount"]}</text>

  <!-- BLOCK 2: Streak -->
  <text x="312" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">STREAK</text>
  <text x="312" y="96" font-family="Georgia,serif" font-size="62" fill="#e8290b" font-weight="700">{cur_s}</text>
  <text x="400" y="84" font-family="'Courier New',monospace" font-size="10" fill="#e8290b" opacity=".6">days</text>
  <text x="312" y="116" font-family="'Courier New',monospace" font-size="8" fill="#555">current streak</text>
  <text x="312" y="152" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">LONGEST STREAK</text>
  <text x="560" y="152" font-family="Georgia,serif" font-size="18" fill="#f4f3ef" opacity=".5" text-anchor="end">{lon_s} <tspan font-size="10" fill="#555">days</tspan></text>
  <text x="312" y="174" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">PULL REQUESTS</text>
  <text x="560" y="174" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".5" text-anchor="end">{cc["totalPullRequestContributions"]}</text>
  <text x="312" y="194" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">ISSUES</text>
  <text x="560" y="194" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".5" text-anchor="end">{cc["totalIssueContributions"]}</text>

  <!-- BLOCK 3: Languages -->
  <text x="604" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">TOP LANGUAGES</text>
  {lang_bars(langs)}

  <text x="604" y="202" font-family="'Courier New',monospace" font-size="7" fill="#222" letter-spacing="1">updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
  <rect x="0" y="206" width="860" height="4" rx="2" fill="#e8290b" opacity=".6"/>
</svg>"""

    with open("stats.svg", "w") as f:
        f.write(svg)
    print("✓ stats.svg written")

def write_activity(user):
    weeks  = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks[-52:]]
    mx     = max(weekly) if weekly else 1
    W, H   = 796, 80
    x0, y0 = 32, 50
    n      = len(weekly)
    step   = W / max(n - 1, 1)

    pts_line = " ".join(f"{x0+i*step:.1f},{y0+H-(v/mx*H):.1f}" for i, v in enumerate(weekly))
    pts_area = f"{x0:.1f},{y0+H} " + pts_line + f" {x0+(n-1)*step:.1f},{y0+H}"

    peak_i = weekly.index(max(weekly)) if weekly else 0
    peak_x = x0 + peak_i * step
    peak_y = y0 + H - (weekly[peak_i] / mx * H)

    # month labels
    months, last = [], None
    for i, w in enumerate(weeks[-52:]):
        if w["contributionDays"]:
            m = datetime.strptime(w["contributionDays"][0]["date"], "%Y-%m-%d").strftime("%b")
            if m != last:
                months.append((i, m))
                last = m
    month_svg = "".join(
        f'<text x="{x0+i*step:.1f}" y="44" font-family="\'Courier New\',monospace" font-size="7" fill="#333">{m}</text>\n  '
        for i, m in months
    )

    svg = f"""<svg width="860" height="160" viewBox="0 0 860 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="860" y2="160" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0a0a0a"/><stop offset="100%" stop-color="#0f0a0a"/>
    </linearGradient>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e8290b" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#e8290b" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="860" height="160" fill="url(#bg)" rx="4"/>
  <rect width="860" height="160" fill="none" stroke="#1a1a1a" stroke-width="1" rx="4"/>
  <text x="32" y="22" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">CONTRIBUTION ACTIVITY · LAST 52 WEEKS</text>
  <rect x="32" y="28" width="796" height="1" fill="#1a1a1a"/>
  <line x1="32" y1="{y0}" x2="828" y2="{y0}" stroke="#111" stroke-width=".5"/>
  <line x1="32" y1="{y0+H//2}" x2="828" y2="{y0+H//2}" stroke="#111" stroke-width=".5"/>
  <line x1="32" y1="{y0+H}" x2="828" y2="{y0+H}" stroke="#111" stroke-width=".5"/>
  {month_svg}
  <polygon points="{pts_area}" fill="url(#area)"/>
  <polyline points="{pts_line}" fill="none" stroke="#e8290b" stroke-width="1.5" stroke-linejoin="round"/>
  <circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="4" fill="#e8290b"/>
  <circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="9" fill="#e8290b" opacity=".18"/>
  <text x="{peak_x+12:.1f}" y="{peak_y+4:.1f}" font-family="'Courier New',monospace" font-size="7" fill="#e8290b">peak: {mx}</text>
  <text x="20" y="{y0+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">{mx}</text>
  <text x="20" y="{y0+H//2+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">{mx//2}</text>
  <text x="20" y="{y0+H+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">0</text>
  <rect x="0" y="156" width="860" height="4" rx="2" fill="#e8290b" opacity=".6"/>
</svg>"""

    with open("activity.svg", "w") as f:
        f.write(svg)
    print("✓ activity.svg written")

if __name__ == "__main__":
    print(f"Fetching data for @{USERNAME}...")
    user = fetch()
    write_stats(user)
    write_activity(user)
    print("All done!")
