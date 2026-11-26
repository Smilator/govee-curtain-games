"""Arkanoid sulla tenda LED Govee H70B4.

Frecce sinistra/destra = racchetta, spazio = lancia la palla, q = esci.
3 vite (puntini a destra del punteggio). Finiti i mattoni si passa al livello dopo.
Quando perdi parte un'animazione e si riparte da 0.
    python arkanoid.py                  gioca sulla tenda
    python arkanoid.py --solo-schermo   gioca solo nel Terminale
"""
import curses
import math
import random

from tenda import TOP, H, W, blank, draw_header, play, rect

PADDLE_Y = H - 1
PADDLE_W = 7
BRICK_W = 4                    # 3 pixel di mattone + 1 di spazio
BRICK_TOP = TOP + 2
ROW_COLORS = [(255, 0, 40), (255, 90, 0), (255, 200, 0), (0, 220, 60), (0, 140, 255)]

PADDLE = (0, 200, 255)
BALL = (255, 255, 0)
LIFE = (255, 0, 80)


class Arkanoid:
    title = "ARKANOID"
    help = "frecce = racchetta   spazio = lancia"

    def __init__(self):
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.over = False
        self.fx = {}
        self.new_level()

    def new_level(self):
        rows = ROW_COLORS[:min(len(ROW_COLORS), 2 + self.level)]
        self.bricks = {(c, r): col for r, col in enumerate(rows) for c in range(W // BRICK_W)}
        self.px = (W - PADDLE_W) // 2
        self.new_ball()

    def new_ball(self):
        self.stuck = True
        self.ball_on_paddle()

    def ball_on_paddle(self):
        self.bx, self.by = self.px + PADDLE_W / 2, PADDLE_Y - 1
        self.vx = self.vy = 0.0

    @property
    def speed(self):
        return min(1.0, 0.7 + 0.1 * self.level)   # pixel per passo

    tick = 0.08

    def launch(self, degrees):
        a = math.radians(degrees)
        self.vx, self.vy = self.speed * math.sin(a), -self.speed * math.cos(a)

    def key(self, k):
        if k == curses.KEY_LEFT:
            self.px = max(0, self.px - 2)
        elif k == curses.KEY_RIGHT:
            self.px = min(W - PADDLE_W, self.px + 2)
        elif k == ord(" ") and self.stuck:
            self.stuck = False
            self.launch(random.choice((-35, -25, 25, 35)))
        if self.stuck:
            self.ball_on_paddle()

    def brick_at(self, x, y):
        x, r = int(x), int(y) - BRICK_TOP
        if r < 0 or x % BRICK_W == BRICK_W - 1:
            return None
        k = (x // BRICK_W, r)
        return k if k in self.bricks else None

    def step(self):
        if self.stuck:
            return
        # movimento orizzontale: pareti e mattoni
        nx = self.bx + self.vx
        if not 0 <= nx < W:
            self.vx, nx = -self.vx, self.bx
        b = self.brick_at(nx, self.by)
        if b:
            del self.bricks[b]
            self.score += 1
            self.vx, nx = -self.vx, self.bx
        self.bx = nx
        # movimento verticale: soffitto, mattoni, racchetta
        ny = self.by + self.vy
        if ny < TOP:
            self.vy, ny = abs(self.vy), self.by
        b = self.brick_at(self.bx, ny)
        if b:
            del self.bricks[b]
            self.score += 1
            self.vy, ny = -self.vy, self.by
        if self.vy > 0 and ny >= PADDLE_Y and self.px - 1 <= self.bx <= self.px + PADDLE_W:
            # più lontano dal centro colpisci, più la palla va di lato (mai dritta in verticale)
            off = (self.bx - (self.px + PADDLE_W / 2)) / (PADDLE_W / 2)
            deg = max(-60, min(60, off * 60))
            self.launch(deg if abs(deg) >= 15 else (15 if deg >= 0 else -15))
            ny = PADDLE_Y - 1
        self.by = ny
        if self.by >= H:                          # palla persa
            self.lives -= 1
            if self.lives == 0:
                self.over = True
            else:
                self.new_ball()
        elif not self.bricks:                     # livello finito
            self.level += 1
            self.new_level()

    def pixels(self):
        img = blank()
        fx = self.fx
        draw_header(img, self.score_text(), fx.get("score", True))
        for i in range(self.lives):
            rect(img, W - 2 - i * 3, 1, 2, 2, LIFE)
        for (c, r), col in self.bricks.items():
            rect(img, c * BRICK_W, BRICK_TOP + r, BRICK_W - 1, 1, fx.get("bricks") or col)
        rect(img, self.px, PADDLE_Y, PADDLE_W, 1, fx.get("paddle") or PADDLE)
        if not self.over and int(self.by) < H:
            rect(img, int(self.bx), int(self.by), 1, 1, BALL)
        return img

    def end_animation(self):
        for i in range(6):                        # racchetta e mattoni lampeggiano rossi
            col = (255, 0, 0) if i % 2 == 0 else (60, 0, 0)
            self.fx = {"paddle": col, "bricks": col}
            yield 0.15
        self.fx = {"paddle": (60, 0, 0)}
        order = sorted(self.bricks, key=lambda k: (-k[1], k[0]))
        while order:                              # i mattoni spariscono dal basso
            for k in order[:3]:
                del self.bricks[k]
            order = order[3:]
            yield 0.05
        for i in range(6):                        # il punteggio finale lampeggia
            self.fx["score"] = i % 2 == 1
            yield 0.3

    def score_text(self):
        return str(self.score)


if __name__ == "__main__":
    play(Arkanoid())
