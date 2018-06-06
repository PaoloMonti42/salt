# Preparing the working environment

## Table of contents
* [Setting up the VM](#setting-up-the-vm)
    * [Quality of life improvements](#quality-of-life-improvements)
* [Connecting to gdb](#connecting-to-gdb)

My choice was to employ a Virtual Machine under the QEMU virtualizer.

At this point, there are three options:
* You have already been working of this topic and have your own setup. That's alright, just make sure that gdb can connect and control the kernel from the outside, and that debugging symbols are loaded.

* You can follow the procedure described in the rest of this document. That will allow you to get started from scratch and possibly tune the parameters along the way.

* You can just use the clean setup I prepared in the [clean_setup](../clean_setup) directory. This is recommended for both speed and reliability: more information on how to get started is in the folder README.

## Setting up the VM

Disclaimer: this is not guaranteed to be the best procedure: the following is the just the list of instructions that brought me to the first working result, stripped of all the unsuccessful tries and failures. There might be, and there probably is, a cleaner, more optimized series of steps: I'm just sharing mine because I know that it works as a whole.


Download the Ubuntu Server 16.04.3 LTS image from [the official website](https://www.ubuntu.com/download/server) (careful, it might not be the latest version anymore) or just
```
$ wget http://releases.ubuntu.com/16.04.3/ubuntu-16.04.3-server-amd64.iso
```

Create a hard disk image for the VM. I gave it 10 GB of space but 5 are probably more than enough.
```
$ sudo apt install qemu-utils
$ qemu-img create -f qcow2 ubuntu.img 10G
```

Then, launch qemu with the downloaded iso (make sure to change the name of the file if you have something different) and follow the installation process. **Do not** enable LVM when partitioning the disk or some commands in this guide will not work.
The -m 1024 option gives the machine 1GB of RAM.
```
$ sudo apt install qemu-system-x86
$ qemu-system-x86_64 -hda ubuntu.img -cdrom ubuntu-16.04.3-server-amd64.iso -m 1024
 ```

The SLUB allocator is default for this distribution, so we don't need to make any changes in the configuration.


### Quality of life improvements

At this point, the bare minimum setup is done, but working in this state might be a bit unpractical. Starting Qemu with the graphical interface, having to continuously hook and unhook the mouse and not having the possibility to share files is cumbersome to say the least.
For this reason, the next steps are designed as a quality of life improvement, but are not necessary for the tool to work.

First of all, we want to have the kernel image so that we can bypass GRUB, and easily disable kaslr and the graphical interface.
The file is located at `/boot/vmlinuz-4.4.0-87-generic` in the VM, so any method to retrieve it works.

One way to do it is to use the libguestfs toolset to mount the disk image and copy back the file.
```
$ sudo apt install libguestfs-tools
$ mkdir /tmp/kernel; sudo guestmount -a ubuntu.img -m /dev/sda1 /tmp/kernel
$ sudo cp /tmp/kernel/boot/vmlinuz-4.4.0-87-generic .
$ sudo chmod +r vmlinuz-4.4.0-87-generic
$ sudo guestunmount /tmp/kernel
```

The last step allows to enable a ssh connection from the host machine to the VM. This makes it more convenient to share files through scp and also avoids *accidental* Ctrl-Cs that would close Qemu.
From inside the VM, make sure that `sshd` is up by running
```
$ sudo apt-get install openssh-server
$ sudo service sshd restart
```

The setup is complete. The VM can be started from now on with the following command:
```
$ qemu-system-x86_64 \
-hda ubuntu.img -m 1024 \
-kernel vmlinuz-4.4.0-87-generic \
-append "root=/dev/sda1 nokaslr console=ttyS0" \
-nographic -monitor /dev/null \
-net nic -net user,hostfwd=tcp::2223-:22 \
-s
```
The `-kernel` option boots the system with a given kernel, bypassing GRUB.
The following line mounts the root home directory, disables kaslr and connects the console to the host machine terminal.
The rest of the command disables the graphical interface, enables an ssh tunnel through port 2223. Finally, `-s` opens a gdb server and connects it to port 1234.

After the system has booted, one can login directly from the VM console, or ssh into the machine from another terminal with `ssh user@localhost -p 2223`.

This should conclude the part about setting up the kernel. The procedure is long but it should be a one time thing. Creating a backup at this point is always recommended, so that resetting is not going to be as painful.

## Connecting to gdb

As a last piece, we need the debugging symbols for the kernel. If using a different kernel, check the version with `uname -a` and adjust the commands accordingly.
```
$ wget http://ddebs.ubuntu.com/pool/main/l/linux/linux-image-4.4.0-87-generic-dbgsym_4.4.0-87.110_amd64.ddeb
$ mkdir /tmp/symbols; dpkg -x linux-image-4.4.0-87-generic-dbgsym_4.4.0-87.110_amd64.ddeb /tmp/symbols
$ cp /tmp/symbols/usr/lib/debug/boot/vmlinux-4.4.0-87-generic .
```

Now we can finally put the everything together.
After having started qemu and let the kernel boot up, open gdb in another terminal.
The following commands enable communication between the debugger and the target system.
```
set architecture i386:x86-64:intel
target remote localhost:1234
add-symbol-file vmlinux-4.4.0-87-generic 0
```
At this point, we can test that everything is working properly by executing `tbreak defaul_idle` (or any known frequent function) and then `continue`. The breakpoint should be hit very quickly, unless you just booted the system: in that case it will be busy for a bit checking packages.
