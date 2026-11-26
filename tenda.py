"""Libreria per giocare sulla tenda LED Govee H70B4 (40x26 pixel) via Bluetooth.

Contiene:
- il collegamento Bluetooth cifrato con la tenda (classe Tenda);
- la creazione delle immagini PNG che la tenda sa mostrare;
- gli strumenti di disegno (rettangoli, cifre, punteggio in alto);
- l'anteprima nel Terminale e il ciclo di gioco comune (funzione play).

Opzioni da riga di comando, valide per tutti i giochi:
    --solo-schermo          gioca senza tenda, solo con l'anteprima nel Terminale
    --non-specchiare        non girare l'immagine destra/sinistra
    --specchia-verticale    gira l'immagine sopra/sotto
"""
import asyncio
import curses
import os
import struct
import subprocess
import sys
import time
import zlib

W, H = 40, 26            # pixel della tenda
TOP = 6                  # righe in alto riservate al punteggio (cifre alte 5 + linea)

BG = (0, 0, 1)           # sfondo: la tenda non spegne il nero puro, questo è il colore più scuro
LINE = (0, 0, 40)        # linea sotto il punteggio
SCORE = (255, 180, 0)    # colore del punteggio

MIRROR_X = "--non-specchiare" not in sys.argv
MIRROR_Y = "--specchia-verticale" in sys.argv


# =============================================================================
# Disegno
# =============================================================================
# cifre 3x5: ogni stringa sono 5 righe da 3 pixel
FONT = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
        "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
        "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
        "9": "111101111001111", "-": "000000111000000"}


def blank():
    """Immagine vuota W x H: lista di righe di colori (r, g, b)."""
    return [[BG] * W for _ in range(H)]


def rect(img, x0, y0, w, h, col):
    for y in range(max(0, y0), min(H, y0 + h)):
        for x in range(max(0, x0), min(W, x0 + w)):
            img[y][x] = col


def draw_text(img, txt, x0, y0, col):
    for k, ch in enumerate(txt):
        bits = FONT[ch]
        for i, bit in enumerate(bits):
            if bit == "1":
                rect(img, x0 + k * 4 + i % 3, y0 + i // 3, 1, 1, col)


def draw_header(img, txt, show=True):
    """Punteggio centrato in alto e linea di separazione, uguale in tutti i giochi."""
    if show:
        draw_text(img, txt, (W - (len(txt) * 4 - 1)) // 2, 0, SCORE)
    rect(img, 0, TOP - 1, W, 1, LINE)


# =============================================================================
# PNG (stesso formato usato dall'app Govee)
# =============================================================================
def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def make_png(img):
    raw = b"".join(b"\0" + bytes(c for p in row for c in p) for row in img)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", len(img[0]), len(img), 8, 2, 0, 0, 0))
            + _chunk(b"sRGB", b"\x00")
            + _chunk(b"sBIT", b"\x05\x06\x05")
            + _chunk(b"IDAT", zlib.compress(raw, 9))
            + _chunk(b"IEND", b""))


def oriented(img):
    if MIRROR_X:
        img = [row[::-1] for row in img]
    if MIRROR_Y:
        img = img[::-1]
    return img


# =============================================================================
# Cifratura del protocollo Bluetooth Govee
# Handshake con la chiave fissa del protocollo (pubblica, uguale per tutti i
# dispositivi), poi ogni pacchetto è cifrato con la chiave di sessione:
# AES-128-ECB sui blocchi da 16 byte e RC4 sui byte che avanzano.
# =============================================================================
PROTOCOL_KEY = b"MakingLifeSmarte"


def _aes(key, data, decrypt):
    if not data:
        return b""
    args = ["openssl", "enc", "-aes-128-ecb", "-nopad", "-K", key.hex()] + (["-d"] if decrypt else [])
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout


def _rc4(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for c in data:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(c ^ s[(s[i] + s[j]) % 256])
    return bytes(out)


def _crypt(key, data, decrypt):
    n = len(data) // 16 * 16
    return _aes(key, data[:n], decrypt) + _rc4(key, data[n:])


def _xor(data):
    c = 0
    for b in data:
        c ^= b
    return c


def _cmd(*b):
    """Comando corto: 19 byte + controllo XOR."""
    p = bytes(b) + bytes(19 - len(b))
    return p + bytes([_xor(p)])


# =============================================================================
# Collegamento con la tenda
# =============================================================================
WRITE_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b11"
NOTIFY_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b10"
IMG_HEAD = bytes.fromhex("010200585fffffff64000001f40000")
IMG_TAIL = bytes.fromhex("00006401f401000000")
MAX_WRITE = 509          # byte per invio (MTU 512 - 3)


class Tenda:
    def __init__(self, name="H70B4", log=print):
        self.name = name
        self.log = log
        self.client = None
        self.key = None
        self.rx = asyncio.Queue()
        self.last = None
        self.info = "..."
        self._keepalive_task = None

    async def connect(self):
        from bleak import BleakClient, BleakScanner

        dev = None
        for attempt in range(4):
            self.log("cerco la tenda..." if attempt == 0 else
                     f"non la trovo, riprovo ({attempt + 1}/4): stacca e riattacca la tenda dalla corrente")
            dev = await BleakScanner.find_device_by_filter(
                lambda d, a: self.name in (d.name or a.local_name or ""), timeout=20)
            if dev:
                break
        if not dev:
            raise RuntimeError("tenda non trovata: vedi 'Problemi comuni' nel README")
        self.log(f"trovata {dev.name}, mi collego...")
        self.client = BleakClient(dev, timeout=20)
        await self.client.connect()
        await self.client.start_notify(NOTIFY_CHAR, self._on_notify)
        # handshake: due scambi con la chiave fissa, il primo restituisce la chiave di sessione
        await self._write(_cmd(0xE7, 0x01, *os.urandom(17)), PROTOCOL_KEY)
        self.key = (await self._wait(b"\xe7\x01"))[2:18]
        await self._write(_cmd(0xE7, 0x02, *os.urandom(17)), PROTOCOL_KEY)
        await self._wait(b"\xe7\x02")
        await self.send(_cmd(0x33, 0x01, 0x01))  # accendi
        await asyncio.sleep(0.3)
        self._keepalive_task = asyncio.create_task(self._keepalive())
        self.info = "tenda collegata"
        self.log("collegata")

    def _on_notify(self, _, data):
        for k in [self.key, PROTOCOL_KEY]:
            if k:
                p = _crypt(k, bytes(data), True)
                if _xor(p) == 0:
                    self.rx.put_nowait(p)
                    return

    async def _write(self, plain, key):
        await self.client.write_gatt_char(WRITE_CHAR, _crypt(key, plain, False), response=False)

    async def send(self, plain):
        await self._write(plain, self.key)

    async def _wait(self, prefix, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            try:
                p = await asyncio.wait_for(self.rx.get(), end - time.time())
            except asyncio.TimeoutError:
                break
            if p.startswith(prefix):
                return p
        raise RuntimeError(f"nessuna risposta {prefix.hex()}")

    async def _keepalive(self):
        while True:
            await asyncio.sleep(2)
            try:
                await self.send(_cmd(0xAA, 0x01))
            except Exception:
                return

    async def show(self, img):
        """Mostra un'immagine W x H sulla tenda e aspetta la conferma."""
        png = make_png(oriented(img))
        if png == self.last:
            return
        self.last = png
        while not self.rx.empty():
            self.rx.get_nowait()
        t = time.time()
        body = IMG_HEAD + len(png).to_bytes(2, "little") + png + IMG_TAIL
        step = MAX_WRITE - 4
        for n, i in enumerate(range(0, len(body), step)):
            part = b"\xa4" + n.to_bytes(2, "little") + body[i:i + step]
            await self.send(part + bytes([_xor(part)]))
        await self.send(b"\xa4\xff\xff\xa4")              # fine immagine
        await self.send(_cmd(0x33, 0x05, 0x0A, 0x20, 0x03))  # mostrala (va mandato ogni volta)
        try:
            await self._wait(b"\x33\x05", timeout=1.0)
            self.info = f"tenda ok, {int((time.time() - t) * 1000)} ms"
        except RuntimeError:
            self.info = "tenda: nessuna conferma"

    async def close(self):
        if self._keepalive_task:
            self._keepalive_task.cancel()
        if self.client:
            await self.client.disconnect()


# =============================================================================
# Anteprima nel Terminale
# =============================================================================
_BASIC = [(curses.COLOR_RED, (255, 0, 0)), (curses.COLOR_GREEN, (0, 255, 0)),
          (curses.COLOR_YELLOW, (255, 255, 0)), (curses.COLOR_BLUE, (0, 0, 255)),
          (curses.COLOR_MAGENTA, (255, 0, 255)), (curses.COLOR_CYAN, (0, 255, 255)),
          (curses.COLOR_WHITE, (255, 255, 255))]


def _color_pair(p):
    if max(p) < 30:
        return 0
    return 1 + min(range(len(_BASIC)), key=lambda i: sum((a - b) ** 2 for a, b in zip(p, _BASIC[i][1])))


def _preview(scr, img, top_line, help_line, colors):
    scr.erase()
    try:
        scr.addstr(0, 0, top_line[:2 * W + 2])
        scr.addstr(1, 0, "+" + "-" * 2 * W + "+")
        for y, row in enumerate(img):
            scr.addstr(2 + y, 0, "|")
            for x, p in enumerate(row):
                n = _color_pair(p)
                if n:
                    scr.addstr(2 + y, 1 + 2 * x, "  " if colors else "##", curses.color_pair(n) if colors else 0)
            scr.addstr(2 + y, 1 + 2 * W, "|")
        scr.addstr(2 + H, 0, "+" + "-" * 2 * W + "+")
        scr.addstr(3 + H, 0, help_line[:2 * W + 2])
    except curses.error:
        pass  # finestra troppo piccola: ingrandisci il Terminale
    scr.refresh()


# =============================================================================
# Ciclo di gioco comune
# =============================================================================
class _Quit(Exception):
    pass


async def _run(scr, game):
    curses.curs_set(0)
    scr.nodelay(True)
    scr.keypad(True)
    try:
        curses.start_color()
        for i, (c, _) in enumerate(_BASIC, 1):
            curses.init_pair(i, c, c)
        colors = True
    except curses.error:
        colors = False

    tenda = None
    if "--solo-schermo" not in sys.argv:
        def log(s):
            scr.erase()
            scr.addstr(0, 0, s[:79])
            scr.refresh()
        tenda = Tenda(log=log)
        await tenda.connect()

    def read_keys():
        while True:
            k = scr.getch()
            if k == -1:
                return
            if k in (ord("q"), ord("Q")):
                raise _Quit
            if not game.over:
                game.key(k)

    async def draw():
        img = game.pixels()
        info = tenda.info if tenda else "solo schermo"
        _preview(scr, img, f"{game.title}  punti: {game.score_text()}   {info}", game.help + "   q = esci", colors)
        if tenda:
            await tenda.show(img)

    try:
        while True:
            t0 = time.time()
            read_keys()
            game.step()
            await draw()
            if game.over:
                for pause in game.end_animation():
                    t1 = time.time()
                    read_keys()
                    await draw()
                    await asyncio.sleep(max(0.0, pause - (time.time() - t1)))
                game.reset()
                continue
            await asyncio.sleep(max(0.0, game.tick - (time.time() - t0)))
    except _Quit:
        return game.score_text()
    finally:
        if tenda:
            await tenda.close()


def play(game):
    """Avvia un gioco. Il gioco deve avere: title, help, tick, over, key(k), step(),
    pixels(), end_animation() (generatore di pause in secondi), reset(), score_text()."""
    result = curses.wrapper(lambda scr: asyncio.run(_run(scr, game)))
    print(f"Partita finita. Punti: {result}")
