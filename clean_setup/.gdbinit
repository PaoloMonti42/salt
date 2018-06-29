# The following lines are the bare minimum to get the connection working.
# Remember to edit the file names if you renamed anything

set architecture i386:x86-64:intel
target remote localhost:1234
add-symbol-file vmlinux-4.4.0-87-generic 0

# The rest of this file is just convenience commands I usually run everytime.
# Mileage might vary based on your activity

# This allows gdb's list to find the kernel source files even if they are not in the expected path. Change accordingly to your file system
set substitute-path /build/linux-5EyXrQ/linux-4.4.0 src/linux-4.4

set disassembly-flavor intel

# This prevents gdb from truncating long lists or strings.
set print elements 0

# Set a one-time breakpoint at default_idle, then run until it's hit
tbreak default_idle
continue
