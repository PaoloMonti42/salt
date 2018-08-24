Welcome to ***salt***, a tool to reverse and learn kernel heap memory management. It can be useful to develop an exploit, to debug your own kernel code, and, more importantly, to play with the kernel heap allocations and learn its inner workings.

This tool helps tracing allocations and the current state of the SLUB allocator in modern linux kernels.

It is written as a gdb plugin, and it allows you to *trace* and *record* memory allocations and to *filter* them by process name or by cache. The tool can also dump the list of active caches and print relevant information.

This repository also includes a *playground* loadable kernel module that can trigger allocations and deallocations at will, to serve both as a debugging tool and as a learning tool to better understand how the allocator works.

More information about the [inner workings of the SLUB allocator](docs/0x00_SLUB_refresher.md), how to [get started](docs/0x01_getting_started.md), the [detailed documentation of the plugin](docs/0x02_the_plugin.md), and [notes on the playground module](docs/0x03_the_playground.md) can be found in the [docs](docs) folder.


Here is the full list of commands:

```
> salt help
Possible commands:

filter -- manage filtering features by adding with one of the following arguments
       enable -- enable filtering. Only information about filtered processes will be displayed
       disable -- disable filtering. Information about all processes will be displayed.
       status -- display current filtering parameters
       add process/cache <arg>-- add one or more filtering conditions
       remove process/cache <arg>-- remove one or more filtering conditions
       relation -- change how the two filters are combined. The default is OR
              OR -- an event is selected if it satisfied one filter OR the other
              AND -- an event is selected if it satisfied one filter AND the other

record -- manage recording features by adding with one of the following arguments
       on -- enable recording. Information about filtered processes will be added to the history
       off -- disable recording.
       show -- display the recorded history
       clear -- delete the recorded history

trace <proc name> -- reset all filters and configure filtering for a specific process

walk -- navigate all active caches and print relevant information

walk_html -- navigate all active caches and generate relevant information in html format

walk_json -- navigate all active caches and generate relevant information in json format

help -- display this message

```

And here you can see salt in action:


![screenshot](docs/img/frontpage.png)



This project was developed at [EURECOM](http://www.eurecom.fr/en) as a semester project for Spring 2018.  
Many thanks to my supervisors [Yanick](http://www.s3.eurecom.fr/~yanick/), Fabio, Emanuele, Dario, Marius, and to the rest of the [S3 team](http://s3.eurecom.fr) that helped and followed me.

## Presentation

As part of my project, I also gave a presentation to the security team of EURECOM. The slides are available [here](presentation.pdf).

## Additional Resources

[Perla E, Oldani M (2010) - A Guide to Kernel Exploitation: Attacking the Core](https://books.google.com/books?id=G6Zeh_XSOqUC&printsec=frontcover)

[Christopher Lameter - Slab allocators in the linux kernel](https://events.static.linuxfound.org/sites/events/files/slides/slaballocators.pdf)

[th7.cn](http://www.th7.cn/system/lin/201701/200668.shtml)
