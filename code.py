# SPDX-FileCopyrightText: 2025 Iron Man Repulsor Glove - RP2040 PropMaker
# SPDX-License-Identifier: MIT
#
# RP2040 PropMaker Repulsor Glove
# Combines the hardware architecture of Adafruit's Lightsaber with
# the behavior of the ESP32 Wireless Repulsor Glove

import time
import os
import random
import math
import board
import pwmio
import audiocore
import audiobusio
from adafruit_debouncer import Button
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import adafruit_lis3dh
import simpleio

# ============================================================================
# CONFIGURATION - Customize these values
# ============================================================================

# LED Configuration
NUM_PIXELS = 7  # Number of NeoPixels in your repulsor ring
REPULSOR_COLOR = (255, 255, 255)  # White (Iron Man classic)
BLAST_COLOR = (255, 200, 0)  # Yellow/orange for blast effect
LED_BRIGHTNESS = 0.8

# Motion Detection Sensitivity
ANGLE_THRESHOLD = 35  # Degrees - arm angle to activate (lower = more sensitive)
BLAST_ACCELERATION = 0.5  # Forward thrust detection (positive for this board orientation)
BLAST_Y_ANGLE_MAX = 45  # Maximum Y angle for blast detection
BLAST_Z_ANGLE_MAX = 30  # Maximum Z angle for blast detection
MOVEMENT_THRESHOLD = 0.8  # Smoothing threshold for angle changes

# Timing Configuration
FADE_DURATION = 500  # milliseconds for fade on/off
BLAST_DURATION = 1500  # milliseconds for blast effect
BLAST_COOLDOWN = 1000  # milliseconds between blasts
ANGLE_CHECK_INTERVAL = 50  # milliseconds between angle checks

# Button Press Thresholds (milliseconds)
LONG_PRESS_THRESHOLD = 1000  # 1 second
VERY_LONG_PRESS_THRESHOLD = 5000  # 5 seconds
EXTRA_LONG_PRESS_THRESHOLD = 8000  # 8 seconds

# Color Options (for color changing mode)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
WHITE = (255, 255, 255)
ORANGE = (255, 128, 0)
COLORS = [WHITE, RED, BLUE, CYAN, YELLOW, GREEN, PURPLE, ORANGE]

# ============================================================================
# HARDWARE SETUP
# ============================================================================

# Enable external power pin for external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# Load all WAV files from sounds directory
wavs = []
for filename in os.listdir('/sounds'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/sounds/" + filename)
wavs.sort()
print("Sound files loaded:")
print(wavs)
print(f"Total sound files: {len(wavs)}")

# Audio setup using I2S
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

def play_wav(num, loop=False):
    """
    Play a WAV file from the sounds directory
    :param num: Index of the WAV file to play
    :param loop: If True, sound will loop until interrupted
    """
    try:
        n = wavs[num]
        wave_file = open(n, "rb")
        wave = audiocore.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except Exception as e:
        print(f"Error playing sound {num}: {e}")
        return

# External button setup
button_pin = DigitalInOut(board.EXTERNAL_BUTTON)
button_pin.direction = Direction.INPUT
button_pin.pull = Pull.UP
button = Button(button_pin, long_duration_ms=LONG_PRESS_THRESHOLD)

# External NeoPixels setup
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, NUM_PIXELS, auto_write=True)
pixels.brightness = LED_BRIGHTNESS

# Onboard LIS3DH accelerometer setup
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

# RGB LED in button (optional, for status indication)
red_led = pwmio.PWMOut(board.D10)
green_led = pwmio.PWMOut(board.D11)
blue_led = pwmio.PWMOut(board.D12)

def set_rgb_led(color):
    """Set the color of the RGB LED inside the button"""
    red_led.duty_cycle = int(simpleio.map_range(color[0], 0, 255, 65535, 0))
    green_led.duty_cycle = int(simpleio.map_range(color[1], 0, 255, 65535, 0))
    blue_led.duty_cycle = int(simpleio.map_range(color[2], 0, 255, 65535, 0))

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class RepulsorState:
    """States for the repulsor glove"""
    OFF = "off"
    FADING_ON = "fading_on"
    ON = "on"
    FADING_OFF = "fading_off"
    BLAST = "blast"
    ALWAYS_ON = "always_on"
    COLOR_CHANGE = "color_change"
    SHUTDOWN = "shutdown"

# Initial state
current_state = RepulsorState.OFF
color_index = 0  # Start with WHITE
current_color = COLORS[color_index]

# Timing variables
fade_start_time = 0
blast_start_time = 0
last_angle_check_time = 0
last_blast_time = 0
button_press_start_time = 0

# Motion filtering
angle_buffer = [0] * 20
buffer_index = 0
last_filtered_angle = 0

# Flags
blast_triggered = False

# ============================================================================
# MOTION PROCESSING
# ============================================================================

def calculate_moving_average(new_value):
    """Calculate moving average for smooth angle detection"""
    global buffer_index
    angle_buffer[buffer_index] = new_value
    buffer_index = (buffer_index + 1) % len(angle_buffer)
    return sum(angle_buffer) / len(angle_buffer)

def check_blast_gesture():
    """
    ULTRA SIMPLE blast detection - just X acceleration
    """
    global blast_triggered, last_blast_time
    
    # Only check if repulsor is ON
    if current_state != RepulsorState.ON:
        return False
    
    # Skip if already blasting
    if blast_triggered:
        return False
    
    # Check cooldown
    current_time = time.monotonic() * 1000
    if current_time - last_blast_time < BLAST_COOLDOWN:
        return False
    
    # Get X acceleration
    x, y, z = lis3dh.acceleration
    
    # Simple check - just X value
    if x > 6.5:
        print(f">>> BLAST DETECTED! X was {x:.2f}")
        return True
    
    return False

def check_arm_angle():
    """
    Check if arm is raised to activate/deactivate repulsor
    Returns: 'raise' if arm raised, 'lower' if arm lowered, None otherwise
    """
    global last_filtered_angle, last_angle_check_time
    
    current_time = time.monotonic() * 1000
    
    if current_time - last_angle_check_time < ANGLE_CHECK_INTERVAL:
        return None
    
    last_angle_check_time = current_time
    
    # Get accelerometer data
    x, y, z = lis3dh.acceleration
    
    # Calculate arm angle
    angle = math.atan2(y, z) * 180 / math.pi
    filtered_angle = calculate_moving_average(angle)
    
    # Check for significant angle change
    if abs(filtered_angle - last_filtered_angle) < MOVEMENT_THRESHOLD:
        return None
    
    result = None
    
    # Arm raised above threshold
    if filtered_angle <= ANGLE_THRESHOLD and current_state == RepulsorState.OFF:
        result = 'raise'
        print(f"Arm raised: {filtered_angle:.1f}°")
    
    # Arm lowered below threshold
    elif filtered_angle > ANGLE_THRESHOLD and current_state == RepulsorState.ON:
        result = 'lower'
        print(f"Arm lowered: {filtered_angle:.1f}°")
    
    last_filtered_angle = filtered_angle
    return result

# ============================================================================
# LED EFFECTS
# ============================================================================

def update_leds():
    """Update LED state based on current repulsor state"""
    global fade_start_time, blast_start_time, current_state, blast_triggered
    
    current_time = time.monotonic() * 1000
    
    if current_state == RepulsorState.OFF:
        pixels.fill((0, 0, 0))
        pixels.show()
    
    elif current_state == RepulsorState.FADING_ON:
        elapsed = current_time - fade_start_time
        if elapsed < FADE_DURATION:
            # Calculate brightness based on fade progress
            brightness = int((elapsed / FADE_DURATION) * 255)
            color = tuple(int(c * brightness / 255) for c in current_color)
            pixels.fill(color)
            pixels.show()
        else:
            # Fade complete
            pixels.fill(current_color)
            pixels.show()
            current_state = RepulsorState.ON
            print("Repulsor fully charged")
    
    elif current_state == RepulsorState.ON or current_state == RepulsorState.ALWAYS_ON:
        pixels.fill(current_color)
        pixels.show()
    
    elif current_state == RepulsorState.FADING_OFF:
        elapsed = current_time - fade_start_time
        if elapsed < FADE_DURATION:
            # Calculate brightness based on fade progress
            brightness = 255 - int((elapsed / FADE_DURATION) * 255)
            color = tuple(int(c * brightness / 255) for c in current_color)
            pixels.fill(color)
            pixels.show()
        else:
            # Fade complete
            pixels.fill((0, 0, 0))
            pixels.show()
            current_state = RepulsorState.OFF
            print("Repulsor powered down")
    
    elif current_state == RepulsorState.BLAST:
        elapsed = current_time - blast_start_time
        if elapsed < BLAST_DURATION:
            # Flickering blast effect
            for i in range(NUM_PIXELS):
                flicker = random.randint(100, 150)
                if random.randint(0, 2) == 0:
                    # Occasional orange/yellow flicker
                    pixels[i] = (flicker, flicker // 2, 0)
                else:
                    # White with flicker
                    pixels[i] = (flicker, flicker, flicker)
            pixels.show()
            time.sleep(0.05)
        else:
            # Blast complete, return to ON state
            blast_triggered = False
            current_state = RepulsorState.ON
            pixels.fill(current_color)
            pixels.show()
            print("Blast complete")

# ============================================================================
# BUTTON HANDLING
# ============================================================================

def handle_button():
    """Process button presses and update state accordingly"""
    global button_press_start_time, current_state, color_index, current_color
    
    button.update()
    current_time = time.monotonic() * 1000
    
    # Detect button press start
    if button.pressed and button_press_start_time == 0:
        button_press_start_time = current_time
    
    # Detect button release and calculate press duration
    if button.released and button_press_start_time > 0:
        press_duration = current_time - button_press_start_time
        button_press_start_time = 0
        
        print(f"Button press duration: {press_duration}ms")
        
        # Extra long press: Future feature (mode switching, etc.)
        if press_duration >= EXTRA_LONG_PRESS_THRESHOLD:
            print("Extra long press detected - Reserved for future features")
            # Could add wireless mode switching here
        
        # Very long press: Toggle ALWAYS_ON mode
        elif press_duration >= VERY_LONG_PRESS_THRESHOLD:
            if current_state == RepulsorState.ALWAYS_ON:
                current_state = RepulsorState.OFF
                print("Exiting ALWAYS_ON mode")
            else:
                current_state = RepulsorState.ALWAYS_ON
                pixels.fill(current_color)
                pixels.show()
                print("Entering ALWAYS_ON mode")
        
        # Long press: Enter color change mode
        elif press_duration >= LONG_PRESS_THRESHOLD:
            if current_state != RepulsorState.COLOR_CHANGE:
                audio.stop()
                play_wav(3, loop=True)  # Color change mode sound
                current_state = RepulsorState.COLOR_CHANGE
                print("Entering color change mode")
            else:
                # Exit color change mode
                audio.stop()
                current_state = RepulsorState.OFF
                print("Exiting color change mode")
        
        # Short press: Power on/off or cycle colors
        else:
            if current_state == RepulsorState.COLOR_CHANGE:
                # Cycle through colors
                color_index = (color_index + 1) % len(COLORS)
                current_color = COLORS[color_index]
                pixels.fill(current_color)
                pixels.show()
                set_rgb_led(current_color)
                print(f"Color changed to index {color_index}")
            else:
                # Manual power toggle
                print("Short press - Manual toggle")

# ============================================================================
# MAIN LOOP
# ============================================================================

print("=" * 50)
print("RP2040 PropMaker Repulsor Glove")
print("=" * 50)
print(f"Number of LEDs: {NUM_PIXELS}")
print(f"Angle threshold: {ANGLE_THRESHOLD}°")
print(f"Blast acceleration: {BLAST_ACCELERATION}")
print("Ready!")
print()

# Initialize
set_rgb_led(current_color)
pixels.fill((0, 0, 0))
pixels.show()

while True:
    # Update button state
    handle_button()
    
    # Skip motion detection in certain states
    if current_state in [RepulsorState.COLOR_CHANGE, RepulsorState.SHUTDOWN]:
        continue
    
    # Check for arm angle changes (raise/lower)
    if current_state not in [RepulsorState.ALWAYS_ON, RepulsorState.BLAST]:
        arm_motion = check_arm_angle()
        
        if arm_motion == 'raise':
            # Activate repulsor
            play_wav(1, loop=False)  # Power-up sound
            fade_start_time = time.monotonic() * 1000
            current_state = RepulsorState.FADING_ON
            print("Repulsor activating...")
        
        elif arm_motion == 'lower':
            # Deactivate repulsor
            play_wav(2, loop=False)  # Power-down sound
            fade_start_time = time.monotonic() * 1000
            current_state = RepulsorState.FADING_OFF
            print("Repulsor deactivating...")
    
    # DEBUG: Show X acceleration when repulsor is ON
    if current_state == RepulsorState.ON:
        x_debug, y_debug, z_debug = lis3dh.acceleration
        print(f"X: {x_debug:.2f}")
    
    # Check for blast gesture when repulsor is active
    if check_blast_gesture():
        blast_triggered = True
        blast_start_time = time.monotonic() * 1000
        last_blast_time = blast_start_time
        current_state = RepulsorState.BLAST
        play_wav(0, loop=False)  # Blast sound
        print("BLAST!")
    
    # Update LED effects
    update_leds()
    
    # Small delay to prevent overwhelming the CPU
    time.sleep(0.01)
