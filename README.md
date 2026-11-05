# scd-bios-disassembly

Annotated disassemblies for the North American Sega CD BIOS, version
2.00W (CRC 9F6F6276).

The repository includes the main-CPU BIOS, three sub-CPU modules (BIOS,
boot, and CD player), and the Z80 program 0 sound driver. The other Z80
programs are currently present as binaries only.

See [docs/BIOS-REFERENCE.md](docs/BIOS-REFERENCE.md) for a map of the
disassemblies, notes comparing them with [docs/MCDBios.pdf](docs/MCDBios.pdf), and the results of
a focused code review.

The 68K disassemblies target the Nemesis-modified SN Systems ASM68K
assembler, which is included in this repository.

Original BIOS copyright (c) 1993 SEGA.

This disassembly is for informational use only.
