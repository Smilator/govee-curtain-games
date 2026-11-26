"""Snake sulla tenda LED Govee H70B4.

Frecce = muovi, q = esci. I bordi fanno da tunnel.
Quando perdi parte un'animazione e si riparte da 0.
    python snake.py                  gioca sulla tenda
    python snake.py --solo-schermo   gioca solo nel Terminale
"""
import curses
import random

from tenda import TOP, H, W, blank, draw_header, play, rect

CELL = 2                                  # ogni casella = blocco 2x2 di pixel
GW, GH = W // CELL, (H - TOP) // CELL     # campo 20x10 caselle

HEAD = (255, 180, 0)
FOOD = (255, 0, 0)
DEAD = (120, 0, 0)
SPARK = (255, 120, 0)

DIRS = {curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
        curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0)}


def body_color(i, n):
    """Sfumatura dal verde acceso al verde-azzurro verso la coda."""
    t = i / max(1, n - 1)
    return (0, int(255 - 120 * t), int(60 + 140 * t))


class Snake:
    title = "SNAKE"
    help = "frecce = muovi"

    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = GW // 2, GH // 2
        self.snake = [(cx - i, cy) for i in range(4)]
        self.dir = self.next_dir = (1, 0)
        self.over = False
        self.score = 0
        self.fx = {}                      # stato dell'animazione di fine partita
        self.place_food()

    def place_food(self):
        free = [(x, y) for x in range(GW) for y in range(GH) if (x, y) not in self.snake]
        self.food = random.choice(free)

    @property
    def tick(self):
        return max(0.15, 0.35 - self.score * 0.01)

    def key(self, k):
        d = DIRS.get(k)
        if d and (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
            self.next_dir = d

    def step(self):
        self.dir = self.next_dir
        hx, hy = self.snake[0]
        head = ((hx + self.dir[0]) % GW, (hy + self.dir[1]) % GH)
        grow = head == self.food
        body = self.snake if grow else self.snake[:-1]
        if head in body:
            self.over = True
            return
        self.snake = [head] + body
        if grow:
            self.score += 1
            self.place_food()

    def pixels(self):
        img = blank()
        fx = self.fx
        draw_header(img, self.score_text(), fx.get("score", True))

        def cell(x, y, col):
            rect(img, x * CELL, TOP + y * CELL, CELL, CELL, col)

        if fx.get("food", True):
            cell(*self.food, FOOD)
        n = len(self.snake)
        for i, (x, y) in enumerate(self.snake):
            cell(x, y, fx.get("snake") or (DEAD if self.over else HEAD if i == 0 else body_color(i, n)))
        for x, y in fx.get("sparks", ()):
            cell(x, y, SPARK)
        return img

    def end_animation(self):
        self.fx = {"food": False}
        for i in range(6):                        # il serpente lampeggia rosso
            self.fx["snake"] = (255, 0, 0) if i % 2 == 0 else (50, 0, 0)
            yield 0.15
        self.fx["snake"] = DEAD
        delay = max(0.04, min(0.1, 1.5 / len(self.snake)))
        while self.snake:                         # esplode dalla testa alla coda
            self.fx["sparks"] = [self.snake.pop(0)]
            yield delay
        self.fx["sparks"] = []
        yield 0.3
        for i in range(6):                        # il punteggio finale lampeggia
            self.fx["score"] = i % 2 == 1
            yield 0.3

    def score_text(self):
        return str(self.score)


if __name__ == "__main__":
    play(Snake())
