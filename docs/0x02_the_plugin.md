# Using the ***salt*** plugin

## Table of contents
* [General functioning](#general-functioning)
    * [Filtering](#filtering)
    * [Recording](#recording)
    * [Tracing](#tracing)
    * [Walking](#walking)
* [Further work](#further-work)
 
From now on, it will assumed that you followed the setup in the previous chapter, or that you have your own working environment.

After opening gdb, connecting it to the kernel, and importing the symbol file, you can initialize the plugin by typing `source salt.py`.

All the commands in the tool are now available. Type `salt help` for a quick summary. Some more in-depth documentation is provided in the rest of this chapter.

## General functioning

salt works by putting breakpoints in specific functions in the kernel.  
In order to maximize compatibility with as many systems as possible, breakpoints are only inserted at the beginning or at the end of a function (*finish* breakpoints).
Placing them at a specific offset inside the function would be easier and more powerful, but that would only work when the assembly code is identical.
This isn't feasible given the amount of kernel and compiler variants.

When inside a kernel function, like the ones we're interested in, it's not possible to retrieve the corresponding user-space process by just looking at the backtrace.
Instead, a data structure inside the kernel is queried: the **current_task** variable.
Since on SMP systems there could be a different process running for each CPU, this makes it a *per-cpu-variable*.

Its value needs to be added to the corresponding **__per_cpu_offset** for the current processor (there is an array of one value per each core).
Once the final address is computed, we can look into the struct to find a lot of important information about the user-space task like name, PID, priority, etc.
The tool only reports information about name and PID, but this can be easily configured.

When the system requests the allocation of some dynamic memory, it always goes through **slab_alloc()**.
Sadly, this function is defined as *inline*, so determining its arguments and its caller is impossible by only placing a breakpoint inside of it.  
Going back one step, the kernel APIs that make use of this function are **kmem_cache_alloc** and **kmalloc**.

Albeit similar, I had to follow some different approaches for tracing the unfolding of those functions:
* kmem_cache_alloc -> luckily, this procedure already receives as an argument the address of the target cache to allocate to: every useful information can be gathered at the beginning. XXX return.

* kmalloc -> in this case, the caller does not specify (nor know) the target cache; it only passes the size of the desired object, and then the function computes the target cache through **kmalloc_slab()**. Information can only be retrieved at that point, so it's necessary to use a *finish* breakpoint at its return point. Also, in the case of preemption, some desynchronization can happen, so that needs to be handled.

Likewise, for deallocation functions:
* kmem_cache_free -> both the cache and the freed address are available at the beginning.

* kfree -> again, the function starts with no information about the target cache. It's computed later by **virt_to_head_page**, so another *finish* breakpoint is needed. Also, the plugin tries to filter out failed kfree attempts by looking at the value stored in the rdi register. If portability is a concern and such errors are not likely, that part can be removed.

I also added a breakpoint to trace the **new_slab** function, that notifies the user when a fresh slab is allocated. This can be useful for monitoring the memory usage of the system, or to set up the environment for an exploit (e.g. the overflow-into-free-object-metadata technique).

### Filtering

Filtering defines which SLUB events are notified to the user.

By default, the filter is disabled, so every allocation generates a message on the screen.
This can become quickly annoying and verbose when not interested in every single thing that the system does.  

For this reason, the ability to filter events is provided.
After having enabled filtering with `salt filter enable`, the user can add some criteria with `salt filter add ...`.  
At the moment, there are two possibilities:
* `salt filter add process foo`: when the 'foo' user-space task generates an allocation (or deallocation), the event goes through the filter.
* `salt filter add cache bar`: when the task generates an allocation (or deallocation) involving cache 'bar', the event goes through the filter.

Both command variations accept a list of targets separated by spaces.

Also, the user can select how to combine the two *subfilters*. By default they follow an **OR** relationship: an event that satisfies at least one of the criteria will go through the filter and generate a message.  
This behavior can be overridden by typing `salt filter relation OR/AND`.

A filtering criteria can be removed with `salt filter remove ...` and filtering can be disabled altogether with `salt filter disable` (criteria will be saved and applied the next time filtering will be re-enabled).

`salt filter status` displays the current state of filtering.

#### Example usage

```
> salt filter enable
Filtering enabled.
> salt filter add process sshd
Added 'sshd' to filtered processes.
> salt filter add cache kmalloc-4096
Added 'kmalloc-4096' to filtered caches.
> salt filter status
Filtering is on.
Tracing information will be displayed for the following processes: sshd
Tracing information will be displayed for the following caches: kmalloc-4096
Subfilter relation is set to AND.
> continue
...
kmem_cache_free is freeing from cache kmalloc-256 on behalf of process "sshd", pid 1022
kmem_cache_alloc is accessing cache kmalloc-4096 on behalf of process "gmain", pid 640
kmem_cache_free is freeing from cache kmalloc-4096 on behalf of process "gmain", pid 640
kmem_cache_alloc is accessing cache kmalloc-4096 on behalf of process "snapd", pid 689
kmem_cache_alloc is accessing cache kmalloc-256 on behalf of process "sshd", pid 1022
kmem_cache_free is freeing from cache kmalloc-512 on behalf of process "sshd", pid 1022
kmem_cache_free is freeing from cache kmalloc-4096 on behalf of process "snapd", pid 689
```

### Recording

Recording provides the ability to generate a *history* of SLUB events from a certain point in time to another.

Recording can be started by typing `salt record on` and stopped with `salt record off`.
The history is stored into a data structure and can be displayed with the `salt record show` command.

`salt record clear` clears the current history.
Starting a recording will not automatically clear the history, but append to it.

#### Example usage

```
> salt record on
Recording enabled.
> continue
...
> salt record off
Recording disabled.
> salt record show
('kmem_cache_alloc', 'kmalloc-4096', 'gmain', 640)
('kmalloc', 'kmalloc-192', 'kworker/u2:2', 17816)
('kmem_cache_alloc', 'mnt_cache', 'kworker/u2:2', 17816)
('kmem_cache_free' , 'blkdev_requests', 'kworker/u2:2', 17816)
```

### Tracing

Tracing is a convenience wrapper around filtering and recording.

When only interested in the activity generated by a single process, setting up the desired plugin environment every time can be cumbersome.

By typing `salt trace foobar`, the recording is cleared and started, the filtering is reset and enabled only for the 'foobar' process.
Additional rules can then be added through the previous commands.  
This can prove especially useful when developing an exploit or debugging a kernel module.

#### Example usage

```
> salt trace exploit
Tracing enabled.
> salt filter add cache kmalloc-256
Added 'kmalloc-256' to filtered caches.
> salt filter relation AND
Subfilter relation set to AND.
> salt filter status
Filtering is on.
Tracing information will be displayed for the following processes: exploit
Tracing information will be displayed for the following caches: kmalloc-2048
Subfilter relation is set to AND.
> continue
...
kmem_cache_alloc is accessing cache kmalloc-256 on behalf of process "exploit", pid 1087
kmem_cache_alloc is accessing cache kmalloc-256 on behalf of process "exploit", pid 1087
kmem_cache_alloc is accessing cache kmalloc-256 on behalf of process "exploit", pid 1087
kmem_cache_alloc is accessing cache kmalloc-256 on behalf of process "exploit", pid 1087
...
a new slab is being created for kmalloc-256 on behalf of process "exploit", pid 1087
```

### Walking

Walking refers to the process of gathering information about the state of the caches by navigating through the data structures stored in memory.

This process does not need any breakpoint, and is performed statically, on a halted system.
Starting from the **slab_caches** kernel variable, the command will reconstruct the linked list of all the system caches, retrieving data about their state, in particular the active slab.

Simply typing `salt walk` will navigate all the caches and show relevant information on the screen, in a human readable way.
The `salt walk_json` and `salt walk_html` variants format their output in the respective output.

Since information about *all* caches is rarely relevant, all the previous commands accept a list of cache names, separated by spaces, to use as a filter.

#### Example usage
```
> salt walk files_cache TCP
  --------------
 |             |
 |        slab_caches
 |             |
 |            ...
 |             |
 |             v
 |   name: TCP
 |   fist_free: 0xffff88003b66cf00
 |   freelist:  0xffff88003b66d680
 |              0xffff88003b66de00
 |              0xffff88003b66e580
 |              0xffff88003b66ed00
 |              0xffff88003b66f480
 |              0x0
 |   next: 0xffff88003e22ed00
 |             |
 |            ...
 |             |
 |             v
 |   name: files_cache
 |   fist_free: 0xffff88003e2ea840
 |   freelist:  0xffff88003e2eb8c0
 |              0xffff88003e2ea2c0
 |              0xffff88003e2eadc0
 |              0xffff88003e2ebb80
 |              0xffff88003e2eb080
 |              0x0
 |   next: 0xffff88003e090800
 |             |
 |            ...
 |             |
 |             v
  <-------------
```

## Further work

* Provide an utility that, given a certain process and a certain cache, notifies the user when a fresh slab was allocated and completely filled by that process only.

* Combine walking with recording to generate a visual representation of the heap evolution.

* Provide the option to also walk through partial and full slabs through kmem_cache_node.
