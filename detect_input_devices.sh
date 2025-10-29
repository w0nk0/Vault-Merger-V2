#!/bin/bash

echo "=== Detecting Input Devices on Your System ==="
echo

echo "1. Listing all input devices recognized by the system:"
echo "------------------------------------------------------"
xinput list
echo

echo "2. Checking for input devices via /dev/input:"
echo "----------------------------------------------"
ls -la /dev/input/
echo

echo "3. Looking specifically for touchpad devices:"
echo "----------------------------------------------"
xinput list | grep -i "touchpad\|ELAN\|Synaptics\|ALPS\|Finger"
echo

echo "4. Checking event devices for touchpad signatures:"
echo "---------------------------------------------------"
for device in /dev/input/event*; do
    if xinput list-props $(xinput list | grep -o "id=[0-9]*" | head -1 | cut -d'=' -f2) 2>/dev/null; then
        echo "Checking device: $device"
        xinput list-props $(basename $device | sed 's/event//' | grep -o '[0-9]*')
    fi
done
echo

echo "5. Alternative method using libinput debug events (if available):"
echo "------------------------------------------------------------------"
if command -v libinput &> /dev/null; then
    echo "Available"
    which libinput
else
    echo "libinput not installed - you may want to install it with: sudo dnf install libinput"
fi
echo

echo "6. Checking system hardware information for input devices:"
echo "------------------------------------------------------------"
lshw -class input
echo

echo "7. Kernel messages related to input devices:"
echo "---------------------------------------------"
dmesg | grep -i "input\|touchpad\|elan\|synaptics"
echo

echo "8. Checking for I2C devices (some touchpads use I2C interface):"
echo "----------------------------------------------------------------"
ls -la /sys/bus/i2c/devices/
echo

echo "=== End of Detection Commands ==="
echo
echo "Save this output and share it with Fedora support communities."