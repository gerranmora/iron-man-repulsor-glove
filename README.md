# Iron Man Repulsor Glove

RP2040 PropMaker-based gesture-controlled Iron Man repulsor glove with motion-activated LEDs and sound effects.

![CircuitPython](https://img.shields.io/badge/CircuitPython-9.x%20%7C%2010.x-blueviolet)
![Hardware](https://img.shields.io/badge/Hardware-RP2040-green)

## Features

- 🎭 **Gesture Control** - Raise arm to activate, lower to deactivate
- 💥 **Blast Effect** - Thrust palm forward for repulsor blast
- 🎨 **LED Effects** - Smooth fade animations and blast flicker
- 🔊 **High-Quality Audio** - I2S audio with custom sound effects
- ⚡ **Easy to Build** - Screw terminals, no complex wiring

## Hardware Requirements

- **Adafruit RP2040 Prop-Maker Feather** ([#5768](https://www.adafruit.com/product/5768))
- **NeoPixel Ring - 8 LEDs** ([#1463](https://www.adafruit.com/product/1463))
- **8Ω Mini Oval Speaker** ([#3923](https://www.adafruit.com/product/3923))
- **LiPo Battery** (1200-2200mAh recommended)
- **Wire** (22-24 AWG)

**Total Cost:** ~$60-75

## Quick Start

### 1. Install CircuitPython

1. Download CircuitPython from [circuitpython.org](https://circuitpython.org/board/adafruit_feather_rp2040_prop_maker/)
2. Hold BOOT button, plug in USB
3. Drag .UF2 file to RPI-RP2 drive
4. Board reboots as CIRCUITPY

### 2. Install Libraries

Download the [CircuitPython Library Bundle](https://circuitpython.org/libraries) and copy these to `CIRCUITPY/lib/`:

- `neopixel.mpy`
- `adafruit_lis3dh.mpy`
- `adafruit_debouncer.mpy`
- `simpleio.mpy`
- `adafruit_pixelbuf.mpy`
- `adafruit_ticks.mpy`
- `adafruit_bus_device/` (entire folder)

### 3. Copy Files

1. Copy `code.py` to CIRCUITPY root
2. Copy `sounds/` folder to CIRCUITPY
3. Board will auto-restart

### 4. Wire Hardware

Connect to RP2040 Prop-Maker screw terminals:

```
NeoPixel Ring:
  5V + Data → NEO terminal (both wires together)
  GND → GND terminal

Speaker:
  + → SPK+
  - → SPK-

Battery:
  JST connector → Battery port
```

## How to Use

1. **Raise your arm** (palm up) → Repulsor activates with fade-on animation
2. **Lower your arm** → Repulsor deactivates with fade-off animation
3. **Thrust palm forward hard** → Fire blast with flickering effect

## Configuration

Edit settings at the top of `code.py`:

```python
# LED Configuration
NUM_PIXELS = 8
REPULSOR_COLOR = (255, 255, 255)  # White
LED_BRIGHTNESS = 0.8

# Motion Sensitivity
ANGLE_THRESHOLD = 35  # Arm angle to activate
BLAST_ACCELERATION = 6.5  # Forward thrust threshold

# Timing
FADE_DURATION = 500  # milliseconds
BLAST_DURATION = 1500  # milliseconds
```

### Adjusting Blast Sensitivity

- **Too easy to trigger?** Increase `BLAST_ACCELERATION` (try 7.5)
- **Too hard to trigger?** Decrease `BLAST_ACCELERATION` (try 5.5)
- Watch serial monitor to see your X acceleration values

## Sound Files

Place WAV files in `CIRCUITPY/sounds/`:

- `0_blast.wav` - Repulsor blast/firing sound
- `1_powerup.wav` - Activation sound
- `2_powerdown.wav` - Deactivation sound

**Audio Requirements:**
- Format: WAV (16-bit PCM)
- Sample Rate: 22050 Hz or 44100 Hz
- Channels: Mono

## Troubleshooting

### Blast triggering constantly
- Increase blast threshold in code (line ~192)
- Currently set to 6.5, try 7.5 or 8.0

### Blast won't trigger
- Decrease blast threshold (try 5.5 or 5.0)
- Watch serial monitor during thrust to see X values
- Make sure repulsor is ON (LEDs lit)

### No sound
- Verify WAV files are in `/sounds/` folder
- Check files are proper WAV format (not renamed MP3)
- Check speaker wiring to SPK+/SPK-

### LEDs backwards
- Angle logic is pre-configured for typical orientation
- If behavior is inverted, check lines 255-265

## Project Origin

This project combines:
- **Hardware platform:** Adafruit RP2040 Prop-Maker Lightsaber
- **Gesture behavior:** ESP32 Wireless Repulsor Glove concept
- **Custom tuning:** Optimized for ease of use and reliability

## License

MIT License - feel free to modify and share!

## Credits

- **Hardware:** Adafruit Industries
- **Concept:** plentifulprops3d (ESP32 repulsor glove)
- **Implementation:** Custom CircuitPython adaptation

---

**May your arc reactor never run out of power!** ⚡🦾
