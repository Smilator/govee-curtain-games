"""Pong contro il computer sulla tenda LED Govee H70B4.

Tu sei la racchetta azzurra a sinistra: frecce su/giù, q = esci.
In alto il punteggio "tu-computer". Vince chi arriva a 5, poi si riparte da 0-0.
    python pong.py                  gioca sulla tenda
    python pong.py --solo-schermo   gioca solo nel Terminale
"""
import curses
import math
import random

from tenda import TOP, H, W, blank, draw_header, play, rect

PAD_H = 5
WIN = 5
FIELD_TOP, FIELD_BOTTOM = TOP, H - 1      # righe giocabili (comprese)

ME = (0, 200, 255)
CPU = (255, 60, 0)
BALL = (255, 255, 0)
NET = (0, 0, 60)


class Pong:
    title = "PONG"
    help = "frecce su/giu = racchetta   (vince chi fa 5)"
    tick = 0.08

    def __init__(self):
        self.reset()

    def reset(self):
        self.me = self.cpu = 0
        self.over = False
        self.fx = {}
        self.my_y = self.cpu_y = (FIELD_TOP + FIELD_BOTTOM - PAD_H) // 2 + 1
        self.serve(random.choice((-1, 1)))

    def serve(self, direction):
        self.bx, self.by = W / 2, (FIELD_TOP + FIELD_BOTTOM) / 2
        self.speed = 1.0
        a = math.radians(random.uniform(-30, 30))
        self.vx, self.vy = direction * math.cos(a), math.sin(a)
        self.wait = 6                             # breve pausa prima del servizio

    def key(self, k):
        if k == curses.KEY_UP:
            self.my_y = max(FIELD_TOP, self.my_y - 2)
        elif k == curses.KEY_DOWN:
            self.my_y = min(FIELD_BOTTOM - PAD_H + 1, self.my_y + 2)

    def bounce(self, pad_y, direction):
        off = (self.by - (pad_y + PAD_H / 2)) / (PAD_H / 2)
        a = math.radians(max(-55, min(55, off * 55)))
        self.speed = min(1.6, self.speed + 0.05)
        self.vx, self.vy = direction * self.speed * math.cos(a), self.speed * math.sin(a)

    def step(self):
        # il computer insegue la palla ma più lento di te: si può battere
        target = self.by - PAD_H / 2
        if self.vx > 0 and abs(target - self.cpu_y) > 1 and random.random() < 0.8:
            self.cpu_y += 1 if target > self.cpu_y else -1
        self.cpu_y = max(FIELD_TOP, min(FIELD_BOTTOM - PAD_H + 1, self.cpu_y))
        if self.wait:
            self.wait -= 1
            return
        self.bx += self.vx
        self.by += self.vy
        if self.by < FIELD_TOP:
            self.by, self.vy = 2 * FIELD_TOP - self.by, -self.vy
        if self.by > FIELD_BOTTOM:
            self.by, self.vy = 2 * FIELD_BOTTOM - self.by, -self.vy
        if self.vx < 0 and self.bx < 2 and self.my_y - 1 <= self.by <= self.my_y + PAD_H:
            self.bx = 2
            self.bounce(self.my_y, 1)
        elif self.vx > 0 and self.bx >= W - 2 and self.cpu_y - 1 <= self.by <= self.cpu_y + PAD_H:
            self.bx = W - 2.01
            self.bounce(self.cpu_y, -1)
        elif self.bx < 0 or self.bx >= W:          # punto
            if self.bx < 0:
                self.cpu += 1
            else:
                self.me += 1
            if max(self.me, self.cpu) >= WIN:
                self.over = True
            else:
                self.serve(1 if self.bx < 0 else -1)

    def pixels(self):
        img = blank()
        fx = self.fx
        draw_header(img, self.score_text(), fx.get("score", True))
        for y in range(FIELD_TOP, H, 2):
            img[y][W // 2] = NET
        rect(img, 0, self.my_y, 1, PAD_H, fx.get("me") or ME)
        rect(img, W - 1, self.cpu_y, 1, PAD_H, fx.get("cpu") or CPU)
        if not self.over and 0 <= self.bx < W:
            rect(img, int(self.bx), int(round(self.by)), 1, 1, BALL)
        return img

    def end_animation(self):
        winner, col = ("me", ME) if self.me > self.cpu else ("cpu", CPU)
        for i in range(8):                        # la racchetta di chi ha vinto lampeggia
            self.fx = {winner: col if i % 2 == 0 else (0, 0, 40)}
            yield 0.15
        for i in range(6):                        # poi il punteggio finale
            self.fx = {"score": i % 2 == 1}
            yield 0.3

    def score_text(self):
        return f"{self.me}-{self.cpu}"


if __name__ == "__main__":
    play(Pong())
