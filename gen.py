"""Draws dist/terminal.svg and dist/pacman.svg for the GitHub profile README.

Runs nightly in .github/workflows/profile.yml. Needs GITHUB_TOKEN for the
contribution calendar (GraphQL). Stdlib only. The SVGs animate with CSS
keyframes because GitHub shows README images without running scripts.
"""
import base64
import datetime
import json
import os
import random
import urllib.request
from html import escape
from pathlib import Path

USER = "Mascotte33"
OUT_DIR = "dist"
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@14.0.0/icons/"
BACKGROUND, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
GREEN, BLUE, GREY, YELLOW, TEXT = "#3fb950", "#58a6ff", "#8b949e", "#d29922", "#c9d1d9"

# Hand-written stack per repo; new repos fall back to their main language.
REPO_STACKS = {
    "multi-url-monitor": "K8s, Terraform, AWS",
    "System-Resource-Monitor": "Prometheus, Grafana",
    "cron-data-puller": "cron, APIs",
    "Moonlight": "Python, OpenCV, Claude Code",
    "Gierka": "k3s, Argo CD (Azure DevOps)",
}
# The multiplayer game lives in Azure DevOps; its commits join the contribution graph.
AZURE_DEVOPS_ORG = "https://dev.azure.com/michalkogut810"
AZURE_GAME_REPO = "Gierka"
AZURE_AUTHOR_EMAIL = "kamil.kolmasiak@gmail.com"


def fetch(url: str, body: dict | None = None) -> bytes:
    headers = {"User-Agent": USER}
    if url.startswith("https://api.github.com"):
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set")
        headers["Authorization"] = f"bearer {token}"
    if url.startswith(AZURE_DEVOPS_ORG):
        token = os.environ.get("AZURE_DEVOPS_TOKEN")
        if not token:
            raise SystemExit("AZURE_DEVOPS_TOKEN is not set (a PAT with Code: Read)")
        # A PAT goes in Basic auth; an `az account get-access-token` JWT (starts eyJ) is a Bearer.
        headers["Authorization"] = (f"Bearer {token}" if token.startswith("eyJ")
                                    else "Basic " + base64.b64encode(f":{token}".encode()).decode())
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_json(url: str, body: dict | None = None):
    return json.loads(fetch(url, body))


def azure_devops_commits_per_day(from_date: str) -> dict[str, int]:
    """My commits per day (YYYY-MM-DD) on the default branch of every repo in the Azure DevOps org."""
    page_size = 5000
    per_day: dict[str, int] = {}
    for repo in fetch_json(f"{AZURE_DEVOPS_ORG}/_apis/git/repositories?api-version=7.1")["value"]:
        commits = fetch_json(f"{AZURE_DEVOPS_ORG}/_apis/git/repositories/{repo['id']}/commits"
                             f"?searchCriteria.fromDate={from_date}&searchCriteria.$top={page_size}"
                             "&api-version=7.1")["value"]
        if len(commits) == page_size:
            raise SystemExit(f"{repo['name']}: {page_size}+ commits in a year, add paging")
        for commit in commits:
            if commit["author"]["email"].lower() == AZURE_AUTHOR_EMAIL:
                day = commit["author"]["date"][:10]
                per_day[day] = per_day.get(day, 0) + 1
    return per_day


def keyframes(name: str, frames: list[tuple[float, str]], total_seconds: float) -> str:
    """CSS @keyframes from (seconds, declarations); a later frame at the same time wins."""
    by_percent: dict[str, str] = {}
    for seconds, declarations in sorted(frames, key=lambda frame: frame[0]):
        by_percent[f"{seconds / total_seconds * 100:.4f}%"] = declarations
    return f"@keyframes {name}{{" + "".join(f"{pct}{{{d}}}" for pct, d in by_percent.items()) + "}"


# ---------------------------------------------------------------- terminal

PROMPT = [("kamil@devops", GREEN), (":~$ ", GREY)]
CHAR_WIDTH, LINE_HEIGHT, FONT_SIZE = 7.8, 19, 13
TYPE_SECONDS_PER_CHAR, READ_SECONDS = 0.045, 5.5


def terminal_scenes(repos: list[dict]) -> list[tuple[str, list[list[tuple[str, str]]]]]:
    repo_lines = [[(f"{'NAME':<25}STACK", GREY)]]
    for repo in repos[:6]:
        stack = REPO_STACKS.get(repo["name"], repo.get("language") or "")
        repo_lines.append([(f"{repo['name']:<25}", BLUE), (stack, TEXT)])
    return [
        ("gh repo list --public", repo_lines),
        ("kubectl describe pod kamil | grep -E 'Role|Location|Experience'", [
            [("Role:        ", TEXT), ("DevOps / Cloud Engineer", YELLOW)],
            [("Location:    Kraków, Poland", TEXT)],
            [("Experience:  8 years IT Infrastructure & Operations", TEXT)],
        ]),
        ("docker images --format '{{.Repository}}'", [
            [(name, TEXT)] for name in ("k3s", "argo-cd", "helm", "terraform", "ansible", "aws")
        ]),
        ("argocd app list", [
            [("NAME        SYNC     HEALTH", GREY)],
            [("game-qa     ", TEXT), ("Synced   Healthy", GREEN)],
            [("game-prod   ", TEXT), ("Synced   Healthy", GREEN)],
        ]),
        ("kubectl get pods -n observability", [
            [("NAME           READY   STATUS", GREY)],
            *[[(f"{name:<15}1/1     ", TEXT), ("Running", GREEN)]
              for name in ("prometheus", "grafana", "loki", "alloy", "alertmanager", "cloudwatch")],
        ]),
        ("ls /usr/bin | grep -E 'python|bash|psql'", [[("python3", TEXT)], [("bash", TEXT)], [("psql", TEXT)]]),
        ("terraform plan", [
            [("+ ", GREEN), ('aws_instance.app', TEXT)],
            [("+ ", GREEN), ('aws_db_instance.postgres', TEXT)],
            [("+ ", GREEN), ('aws_s3_bucket.assets', TEXT)],
            [("+ ", GREEN), ('aws_cloudfront_distribution.cdn', TEXT)],
            [("Plan: ", TEXT), ("4 to add", GREEN), (", 0 to change, 0 to destroy.", TEXT)],
        ]),
        ("systemctl status open-to-work", [
            [("● ", GREEN), ("open-to-work.service", TEXT)],
            [("   Active: ", TEXT), ("active (running)", GREEN), (" since today", TEXT)],
        ]),
        ("cat ~/.contact", [
            [("linkedin  ", TEXT), ("linkedin.com/in/kamil-kolmasiak-6aa683132", BLUE)],
            [("email     ", TEXT), ("kamil.kolmasiak@gmail.com", BLUE)],
        ]),
    ]


def text_line(x: float, y: float, segments: list[tuple[str, str]]) -> str:
    spans = "".join(f'<tspan fill="{color}">{escape(text)}</tspan>' for text, color in segments)
    return f'<text x="{x}" y="{y}" xml:space="preserve">{spans}</text>'


def draw_terminal(repos: list[dict], avatar_data_uri: str) -> str:
    width, height = 860, 250
    panel_x, panel_y, panel_w, panel_h = 170, 12, 676, 226
    text_x, first_line_y = panel_x + 16, panel_y + 50
    prompt_width = sum(len(text) for text, _ in PROMPT) * CHAR_WIDTH

    scenes = terminal_scenes(repos)
    timings, start = [], 0.0
    for command, _ in scenes:
        typing_seconds = len(command) * TYPE_SECONDS_PER_CHAR + 0.3
        timings.append((start, typing_seconds))
        start += typing_seconds + READ_SECONDS
    total = start
    hidden, shown = "opacity:0", "opacity:1"

    css, body = [], []
    for index, ((command, output), (scene_start, typing_seconds)) in enumerate(zip(scenes, timings)):
        typed_at = scene_start + typing_seconds
        scene_end = typed_at + READ_SECONDS
        typed_width = len(command) * CHAR_WIDTH
        css.append(keyframes(f"scene{index}", [(0, hidden), (scene_start, shown), (scene_end, hidden)], total))
        css.append(keyframes(f"type{index}", [
            (0, "transform:translateX(0)"),
            (scene_start, f"transform:translateX(0);animation-timing-function:steps({len(command)},end)"),
            (typed_at, f"transform:translateX({typed_width:.1f}px)"),
            (typed_at + 0.01, "transform:translateX(2000px)"),
        ], total))
        css.append(keyframes(f"output{index}", [(0, hidden), (typed_at, shown)], total))
        css.append(f"#scene{index},#output{index}{{opacity:0}}"
                   f"#scene{index}{{animation-name:scene{index}}}#type{index}{{animation-name:type{index}}}"
                   f"#output{index}{{animation-name:output{index}}}")

        command_x = text_x + prompt_width
        parts = [
            text_line(text_x, first_line_y, PROMPT + [(command, TEXT)]),
            f'<g id="type{index}" class="a"><rect x="{command_x}" y="{first_line_y - 14}" '
            f'width="{typed_width + 20}" height="18" fill="{PANEL}"/>'
            f'<rect x="{command_x}" y="{first_line_y - 12}" width="8" height="15" fill="{GREEN}"/></g>',
        ]
        output_parts = [text_line(text_x, first_line_y + (row + 1) * LINE_HEIGHT, segments)
                        for row, segments in enumerate(output)]
        last_y = first_line_y + (len(output) + 1) * LINE_HEIGHT
        output_parts.append(text_line(text_x, last_y, PROMPT))
        output_parts.append(f'<rect class="blink" x="{command_x}" y="{last_y - 12}" '
                            f'width="8" height="15" fill="{GREEN}"/>')
        parts.append(f'<g id="output{index}" class="a">{"".join(output_parts)}</g>')
        body.append(f'<g id="scene{index}" class="a">{"".join(parts)}</g>')

    css.append(f".a{{animation-duration:{total:.2f}s;animation-iteration-count:infinite;"
               "animation-timing-function:steps(1,end)}"
               "@keyframes blink{50%{opacity:0}}.blink{animation:blink 1s steps(1,end) infinite}")
    dots = "".join(f'<circle cx="{panel_x + 16 + i * 16}" cy="{panel_y + 14}" r="5" fill="{color}"/>'
                   for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Animated terminal: Kamil Kolmasiak, junior DevOps and cloud engineer, open to work">
<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;font-size:{FONT_SIZE}px}}{''.join(css)}</style>
<rect width="{width}" height="{height}" rx="12" fill="{BACKGROUND}"/>
<defs><clipPath id="avatar"><circle cx="85" cy="100" r="58"/></clipPath></defs>
<image href="{avatar_data_uri}" x="27" y="42" width="116" height="116" clip-path="url(#avatar)"/>
<circle cx="85" cy="100" r="59" fill="none" stroke="{GREEN}" stroke-width="2"/>
<text x="85" y="190" text-anchor="middle" fill="{TEXT}">Kamil</text>
<text x="85" y="208" text-anchor="middle" fill="{TEXT}">Kolmasiak</text>
<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
{dots}<text x="{panel_x + panel_w / 2}" y="{panel_y + 18}" text-anchor="middle" fill="{GREY}" style="font-size:11px">kamil@devops: ~</text>
{''.join(body)}
</svg>"""


# ---------------------------------------------------------------- pac-man

TICK_SECONDS, FLASH_SECONDS, FLASH_TOGGLES = 0.13, 0.16, 6
GAMES_PER_ANIMATION, MAX_TICKS_PER_GAME = 5, 700
GHOST_POOL = [("crab", ""), ("openai", "#ffffff"), ("docker", "#2496ED"), ("kubernetes", "#326CE5"),
              ("googlegemini", "#8E75B2"), ("terraform", "#844FBA"), ("amazonwebservices", "#FF9900"),
              ("prometheus", "#E6522C"), ("grafana", "#F46800"), ("githubactions", "#2088FF")]
EMPTY_CELL = "#161b22"
GITHUB_GREENS = ["#0e4429", "#006d32", "#26a641", "#39d353"]
AZURE_BLUES = ["#0c2d6b", "#1158c7", "#2f81f7", "#79c0ff"]  # days mostly committed in Azure DevOps
DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
CRAB_SYMBOL = (
    '<symbol id="icon-crab" viewBox="0 0 14 14" shape-rendering="crispEdges">'
    '<rect x="3" y="3" width="8" height="6" fill="#D97757"/><rect x="1" y="5" width="2" height="2" fill="#D97757"/>'
    '<rect x="11" y="5" width="2" height="2" fill="#D97757"/><rect x="5" y="5" width="1" height="1" fill="#0d1117"/>'
    '<rect x="8" y="5" width="1" height="1" fill="#0d1117"/>'
    + "".join(f'<rect x="{x}" y="9" width="1" height="3" fill="#D97757"/>' for x in (4, 6, 7, 9))
    + "</symbol>"
)


def pacman_is_caught(pacman, pacman_before, ghosts, ghosts_before) -> bool:
    """Same square, or Pac-Man and a ghost swapped squares in one tick."""
    return any(ghost == pacman or (ghost == pacman_before and before == pacman)
               for ghost, before in zip(ghosts, ghosts_before))


def play_one_game(food: set, width: int, height: int, rng: random.Random) -> dict:
    """Per-tick positions, the tick each food cell was eaten, and whether a ghost caught Pac-Man."""
    food = set(food)
    pacman = (width // 2, height // 2)
    ghosts = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    ghost_directions = [(0, 0)] * 4
    pacman_frames, ghost_frames, eaten_at_tick = [pacman], [list(ghosts)], {}
    if pacman in food:
        food.discard(pacman)
        eaten_at_tick[pacman] = 0
    caught = False
    for tick in range(1, MAX_TICKS_PER_GAME):
        if not food or caught:
            break
        target = min(food, key=lambda cell: (abs(cell[0] - pacman[0]) + abs(cell[1] - pacman[1]), cell))
        pacman_before, ghosts_before = pacman, list(ghosts)
        step_x = (target[0] > pacman[0]) - (target[0] < pacman[0])
        step_y = (target[1] > pacman[1]) - (target[1] < pacman[1])
        pacman = (pacman[0] + step_x, pacman[1]) if step_x else (pacman[0], pacman[1] + step_y)
        if pacman in food:
            food.discard(pacman)
            eaten_at_tick[pacman] = tick
        if tick % 2:
            for index, ghost in enumerate(ghosts):
                direction = ghost_directions[index]
                if rng.random() < 0.35 or direction == (0, 0):
                    options = [d for d in DIRECTIONS
                               if 0 <= ghost[0] + d[0] < width and 0 <= ghost[1] + d[1] < height]
                    if rng.random() < 0.3:
                        direction = min(options, key=lambda d: abs(pacman[0] - ghost[0] - d[0])
                                        + abs(pacman[1] - ghost[1] - d[1]))
                    else:
                        direction = rng.choice(options)
                moved = (ghost[0] + direction[0], ghost[1] + direction[1])
                if 0 <= moved[0] < width and 0 <= moved[1] < height:
                    ghosts[index] = moved
                else:
                    direction = (0, 0)
                ghost_directions[index] = direction
        pacman_frames.append(pacman)
        ghost_frames.append(list(ghosts))
        caught = pacman_is_caught(pacman, pacman_before, ghosts, ghosts_before)
        if caught:  # a ghost that swapped squares lands on Pac-Man instead of passing it
            ghost_frames[-1] = [pacman if (ghost, before) == (pacman_before, pacman) else ghost
                                for ghost, before in zip(ghosts, ghosts_before)]
    return dict(pacman=pacman_frames, ghosts=ghost_frames, eaten=eaten_at_tick, caught=caught)


def icon_symbol(icon: str, color: str) -> str:
    if icon == "crab":
        return CRAB_SYMBOL
    svg = fetch(f"{SIMPLE_ICONS}{icon}.svg").decode()
    path = svg[svg.index("<path"):svg.index("</svg>")].replace("<path", f'<path fill="{color}"', 1)
    return f'<symbol id="icon-{icon}" viewBox="0 0 24 24">{path}</symbol>'


def contribution_color(count: int, nonzero_counts: list[int], shades: list[str]) -> str:
    """GitHub-style shade: quartile of this count among all days with contributions."""
    if count == 0:
        return EMPTY_CELL
    ordered = sorted(nonzero_counts)
    quartile_tops = [ordered[len(ordered) * q // 4] for q in (1, 2, 3)]
    return shades[sum(count > top for top in quartile_tops)]


def graph_labels(weeks: list[dict], left: int, top: int, step: int, width: int, height: int) -> str:
    """Month names, Mon/Wed/Fri, total count and the Less-More legend, laid out like GitHub's."""
    labels, last_month_x = [], -99
    for x, week in enumerate(weeks):
        month = datetime.date.fromisoformat(week["contributionDays"][0]["date"]).strftime("%b")
        if (x == 0 or month != previous_month) and x - last_month_x >= 3 and x < len(weeks) - 2:
            labels.append(f'<text x="{left + x * step}" y="{top - 7}">{month}</text>')
            last_month_x = x
        previous_month = month
    for row, day in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        labels.append(f'<text x="{left - 6}" y="{top + row * step + 9}" text-anchor="end">{day}</text>')
    total = sum(day["contributionCount"] for week in weeks for day in week["contributionDays"])
    labels.append(f'<text x="{left}" y="{height - 30}">{total} contributions in the last year</text>')
    legend_x = width - 16 - 5 * step - 30
    for baseline, name, shades in ((height - 30, "GitHub", GITHUB_GREENS), (height - 14, "Azure DevOps", AZURE_BLUES)):
        labels.append(f'<text x="{legend_x - 34}" y="{baseline}" text-anchor="end">{name}</text>'
                      f'<text x="{legend_x - 6}" y="{baseline}" text-anchor="end">Less</text>'
                      f'<text x="{legend_x + 5 * step + 3}" y="{baseline}">More</text>')
        labels += [f'<rect x="{legend_x + i * step}" y="{baseline - 10}" width="11" height="11" rx="2" fill="{color}"/>'
                   for i, color in enumerate([EMPTY_CELL] + shades)]
    return f'<g fill="{GREY}" style="font:10px -apple-system,Segoe UI,Helvetica,Arial,sans-serif">{"".join(labels)}</g>'


def draw_pacman(weeks: list[dict], seed: str) -> str:
    cell, gap, left, top, bottom, right = 11, 3, 40, 30, 50, 16
    step = cell + gap
    grid_w, grid_h = len(weeks), 7
    width, height = left + right + grid_w * step - gap, top + bottom + grid_h * step - gap

    def center(position):
        return left + position[0] * step + cell / 2, top + position[1] * step + cell / 2

    def move_to(position):
        x, y = center(position)
        return f"transform:translate({x:.1f}px,{y:.1f}px)"

    fills = {(x, day["weekday"]): day["color"]
              for x, week in enumerate(weeks) for day in week["contributionDays"]}
    food = {position for position, fill in fills.items() if fill != EMPTY_CELL}
    rng = random.Random(seed)
    games, start = [], 0.0
    for _ in range(GAMES_PER_ANIMATION):
        game = play_one_game(food, grid_w, grid_h, rng)
        game["start"] = start
        game["end"] = start + (len(game["pacman"]) - 1) * TICK_SECONDS
        start = game["end"] + (FLASH_SECONDS * FLASH_TOGGLES if game["caught"] else TICK_SECONDS)
        game["next"] = start
        games.append(game)
    total = start
    css = [f".a{{animation-duration:{total:.2f}s;animation-iteration-count:infinite;"
           "animation-timing-function:steps(1,end)}.m{animation-timing-function:linear}"]

    # Cells: refill at each game start, go dark when eaten.
    cells = []
    for index, (position, fill) in enumerate(sorted(fills.items())):
        x, y = left + position[0] * step, top + position[1] * step
        rect = f'x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"'
        if fill == EMPTY_CELL:
            cells.append(f"<rect {rect}/>")
            continue
        frames = []
        for game in games:
            frames.append((game["start"], f"fill:{fill}"))
            if position in game["eaten"]:
                frames.append((game["start"] + game["eaten"][position] * TICK_SECONDS,
                               f"fill:{EMPTY_CELL}"))
        css.append(keyframes(f"c{index}", frames, total) + f"#c{index}{{animation-name:c{index}}}")
        cells.append(f'<rect id="c{index}" class="a" {rect}/>')

    # Pac-Man: one sprite across all games, turned to face where it moves.
    frames, angle, previous = [], 0, None
    for game in games:
        for tick, position in enumerate(game["pacman"]):
            if tick == 0 and frames:  # jump back to the middle without sliding
                frames.append((game["start"] - 0.005, frames[-1][1]))
            elif tick > 0 and position != previous:
                wanted = {(1, 0): 0, (-1, 0): 180, (0, 1): 90, (0, -1): -90}[
                    (position[0] - previous[0], position[1] - previous[1])]
                angle += (wanted - angle + 180) % 360 - 180
            frames.append((game["start"] + tick * TICK_SECONDS, f"{move_to(position)} rotate({angle}deg)"))
            previous = position
    frames.append((total, frames[-1][1]))  # hold still; an open end slides back to the corner
    css.append(keyframes("pacman", frames, total) + "#pacman{animation-name:pacman}"
               "@keyframes chomp{50%{opacity:0}}.chomp{animation:chomp .26s steps(1,end) infinite}")

    # Ghosts: four per game, each game takes the next four logos from the pool.
    ghosts, used_icons = [], {}
    for game_index, game in enumerate(games):
        for slot in range(4):
            icon, color = GHOST_POOL[(game_index * 4 + slot) % len(GHOST_POOL)]
            used_icons[icon] = color
            name = f"g{game_index}_{slot}"
            moves, last = [(0, move_to(game["ghosts"][0][slot]))], None
            for tick, positions in enumerate(game["ghosts"]):
                if positions[slot] != last:
                    moves.append((game["start"] + tick * TICK_SECONDS, move_to(positions[slot])))
                    last = positions[slot]
            moves.append((total, move_to(last)))  # stay put after the game ends
            css.append(keyframes(f"{name}v", [(0, "opacity:0"), (game["start"], "opacity:1"),
                                              (game["next"], "opacity:0")], total)
                       + keyframes(f"{name}m", moves, total)
                       + f"#{name}v{{opacity:0;animation-name:{name}v}}#{name}m{{animation-name:{name}m}}")
            ghosts.append(f'<g id="{name}v" class="a"><g id="{name}m" class="a m">'
                          f'<use href="#icon-{icon}" x="-6.5" y="-6.5" width="13" height="13"/></g></g>')

    # Flash the whole board when a ghost catches Pac-Man.
    flash = [(0, "opacity:1")]
    for game in games:
        if game["caught"]:
            flash += [(game["end"] + toggle * FLASH_SECONDS, f"opacity:{0.15 if toggle % 2 == 0 else 1}")
                      for toggle in range(FLASH_TOGGLES)]
            flash.append((game["next"], "opacity:1"))
    css.append(keyframes("flash", flash, total) + "#board{animation-name:flash}")

    symbols = "".join(icon_symbol(icon, color) for icon, color in used_icons.items())
    pacman_sprite = ('<g id="pacman" class="a m"><circle r="6.5" fill="#f7d51d"/>'
                     f'<path class="chomp" d="M0,0 L7,-4.5 L7,4.5 Z" fill="{BACKGROUND}"/></g>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Pac-Man eating the contribution graph while tech-logo ghosts roam">
<style>{''.join(css)}</style>
<defs>{symbols}</defs>
<rect width="{width}" height="{height}" rx="12" fill="{BACKGROUND}"/>
{graph_labels(weeks, left, top, step, width, height)}
<g id="board" class="a">{''.join(cells)}{''.join(ghosts)}{pacman_sprite}</g>
</svg>"""


# ---------------------------------------------------------------- main

def main() -> None:
    repos = fetch_json(f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=100")
    repos = [r for r in repos if not r["fork"] and r["name"].lower() != USER.lower()]
    photo = (Path(__file__).parent / "assets" / "photo.jpg").read_bytes()
    avatar_uri = "data:image/jpeg;base64," + base64.b64encode(photo).decode()
    repos.insert(0, {"name": AZURE_GAME_REPO})
    calendar = fetch_json("https://api.github.com/graphql", {"query": (
        f'{{user(login:"{USER}"){{contributionsCollection{{contributionCalendar{{weeks{{'
        "contributionDays{date weekday contributionCount}}}}}}")})
    if "errors" in calendar:
        raise SystemExit(f"GraphQL error: {calendar['errors']}")
    weeks = calendar["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    azure = azure_devops_commits_per_day(days[0]["date"])
    for day in days:
        github_count = day["contributionCount"]
        day["contributionCount"] += azure.get(day["date"], 0)
        day["mostly_azure"] = azure.get(day["date"], 0) > github_count
    nonzero_counts = [day["contributionCount"] for day in days if day["contributionCount"]]
    for day in days:
        shades = AZURE_BLUES if day["mostly_azure"] else GITHUB_GREENS
        day["color"] = contribution_color(day["contributionCount"], nonzero_counts, shades)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/terminal.svg", "w", encoding="utf-8") as file:
        file.write(draw_terminal(repos, avatar_uri))
    with open(f"{OUT_DIR}/pacman.svg", "w", encoding="utf-8") as file:
        file.write(draw_pacman(weeks, datetime.date.today().isoformat()))


if __name__ == "__main__":
    main()
