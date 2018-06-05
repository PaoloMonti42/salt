Welcome to SALT, a tool for kernel heap memory reversing.

This project is implemented as a gdb plugin that helps analyze and trace the state of the SLUB allocator in modern linux kernels.   
This can be useful when developing an exploit, XXX , or even debugging your own kernel code.

While working on the tool, I also developed a loadable kernel module that can trigger allocations and frees at will, to serve both as a debugging tool and a playground to better understand the inner workings of the allocator system.

More information about using the tool and replicating the experiments can be found in the [docs](docs) folder.

 Developed at [EURECOM](http://www.eurecom.fr/en) as the semester project for Spring 2018.  
Many thanks to my supervisor [Yanick](https://www.eurecom.fr/fr/people/fratantonio-yanick) and to the rest of the [S3 team](http://s3.eurecom.fr) that helped and followed me.

XXX presentation
