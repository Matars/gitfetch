# Color Configuration

gitfetch uses ANSI color codes for terminal output. Colors can be customized in the `[COLORS]` section of the config file.

## Available Colors

The following color keys can be customized:

### Text Formatting

- `reset`: Reset all formatting
- `bold`: Bold text
- `dim`: Dimmed text

### Basic Colors

- `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`

### Special Colors

- `orange`: Orange color
- `accent`: Accent color for highlights
- `header`: Header text color
- `muted`: Muted text color

### Contribution Graph Colors (0-4)

- `0`: Lowest contribution level
- `1`: Low contribution level
- `2`: Medium contribution level
- `3`: High contribution level
- `4`: Highest contribution level

## Configuration

Colors use ANSI escape codes. Examples:

```ini
[COLORS]
reset = \033[0m
bold = \033[1m
red = \033[91m
green = \033[92m
blue = \033[94m
header = \033[38;2;118;215;161m
0 = \033[48;5;238m
1 = \033[48;5;28m
```

## ANSI Color Codes

- `\033[0m`: Reset
- `\033[1m`: Bold
- `\033[2m`: Dim
- `\033[91m`: Bright Red
- `\033[92m`: Bright Green
- `\033[93m`: Bright Yellow
- `\033[94m`: Bright Blue
- `\033[95m`: Bright Magenta
- `\033[96m`: Bright Cyan
- `\033[97m`: Bright White

For 256-color codes, use `\033[38;5;{color_code}m` for foreground or `\033[48;5;{color_code}m` for background.

For RGB colors, use `\033[38;2;{r};{g};{b}m` for foreground or `\033[48;2;{r};{g};{b}m` for background.
