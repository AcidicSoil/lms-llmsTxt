# ANSI Rendering Reference

## Table of Contents
1. [Cursor Control](#cursor-control)
2. [Screen Control](#screen-control)
3. [Text Styling](#text-styling)
4. [Color Systems](#color-systems)
5. [Unicode Block Characters](#unicode-block-characters)
6. [Rendering Techniques](#rendering-techniques)

## Cursor Control

| Sequence | Effect |
|----------|--------|
| `\033[H` | Cursor to home (0,0) |
| `\033[<r>;<c>H` | Cursor to row r, col c |
| `\033[<n>A` | Cursor up n lines |
| `\033[<n>B` | Cursor down n lines |
| `\033[<n>C` | Cursor forward n cols |
| `\033[<n>D` | Cursor backward n cols |
| `\033[s` | Save cursor position |
| `\033[u` | Restore cursor position |
| `\033[?25l` | Hide cursor |
| `\033[?25h` | Show cursor |

## Screen Control

| Sequence | Effect |
|----------|--------|
| `\033[2J` | Clear entire screen |
| `\033[0J` | Clear from cursor to end |
| `\033[1J` | Clear from cursor to start |
| `\033[2K` | Clear entire line |
| `\033[?1049h` | Switch to alternate screen buffer |
| `\033[?1049l` | Switch back to main screen buffer |

## Text Styling

| Sequence | Effect |
|----------|--------|
| `\033[0m` | Reset all attributes |
| `\033[1m` | Bold |
| `\033[2m` | Dim/faint |
| `\033[3m` | Italic |
| `\033[4m` | Underline |
| `\033[5m` | Slow blink |
| `\033[7m` | Reverse/invert |
| `\033[8m` | Hidden |
| `\033[9m` | Strikethrough |

## Color Systems

### 4-bit (16 colors)
```
Foreground: \033[30m-\033[37m (normal), \033[90m-\033[97m (bright)
Background: \033[40m-\033[47m (normal), \033[100m-\033[107m (bright)
```

### 8-bit (256 colors)
```
Foreground: \033[38;5;<n>m  (n = 0-255)
Background: \033[48;5;<n>m
  0-7:     Standard colors
  8-15:    Bright colors
  16-231:  6x6x6 RGB cube (16 + 36*r + 6*g + b)
  232-255: Grayscale (dark to light)
```

### 24-bit Truecolor
```
Foreground: \033[38;2;<r>;<g>;<b>m
Background: \033[48;2;<r>;<g>;<b>m
```

### Color Fallback Strategy
```python
def color_fg(r, g, b):
    """Truecolor with 256-color fallback."""
    if os.environ.get('COLORTERM') in ('truecolor', '24bit'):
        return f'\033[38;2;{r};{g};{b}m'
    # Map to 256-color cube
    ri, gi, bi = (round(c / 51) for c in (r, g, b))
    return f'\033[38;5;{16 + 36*ri + 6*gi + bi}m'
```

## Unicode Block Characters

### Drawing Blocks (Higher Resolution)
| Char | Code | Name |
|------|------|------|
| `\u2588` | Full block | Solid fill |
| `\u2584` | Lower half | Bottom half |
| `\u2580` | Upper half | Top half |
| `\u2591` | Light shade | 25% fill |
| `\u2592` | Medium shade | 50% fill |
| `\u2593` | Dark shade | 75% fill |
| `\u2596`-`\u259F` | Quadrant blocks | Quarter-cell precision |

### Braille Characters (Highest Resolution)
Unicode range `\u2800`-`\u28FF` (256 patterns). Each character is a 2x4 dot grid, giving 2x4 sub-pixel resolution per terminal cell.

```python
def braille_char(dots):
    """dots: list of (row, col) positions, row 0-3, col 0-1."""
    offsets = {(0,0):0x01, (1,0):0x02, (2,0):0x04, (0,1):0x08,
               (1,1):0x10, (2,1):0x20, (3,0):0x40, (3,1):0x80}
    code = 0x2800
    for dot in dots:
        code |= offsets.get(dot, 0)
    return chr(code)
```

### Box Drawing
| Range | Use |
|-------|-----|
| `\u2500`-`\u257F` | Lines, corners, T-junctions, crosses |
| `\u2550`-`\u256C` | Double-line variants |

## Rendering Techniques

### Double Buffering
```python
import io

def render_scene(objects):
    buf = io.StringIO()
    for obj in objects:
        buf.write(f'\033[{obj.y};{obj.x}H')
        buf.write(obj.render())
    frame = buf.getvalue()
    sys.stdout.write(frame)
    sys.stdout.flush()
```

### Differential Rendering
Only update cells that changed between frames:
```python
def diff_render(prev_grid, curr_grid):
    buf = io.StringIO()
    for y, (prev_row, curr_row) in enumerate(zip(prev_grid, curr_grid)):
        for x, (prev_cell, curr_cell) in enumerate(zip(prev_row, curr_row)):
            if prev_cell != curr_cell:
                buf.write(f'\033[{y+1};{x+1}H{curr_cell}')
    sys.stdout.write(buf.getvalue())
    sys.stdout.flush()
```

### Easing Functions
```python
import math

def ease_in_quad(t):    return t * t
def ease_out_quad(t):   return t * (2 - t)
def ease_in_out_quad(t): return 2*t*t if t < 0.5 else -1+(4-2*t)*t
def ease_out_bounce(t):
    if t < 1/2.75:   return 7.5625 * t * t
    elif t < 2/2.75:  t -= 1.5/2.75;   return 7.5625*t*t + 0.75
    elif t < 2.5/2.75: t -= 2.25/2.75; return 7.5625*t*t + 0.9375
    else:              t -= 2.625/2.75; return 7.5625*t*t + 0.984375
def ease_in_out_elastic(t):
    if t == 0 or t == 1: return t
    p = 0.3
    if t < 0.5:
        return -0.5 * (2**(20*t-10)) * math.sin((20*t-11.125)*(2*math.pi/p))
    return (2**(-20*t+10)) * math.sin((20*t-11.125)*(2*math.pi/p)) * 0.5 + 1
```

### Gradient Generation
```python
def gradient(color1, color2, steps):
    """Interpolate between two RGB tuples."""
    return [
        tuple(int(c1 + (c2-c1) * i / (steps-1)) for c1, c2 in zip(color1, color2))
        for i in range(steps)
    ]

def multi_gradient(colors, total_steps):
    """Multi-stop gradient."""
    segs = len(colors) - 1
    per_seg = total_steps // segs
    result = []
    for i in range(segs):
        n = per_seg if i < segs-1 else total_steps - len(result)
        result.extend(gradient(colors[i], colors[i+1], n))
    return result
```
