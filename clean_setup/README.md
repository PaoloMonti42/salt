# Plug and play instructions

The files in this folder should allow you to use the tool out of the box.

Since some files are of considerable size, I couldn't upload them on the repository. To get everything ready, execute `./pull.sh`.

In one terminal, run `./qemu.sh`.  This will boot the kernel inside the VM.

Here is a little checklist of things you might want to change:
* Login information: I made an username called *user* with password *password*. The *root* account has no password.
* Language: change with `update-locale`.
* keyboard layout: change with `sudo dpkg-reconfigure keyboard-configuration`.
* Timezone: change with `timedatectl`.

In another window, run gdb. Important commands are located in the *.gdbinit*  file, so make sure it gets executed, or run them yourself.

At this point, we can test that everything is working properly by executing `tbreak defaul_idle` (or any known frequent function) and then `continue`. The breakpoint should be hit very quickly, unless you just booted the system: in that case it will be busy for a bit checking packages.
