#!/bin/bash

echo "=== Essential Commands to Identify Your Touchpad ==="
echo

echo "Running essential commands to identify your touchpad device..."
echo

echo "1. xinput list (shows all input devices):"
xinput list
echo

echo "2. Check for specific touchpad identifiers:"
grep -i "touchpad\|elan\|synaptics\|alps\|finger" <<< "$(xinput list)"
echo

echo "3. List input event devices:"
ls -la /dev/input/event*
echo

echo "4. Kernel messages related to input devices:"
dmesg | grep -i "input\|touchpad\|elan\|synaptics\|i2c\|hid"
echo

echo "5. Hardware information for input devices:"
lshw -class input 2>/dev/null
echo

echo "=== Results saved to touchpad_info.txt ==="