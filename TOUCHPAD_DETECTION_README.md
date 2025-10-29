# Touchpad Detection Scripts

These scripts will help you identify your touchpad device on Fedora Linux for your Lenovo ThinkPad P15 Gen 2.

## Scripts included:

1. `essential_touchpad_detect.sh` - Runs the most important commands to identify your touchpad
2. `detect_input_devices.sh` - Runs comprehensive detection commands

## How to use:

1. Make the script executable:
   ```bash
   chmod +x script_name.sh
   ```

2. Run the script:
   ```bash
   ./script_name.sh
   ```

3. Save the output to share with support communities:
   ```bash
   ./script_name.sh > touchpad_output.txt
   ```

## Key information to look for:

- Any device with "touchpad", "elan", "synaptics", "alps", or "finger" in the name
- Input event devices that might correspond to your touchpad
- Kernel messages related to input devices during boot

The output will help you identify:
- Whether the system recognizes your touchpad at all
- What type of touchpad is installed (ELAN, Synaptics, etc.)
- What kernel drivers might be needed