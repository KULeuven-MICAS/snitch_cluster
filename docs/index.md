# SNitch Acceleration eXtension (SNAX)
SNitch Acceleration eXtension (SNAX) is a platform that provides the basic needs of an accelerator in a multi-core system.

* Users can control their accelerator with RISCV control status register (CSR) instructions.
* These accelerators can access a direct memory with high flexibility and bandwidth through the tightly-coupled data memory (TCDM).
* The platform is a complete hw-sw test environment where users can also profile the performance immediately.

SNAX is extension of the [Snitch cluster](https://pulp-platform.github.io/snitch_cluster/) made by [PULP platform](https://pulp-platform.org/). Visit the links for more information.

## Getting Started

See our dedicated [getting started guide](ug/getting_started.md).

## Documentation

The documentation is built from the latest master and hosted at github pages: [https://github.com/KULeuven-MICAS/snitch_cluster](https://github.com/KULeuven-MICAS/snitch_cluster).

## About this Repository

This SNAX repository consists of several IPs from the original Snitch cluster:

* The original repository [https://github.com/pulp-platform/snitch](https://github.com/pulp-platform/snitch) was developed as a monorepo where external dependencies are "vendored-in" and checked in. For easier integration into heterogeneous systems with other PULP Platform IPs, the original repo was archived.
* The Snitch cluster repository [https://github.com/pulp-platform/snitch_cluster](https://github.com/pulp-platform/snitch_cluster) handles depenencies with [Bender](https://github.com/pulp-platform/bender) and has a couple of repositories as submodules.
* The Occamy System part of the original repository is being moved to its own repository [https://github.com/pulp-platform/occamy](https://github.com/pulp-platform/occamy). 


## Licensing

Snitch is being made available under permissive open source licenses. See the `README.md` for a more detailed break-down.
