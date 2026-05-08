---
name: ascii-animator
description: Expert ASCII animation system for terminal/CLI applications. Create terminal animations as standalone shell scripts (bash + awk) with zero dependencies. Supports splash screens, loading sequences, text effects, matrix rain, 3D rotating objects, progress indicators, sprite animations, scene transitions, and interactive ASCII art. Use when the user asks to build terminal animations, ASCII art effects, CLI splash screens, animated banners, loading spinners, text reveal effects, or any visual animation rendered with ASCII/Unicode characters in the terminal.
license: Complete terms in LICENSE.txt
---

# ASCII Animator

Create professional ASCII animations as **standalone shell scripts** (bash + awk). Zero external dependencies — runs on any Unix terminal.

## Default Output: Shell Script

**Always generate `.sh` scripts unless user explicitly asks for Python/Node.js.** Scripts must:
- Use `#!/usr/bin/env bash` shebang
- Use `awk` for floating-point math and frame rendering (awk is ubiquitous)
- Be a single self-contained file
- Work on any terminal with ANSI support

Only use Python/Node.js if user explicitly requests it. See [references/animation-patterns.md](references/animation-patterns.md) for Python templates.

## Core Principles

1. **Terminal-native** - Render inline (not fullscreen). Use cursor-up `\033[<N>A` to overwrite frames, not alternate screen buffer. Animation lives in the normal terminal flow.
2. **Buffer output** - Build full frame in awk, print in single `printf`. No flicker.
3. **Clean exit** - `trap` on INT/TERM to restore cursor (`\033[?25h`) and reset colors (`\033[0m`).
4. **Fixed dimensions** - Render at a fixed size (e.g. 50x24) that fits any terminal. Do NOT fill the whole screen.
5. **Terminal background** - Never paint background color. Use the terminal's own black background. Only emit colored foreground characters and spaces.

## Shell Animation Template

```bash
#!/usr/bin/env bash
# Animation Name — one-line description
# Ctrl+C to exit.

cleanup() { printf '\033[?25h\033[0m\n'; exit 0; }
trap cleanup INT TERM

printf '\033[?25l'  # hide cursor

FRAME=0
while true; do
    # awk generates the full frame as a single string
    OUTPUT=$(awk -v frame="$FRAME" '
    BEGIN {
        W = 50; H = 24
        # ... rendering math here ...
        for (row = 0; row < H; row++) {
            line = ""
            for (col = 0; col < W; col++) {
                # compute character + color
                line = line ch
            }
            print line
        }
    }')

    # Overwrite previous frame (cursor up H lines)
    if [ "$FRAME" -gt 0 ]; then
        printf "\033[24A"
    fi
    printf '%s' "$OUTPUT"

    FRAME=$((FRAME + 1))
    sleep 0.05
done
```

## Rendering Rules

### Shading Ramps (dark to bright)
- Sphere/body: `.,:;+*#@`
- Ring/border: `.:=*#@`
- Letters/text: `+=*#%@` (always visible, skip dim chars)

### Color (foreground only, ANSI truecolor)
```
\033[38;2;R;G;Bm   # set foreground RGB
\033[0m             # reset
```
Never use `\033[48;2;...m` (background). Let terminal background show through.

### Frame Overwrite (NOT fullscreen)
```bash
# Move cursor up N lines to overwrite previous frame
printf "\033[${HEIGHT}A"
```
Do NOT use alternate screen buffer (`\033[?1049h`). Animation stays in normal scrollback.

### 3D Math in awk
```awk
# Rotate point (x,y,z) around Y axis by angle a
rx = x * cos(a) + z * sin(a)
ry = y
rz = -x * sin(a) + z * cos(a)

# Spherical UV mapping
u = 0.5 + atan2(rx, -rz) / (2 * 3.14159)
v = 0.5 + atan2(ry, sqrt(rx*rx + rz*rz)) / 3.14159

# Lighting (dot product with light direction)
dot = nx*lx + ny*ly + nz*lz
bright = max(0, 0.3 + dot * 0.7)
```

## Technical References

- **ANSI codes, Unicode blocks, color systems**: See [references/ansi-rendering.md](references/ansi-rendering.md)
- **Python/Node.js patterns (if explicitly requested)**: See [references/animation-patterns.md](references/animation-patterns.md)

## Quality Checklist

- [ ] Output is `.sh` file with `#!/usr/bin/env bash`
- [ ] Zero dependencies (only bash + awk)
- [ ] Fixed render size (not fullscreen)
- [ ] No background color painting (terminal black shows through)
- [ ] Cursor hidden during animation, restored on exit via trap
- [ ] Frame overwrite via cursor-up (not alternate buffer)
- [ ] Single `printf` per frame (no flicker)
- [ ] Ctrl+C exits cleanly
