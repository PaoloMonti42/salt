#  Your own playground

This chapter will get you familiar with the *salt* kernel module. This little tool will allow you to have a playground at your disposal for better studying and understanding how dynamic allocation works in SLUB.

It's developed as a simple kernel driver that registers a new device, `/dev/salt`. The functions *open* and *close* have approximately the standard behavior, while *read* and *write* were not even implemented.

The crucial function that controls the device is ***ioctl***. Through it, the user can give commands to the module in order to generate events.

Given the prototype of the function, `static long handle_ioctl(struct file *f, unsigned int cmd, char* arg)`, these are the available commands:
* cmd #5: look for a cache whose name matches *arg*: if exists, allocate an object of that type, and print its address.
* cmd #6: list all allocated objects, and their address.
* cmd #7: free a user specified object. The user can choose allocated objects through an unique ID, referencing it with *arg*.
* cmd #8: free all allocated objects.

This is an example output of what the module can do. You can show its output through the `dmesg` command.

```
< opening the device >
[SALT] Salt init
< generating two allocations >
[SALT] Allocated an object from TCPv6 cache, at address ffff88003a151080, with ID 0
[SALT] Allocated an object from kmalloc-192 cache, at address ffff88003b5f8b40, with ID 1
< listing the allocations >
[SALT] Object from TCPv6 cache, at address ffff88003a151080, with ID 0
[SALT] Object from kmalloc-192 cache, at address ffff88003b5f8b40, with ID 1
< freeing an object >
[SALT] Freed an object from TCPv6 cache, at address ffff88003a151080, with ID 0
< generating another allocation>
[SALT] Allocated an object from inode_cache cache, at address ffff88001c111630, with ID 2
< freeing everything >
[SALT] Freed an object from kmalloc-192 cache, at address ffff88003b5f8b40, with ID 1
[SALT] Freed an object from inode_cache cache, at address ffff88001c111630, with ID 2
< closing the device >
[SALT] Salt cleanup

```


For convenience, I also developed an user-space application to control the driver. It sports a nice interface and a small menu. It also provides the ability to read and execute a list of commands from a file, saving the hassle of manually inputting the same (or slightly different) sequence of inputs every time.

This is an usage example. Since the kernel driver will only show its output through **printk**, keep `dmesg` open to see important information.

```
root@ubuntu:~# ./drive
0 - Exit
1 - Alloc
2 - List allocations
3 - Free
4 - Free all
5 - Execute commands from file
Choose the next action: 1
Enter the cache to allocate from: fuse_inode   

0 - Exit
1 - Alloc
2 - List allocations
3 - Free
4 - Free all
5 - Execute commands from file
Choose the next action: 3   
Enter the ID of the allocation to free: 0

0 - Exit
1 - Alloc
2 - List allocations
3 - Free
4 - Free all
5 - Execute commands from file
Choose the next action: 5
Enter the file path: test_file
Batch execution complete

0 - Exit
1 - Alloc
2 - List allocations
3 - Free
4 - Free all
5 - Execute commands from file
Choose the next action: 0
```

Of course the kernel module and the gdb plugin are completely separate entities, but keeping both open while working can prove very useful.  
You can generate specific allocations and put yourself in specific cases that would otherwise be very rare, in order to deeply understand what happens under those conditions, fixing an exploit or investigating why it works.
