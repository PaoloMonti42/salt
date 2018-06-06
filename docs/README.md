This folder contains all the documentation
It is made up of 4 chapters: their topics are quite separate, but they follow a logical thread that will help you understand the tool development process and philosophy.

They are organized as follows:

* [0x00](0x00_SLUB_refresher.md) -> this chapter serves as theory background about the general functioning of SLUB. It provides an in-depth explanation of how allocations and deallocations work in kernel land.

* [0x01](0x01_getting_started.md) -> this chapter will guide you through the creation of a local machine that emulates the target system you want to exploit, reverse, or work on.

* [0x02](0x02_the_plugin.md) -> this chapter will get you familiar with the *salt* tool for tracing dynamic allocations in the kernel.

* [0x03](0x03_the_playground.md) -> this chapter shows a simple implementation of a Linux driver that can act as a kernel heap playground by generating [de]allocations at will.
