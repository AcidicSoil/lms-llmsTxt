# Animation Patterns Reference

## Table of Contents
1. [Matrix Rain](#matrix-rain)
2. [Typewriter Effect](#typewriter-effect)
3. [Decrypt/Scramble Reveal](#decryptscramble-reveal)
4. [Splash Screen with FIGlet](#splash-screen-with-figlet)
5. [Particle System](#particle-system)
6. [Loading Spinner (Braille)](#loading-spinner-braille)
7. [Wave Text](#wave-text)
8. [Fire Effect](#fire-effect)
9. [Starfield](#starfield)
10. [Progress Bar with Animation](#progress-bar-with-animation)

---

## Matrix Rain

```python
import random, shutil, time, sys

def matrix_rain(duration=10, fps=15):
    w, h = shutil.get_terminal_size()
    columns = [0] * w
    chars = "abcdefghijklmnopqrstuvwxyz0123456789@#$%&"

    def gen_frames():
        for _ in range(duration * fps):
            lines = [[' '] * w for _ in range(h)]
            for x in range(w):
                if random.random() < 0.03:
                    columns[x] = 0
                if columns[x] < h:
                    y = columns[x]
                    trail_len = random.randint(5, 15)
                    for j in range(trail_len):
                        row = y - j
                        if 0 <= row < h:
                            c = random.choice(chars)
                            if j == 0:
                                lines[row][x] = f'\033[97m{c}\033[0m'
                            elif j < 3:
                                lines[row][x] = f'\033[92m{c}\033[0m'
                            else:
                                lines[row][x] = f'\033[32m{c}\033[0m'
                    columns[x] += 1
                    if columns[x] > h + 15:
                        columns[x] = 0
            yield '\n'.join(''.join(row) for row in lines)

    return gen_frames
```

## Typewriter Effect

```python
import time, sys, random

def typewriter(text, char_delay=0.05, line_delay=0.3, variance=0.02):
    """Print text with realistic typewriter timing."""
    if not sys.stdout.isatty():
        sys.stdout.write(text)
        return
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        if char == '\n':
            time.sleep(line_delay)
        elif char in '.!?':
            time.sleep(char_delay * 4)
        elif char == ',':
            time.sleep(char_delay * 2)
        else:
            time.sleep(char_delay + random.uniform(-variance, variance))
```

## Decrypt/Scramble Reveal

```python
import random, time, sys

def decrypt_reveal(text, fps=30, scramble_rounds=20):
    """Reveal text through random character scrambling."""
    chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?0123456789"
    revealed = [False] * len(text)
    display = list(text)

    for frame_i in range(scramble_rounds + len(text)):
        # Reveal 1-3 characters per frame
        unrevealed = [i for i, r in enumerate(revealed) if not r and text[i] != ' ']
        if unrevealed:
            for idx in random.sample(unrevealed, min(3, len(unrevealed))):
                if frame_i > scramble_rounds // 2 or random.random() < 0.1:
                    revealed[idx] = True

        # Scramble unrevealed characters
        for i in range(len(text)):
            if not revealed[i] and text[i] != ' ':
                display[i] = random.choice(chars)
            elif revealed[i]:
                display[i] = text[i]

        sys.stdout.write('\r' + ''.join(display))
        sys.stdout.flush()
        time.sleep(1 / fps)

        if all(revealed[i] or text[i] == ' ' for i in range(len(text))):
            break

    sys.stdout.write('\r' + text + '\n')
```

## Splash Screen with FIGlet

```python
import shutil

def splash_screen(title, subtitle="", font="slant"):
    """Generate a centered, gradient-colored splash screen."""
    try:
        import pyfiglet
        ascii_art = pyfiglet.figlet_format(title, font=font)
    except ImportError:
        ascii_art = title

    w, h = shutil.get_terminal_size()
    lines = ascii_art.rstrip().split('\n')

    # Center and apply gradient
    colors = [(0, 180, 255), (128, 0, 255), (255, 0, 128)]
    total = len(lines)

    frame_lines = []
    for i, line in enumerate(lines):
        t = i / max(total - 1, 1)
        if t < 0.5:
            t2 = t * 2
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t2)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t2)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t2)
        else:
            t2 = (t - 0.5) * 2
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * t2)
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * t2)
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * t2)

        padded = line.center(w)
        frame_lines.append(f'\033[38;2;{r};{g};{b}m{padded}\033[0m')

    if subtitle:
        frame_lines.append('')
        frame_lines.append(f'\033[2m{subtitle.center(w)}\033[0m')

    return '\n'.join(frame_lines)
```

## Particle System

```python
import random, math

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'char', 'color')

    def __init__(self, x, y, vx, vy, life, char='*', color=None):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.char = char
        self.color = color or '\033[97m'

    def update(self, dt, gravity=0.5):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += gravity * dt
        self.life -= dt
        return self.life > 0

class ParticleSystem:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.particles = []

    def emit(self, x, y, count=10, spread=2.0, chars='.*+'):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, spread)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 1.5,
                life=random.uniform(0.5, 2.0),
                char=random.choice(chars),
                color=f'\033[38;5;{random.choice([196,202,208,214,220,226])}m'
            ))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def render(self, grid):
        for p in self.particles:
            ix, iy = int(p.x), int(p.y)
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = p.color + p.char + '\033[0m'
```

## Loading Spinner (Braille)

```python
import sys, time, itertools

BRAILLE_SPINNER = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
DOT_SPINNER = ['⠁','⠂','⠄','⡀','⢀','⠠','⠐','⠈']
BAR_SPINNER = ['▏','▎','▍','▌','▋','▊','▉','█','▉','▊','▋','▌','▍','▎','▏']

def spinner(message="Loading", style=BRAILLE_SPINNER, duration=None):
    """Show animated spinner with message."""
    if not sys.stdout.isatty():
        sys.stdout.write(message + '...\n')
        return

    frames = itertools.cycle(style)
    start = time.time()
    sys.stdout.write('\033[?25l')  # hide cursor
    try:
        for frame in frames:
            elapsed = time.time() - start
            if duration and elapsed >= duration:
                break
            sys.stdout.write(f'\r\033[2K {frame} {message}')
            sys.stdout.flush()
            time.sleep(0.08)
    finally:
        sys.stdout.write('\r\033[2K\033[?25h')  # clear + show cursor
        sys.stdout.flush()
```

## Wave Text

```python
import math, time, sys, shutil

def wave_text(text, duration=5, fps=20, amplitude=1.5, frequency=0.3):
    """Animate text with sine wave motion."""
    w, h = shutil.get_terminal_size()
    center_y = h // 2

    sys.stdout.write('\033[?25l\033[?1049h')
    try:
        for frame_i in range(duration * fps):
            t = frame_i / fps
            buf = []
            for i, char in enumerate(text):
                offset = int(amplitude * math.sin(frequency * (i * 0.5 + t * 8)))
                y = center_y + offset
                x = (w // 2 - len(text) // 2) + i
                hue = int((i / len(text)) * 360)
                r, g, b = hsl_to_rgb(hue / 360, 0.8, 0.6)
                buf.append(f'\033[{y};{x}H\033[38;2;{r};{g};{b}m{char}')
            sys.stdout.write('\033[2J' + ''.join(buf) + '\033[0m')
            sys.stdout.flush()
            time.sleep(1 / fps)
    finally:
        sys.stdout.write('\033[?1049l\033[?25h')

def hsl_to_rgb(h, s, l):
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return int(r*255), int(g*255), int(b*255)
```

## Fire Effect

```python
import random, shutil

FIRE_PALETTE = [
    (0,0,0), (32,8,0), (64,16,0), (128,32,0),
    (192,64,0), (224,96,0), (255,128,0), (255,160,32),
    (255,192,64), (255,224,128), (255,240,192), (255,255,255)
]
FIRE_CHARS = ' .:-=+*#%@'

def fire_effect(width=None, height=None):
    """Generate frames for a fire simulation."""
    w, h = width or shutil.get_terminal_size()[0], height or 20
    buf = [[0.0]*w for _ in range(h)]

    while True:
        # Seed bottom row
        for x in range(w):
            buf[h-1][x] = random.uniform(0.6, 1.0) if random.random() < 0.6 else 0

        # Propagate upward with cooling
        new_buf = [[0.0]*w for _ in range(h)]
        for y in range(h-1):
            for x in range(w):
                samples = [buf[min(y+1,h-1)][max(x-1,0)],
                           buf[min(y+1,h-1)][x],
                           buf[min(y+1,h-1)][min(x+1,w-1)],
                           buf[min(y+2,h-1)][x]]
                avg = sum(samples) / len(samples)
                new_buf[y][x] = max(0, avg - random.uniform(0.01, 0.04))
        new_buf[h-1] = buf[h-1]
        buf = new_buf

        # Render
        lines = []
        for row in buf:
            line_chars = []
            for val in row:
                idx = int(val * (len(FIRE_PALETTE)-1))
                r, g, b = FIRE_PALETTE[idx]
                c = FIRE_CHARS[int(val * (len(FIRE_CHARS)-1))]
                line_chars.append(f'\033[38;2;{r};{g};{b}m{c}')
            lines.append(''.join(line_chars) + '\033[0m')
        yield '\n'.join(lines)
```

## Starfield

```python
import random, shutil

def starfield(speed=0.5, density=0.002):
    """3D starfield flying through space."""
    w, h = shutil.get_terminal_size()
    stars = []

    while True:
        # Spawn new stars at random depths
        if random.random() < density * w:
            stars.append({
                'x': random.uniform(-1, 1),
                'y': random.uniform(-1, 1),
                'z': 1.0
            })

        grid = [[' ']*w for _ in range(h)]
        surviving = []
        for s in stars:
            s['z'] -= speed * 0.02
            if s['z'] <= 0.01:
                continue
            surviving.append(s)

            sx = int((s['x']/s['z'] + 1) * w/2)
            sy = int((s['y']/s['z'] + 1) * h/2)
            if 0 <= sx < w and 0 <= sy < h:
                brightness = min(1.0, (1 - s['z']) * 2)
                if brightness > 0.7:
                    grid[sy][sx] = '\033[97m*\033[0m'
                elif brightness > 0.4:
                    grid[sy][sx] = '\033[37m+\033[0m'
                else:
                    grid[sy][sx] = '\033[90m.\033[0m'

        stars = surviving
        yield '\n'.join(''.join(row) for row in grid)
```

## Progress Bar with Animation

```python
import sys, time

def animated_progress(total, width=40, fill_char='\u2588', empty_char='\u2591'):
    """Animated progress bar with percentage, ETA, and color transition."""
    if not sys.stdout.isatty():
        return lambda current: None

    start_time = time.time()
    sys.stdout.write('\033[?25l')

    def update(current):
        pct = current / total
        filled = int(width * pct)

        # Color: red -> yellow -> green
        if pct < 0.5:
            r, g = 255, int(255 * pct * 2)
        else:
            r, g = int(255 * (1 - pct) * 2), 255

        bar = f'\033[38;2;{r};{g};0m' + fill_char*filled + empty_char*(width-filled) + '\033[0m'

        elapsed = time.time() - start_time
        eta = (elapsed / pct - elapsed) if pct > 0 else 0

        sys.stdout.write(f'\r {bar} {pct*100:5.1f}% | ETA {eta:.0f}s')
        sys.stdout.flush()

        if current >= total:
            sys.stdout.write('\033[?25h\n')

    return update
```
