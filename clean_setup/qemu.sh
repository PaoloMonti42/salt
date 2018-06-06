# The `-kernel` option boots the system with a given kernel, bypassing GRUB.
# The following line mounts the root home directory, disables kaslr and connects the console to the host machine terminal.
# The rest of the command disables the graphical interface, enables an ssh tunnel through port 2223. Finally, `-s` opens a gdb server and connects it to port 1234.

qemu-system-x86_64 \
-hda ubuntu.img \
-m 1024 \
-kernel vmlinuz-4.4.0-87-generic \
-append "root=/dev/sda1 nokaslr console=ttyS0" \
-nographic -monitor /dev/null \
-net nic -net user,hostfwd=tcp::2223-:22 \
-s
