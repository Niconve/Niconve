"""
generate_stats.py
Fetches real GitHub data (including private repos) via GraphQL API
and writes stats.svg + activity.svg into the repo.
"""

import os
import json
import requests
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN    = os.environ["GH_TOKEN"]
USERNAME = os.environ.get("GH_USERNAME", "Niconve")
HEADERS  = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type":  "application/json",
}

# ── GraphQL query ─────────────────────────────────────────────────────────────
QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        name
        isPrivate
        stargazerCount
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    followers { totalCount }
    following  { totalCount }
  }
}
"""

def fetch():
    res = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={"query": QUERY, "variables": {"login": USERNAME}},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def lang_totals(repos):
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            n = edge["node"]["name"]
            totals[n] = totals.get(n, 0) + edge["size"]
    return dict(sorted(totals.items(), key=lambda x: -x[1]))

def streak(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort(key=lambda x: x[0])
    cur = longest = 0
    for _, c in reversed(days):
        if c > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            break
    lon = 0
    run = 0
    for _, c in days:
        if c > 0:
            run += 1
            lon = max(lon, run)
        else:
            run = 0
    return cur, lon

# ── SVG: stats.svg ────────────────────────────────────────────────────────────
STATS_TMPL = """\
<svg width="860" height="210" viewBox="0 0 860 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="860" y2="210" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0a0a0a"/>
      <stop offset="100%" stop-color="#0f0a0a"/>
    </linearGradient>
    <linearGradient id="barRed" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#e8290b"/>
      <stop offset="100%" stop-color="#c0200a"/>
    </linearGradient>
  </defs>

  <rect width="860" height="210" fill="url(#bg)" rx="4"/>
  <rect width="860" height="210" fill="none" stroke="#1a1a1a" stroke-width="1" rx="4"/>

  <!-- dividers -->
  <line x1="290" y1="16" x2="290" y2="194" stroke="#1a1a1a" stroke-width="1"/>
  <line x1="580" y1="16" x2="580" y2="194" stroke="#1a1a1a" stroke-width="1"/>

  <!-- ═══ BLOCK 1: Contributions ═══ -->
  <text x="28" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">CONTRIBUTIONS</text>
  <text x="28" y="96" font-family="Georgia,serif" font-size="62" fill="#f4f3ef" font-weight="700">{total_contrib}</text>
  <text x="28" y="116" font-family="'Courier New',monospace" font-size="8" fill="#555">Jan 2021 – today</text>
  {bar_chart}
  <text x="28" y="162" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">REPOS (incl. private)</text>
  <text x="210" y="162" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{total_repos}</text>
  <text x="28" y="178" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">COMMITS 2026</text>
  <text x="210" y="178" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{commits_2026}</text>
  <text x="28" y="194" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">FOLLOWERS</text>
  <text x="210" y="194" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".7" text-anchor="end">{followers}</text>

  <!-- ═══ BLOCK 2: Streak ═══ -->
  <text x="312" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">STREAK</text>
  <text x="312" y="96" font-family="Georgia,serif" font-size="62" fill="#e8290b" font-weight="700">{cur_streak}</text>
  <text x="398" y="84" font-family="'Courier New',monospace" font-size="10" fill="#e8290b" opacity=".6">days</text>
  <text x="312" y="116" font-family="'Courier New',monospace" font-size="8" fill="#555">current streak</text>
  <text x="312" y="152" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">LONGEST STREAK</text>
  <text x="555" y="152" font-family="Georgia,serif" font-size="22" fill="#f4f3ef" opacity=".5" text-anchor="end">{lon_streak} <tspan font-size="11" fill="#555">days</tspan></text>
  <text x="312" y="176" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">PULL REQUESTS</text>
  <text x="555" y="176" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".5" text-anchor="end">{pull_requests}</text>
  <text x="312" y="194" font-family="'Courier New',monospace" font-size="7.5" fill="#333" letter-spacing="1">ISSUES</text>
  <text x="555" y="194" font-family="Georgia,serif" font-size="13" fill="#f4f3ef" opacity=".5" text-anchor="end">{issues}</text>

  <!-- ═══ BLOCK 3: Languages ═══ -->
  <text x="604" y="36" font-family="'Courier New',monospace" font-size="8" fill="#444" letter-spacing="2.5">TOP LANGUAGES</text>
  {lang_bars}

  <!-- updated timestamp -->
  <text x="604" y="200" font-family="'Courier New',monospace" font-size="7" fill="#222" letter-spacing="1">updated: {updated}</text>

  <rect x="0" y="206" width="860" height="4" rx="2" fill="#e8290b" opacity=".6"/>
</svg>
"""

def make_bar_chart(weeks):
    """Mini bar chart from last 6 months of contribution data."""
    # flatten all days, take last 24 weeks
    days = []
    for w in weeks[-24:]:
        total = sum(d["contributionCount"] for d in w["contributionDays"])
        days.append(total)
    if not days:
        return ""
    max_v = max(days) or 1
    bars = []
    bar_w = 8
    gap   = 3
    x0    = 28
    y_base = 145
    max_h  = 20
    for i, v in enumerate(days):
        h = max(2, int(v / max_v * max_h))
        x = x0 + i * (bar_w + gap)
        op = 0.3 + 0.7 * (v / max_v)
        bars.append(
            f'<rect x="{x}" y="{y_base - h}" width="{bar_w}" height="{h}" '
            f'fill="#e8290b" opacity="{op:.2f}" rx="1"/>'
        )
    return "\n  ".join(bars)

def make_lang_bars(langs):
    total = sum(langs.values()) or 1
    items = list(langs.items())[:5]
    bars  = []
    y     = 55
    for name, size in items:
        pct   = size / total
        width = int(pct * 220)
        pct_s = f"{pct*100:.1f}%"
        bars.append(f"""\
  <text x="604" y="{y}" font-family="'Courier New',monospace" font-size="9" fill="#888">{name}</text>
  <rect x="604" y="{y+6}" width="220" height="5" rx="2" fill="#1a1a1a"/>
  <rect x="604" y="{y+6}" width="{width}" height="5" rx="2" fill="url(#barRed)" opacity=".85"/>
  <text x="828" y="{y+12}" font-family="'Courier New',monospace" font-size="8" fill="#555" text-anchor="end">{pct_s}</text>""")
        y += 32
    return "\n".join(bars)

def write_stats_svg(user):
    cc   = user["contributionsCollection"]
    cal  = cc["contributionCalendar"]
    weeks = cal["weeks"]
    cur_s, lon_s = streak(weeks)
    langs = lang_totals(user["repositories"]["nodes"])
    # commits in current year
    year = datetime.now(timezone.utc).year
    commits_yr = sum(
        d["contributionCount"]
        for w in weeks for d in w["contributionDays"]
        if d["date"].startswith(str(year))
    )

    svg = STATS_TMPL.format(
        total_contrib = cal["totalContributions"],
        total_repos   = user["repositories"]["totalCount"],
        commits_2026  = commits_yr,
        followers     = user["followers"]["totalCount"],
        cur_streak    = cur_s,
        lon_streak    = lon_s,
        pull_requests = cc["totalPullRequestContributions"],
        issues        = cc["totalIssueContributions"],
        bar_chart     = make_bar_chart(weeks),
        lang_bars     = make_lang_bars(langs),
        updated       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    with open("stats.svg", "w") as f:
        f.write(svg)
    print("✓ stats.svg written")

# ── SVG: activity.svg ─────────────────────────────────────────────────────────
def write_activity_svg(user):
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]

    # collect last 52 weeks of weekly totals + month labels
    weekly = []
    month_labels = []
    last_month = None
    for i, w in enumerate(weeks[-52:]):
        total = sum(d["contributionCount"] for d in w["contributionDays"])
        weekly.append(total)
        first_day = w["contributionDays"][0]["date"] if w["contributionDays"] else ""
        if first_day:
            m = datetime.strptime(first_day, "%Y-%m-%d").strftime("%b")
            if m != last_month:
                month_labels.append((i, m))
                last_month = m

    max_v  = max(weekly) if weekly else 1
    W      = 796
    H      = 80
    x0, y0 = 32, 50
    n      = len(weekly)
    step   = W / max(n - 1, 1)

    # polyline points
    pts_line = " ".join(
        f"{x0 + i*step:.1f},{y0 + H - (v / max_v * H):.1f}"
        for i, v in enumerate(weekly)
    )
    # area polygon
    pts_area = (
        f"{x0:.1f},{y0+H} " +
        " ".join(f"{x0 + i*step:.1f},{y0 + H - (v / max_v * H):.1f}" for i, v in enumerate(weekly)) +
        f" {x0 + (n-1)*step:.1f},{y0+H}"
    )

    # month label SVG elements
    month_svg = ""
    for idx, label in month_labels:
        mx = x0 + idx * step
        month_svg += (
            f'<text x="{mx:.1f}" y="44" font-family="\'Courier New\',monospace" '
            f'font-size="7" fill="#333">{label}</text>\n  '
        )

    # peak marker
    peak_i = weekly.index(max_v) if max_v > 0 else 0
    peak_x = x0 + peak_i * step
    peak_y = y0 + H - H  # = y0

    svg = f"""\
<svg width="860" height="160" viewBox="0 0 860 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="860" y2="160" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0a0a0a"/>
      <stop offset="100%" stop-color="#0f0a0a"/>
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

  <!-- grid -->
  <line x1="32" y1="{y0}" x2="828" y2="{y0}" stroke="#111" stroke-width=".5"/>
  <line x1="32" y1="{y0+H//2}" x2="828" y2="{y0+H//2}" stroke="#111" stroke-width=".5"/>
  <line x1="32" y1="{y0+H}" x2="828" y2="{y0+H}" stroke="#111" stroke-width=".5"/>

  <!-- month labels -->
  {month_svg}

  <!-- area fill -->
  <polygon points="{pts_area}" fill="url(#area)"/>

  <!-- line -->
  <polyline points="{pts_line}" fill="none" stroke="#e8290b" stroke-width="1.5" stroke-linejoin="round"/>

  <!-- peak -->
  <circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="4" fill="#e8290b"/>
  <circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="9" fill="#e8290b" opacity=".18"/>
  <text x="{peak_x+12:.1f}" y="{peak_y+4:.1f}" font-family="'Courier New',monospace" font-size="7" fill="#e8290b">peak: {max_v}</text>

  <!-- y-axis -->
  <text x="20" y="{y0+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">{max_v}</text>
  <text x="20" y="{y0+H//2+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">{max_v//2}</text>
  <text x="20" y="{y0+H+4}" font-family="'Courier New',monospace" font-size="6.5" fill="#333" text-anchor="end">0</text>

  <rect x="0" y="156" width="860" height="4" rx="2" fill="#e8290b" opacity=".6"/>
</svg>"""

    with open("activity.svg", "w") as f:
        f.write(svg)
    print("✓ activity.svg written")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Fetching data for @{USERNAME}...")
    user = fetch()
    write_stats_svg(user)
    write_activity_svg(user)
    print("All done!")
