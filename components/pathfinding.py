import heapq
from settings import TILE_SIZE
import math


def build_blocked_grid(walls):
    blocked = set()
    for wall in walls:
        blocked.add((wall.x // TILE_SIZE, wall.y // TILE_SIZE))
    return blocked

def find_path(start_pos, goal_pos, walls, map_width=640, map_height=400):
    cols = map_width // TILE_SIZE
    rows = map_height // TILE_SIZE
    blocked = build_blocked_grid(walls)

    sx, sy = start_pos
    gx, gy = goal_pos

    sc = max(0, min(cols - 1, int(sx) // TILE_SIZE))
    sr = max(0, min(rows - 1, int(sy) // TILE_SIZE))
    gc = max(0, min(cols - 1, int(gx) // TILE_SIZE))
    gr = max(0, min(rows - 1, int(gy) // TILE_SIZE))

    start = (sc, sr)
    goal = (gc, gr)

    if start == goal:
        return []

    if goal in blocked:
        neighbors = [
            (gc + dx, gr + dy)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if 0 <= gc + dx < cols and 0 <= gr + dy < rows and (gc + dx, gr + dy) not in blocked
        ]
        if not neighbors:
            return []
        goal = min(neighbors, key=lambda n: math.hypot(n[0] - sc, n[1] - sr))

    goal_c, goal_r = goal
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    directions = [
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, 1.41), (1, -1, 1.41), (-1, 1, 1.41), (1, 1, 1.41)
    ]

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                cur_c, cur_r = current
                path.append((cur_c * TILE_SIZE + TILE_SIZE // 2, cur_r * TILE_SIZE + TILE_SIZE // 2))
                current = came_from[current]
            path.reverse()
            return path

        cx, cy = current
        for dx, dy, cost in directions:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < cols and 0 <= ny < rows) or (nx, ny) in blocked:
                continue
            if dx != 0 and dy != 0:
                if (cx + dx, cy) in blocked or (cx, cy + dy) in blocked:
                    continue

            tentative_g = g_score[current] + cost
            if tentative_g < g_score.get((nx, ny), 999999):
                came_from[(nx, ny)] = current
                g_score[(nx, ny)] = tentative_g
                f_score = tentative_g + abs(nx - goal_c) + abs(ny - goal_r)
                heapq.heappush(open_set, (f_score, (nx, ny)))

    return []
