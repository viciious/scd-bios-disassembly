# Sub-CPU CD-BIOS call dispatch

The CD-BIOS entry is `_CDBIOS`, installed in the sub-CPU jump table. Its
dispatcher is in [`prog0_bios.asm`](../sub-68k/prog0_bios/prog0_bios.asm):

1. `_CDBIOS` clears bit 7 of the function number in `D0`.
2. Calls whose original number was below `$80` go to
   [`queueCdbCommand`](../sub-68k/prog0_bios/prog0_bios.asm#L5047).
   Arguments are copied from the parameter block addressed by `A0` into
   the pending-command buffer; the CDD state machine later picks up the
   request.
3. Calls whose original number was `$80` or greater go immediately to
   [`executeCdbCommand`](../sub-68k/prog0_bios/prog0_bios.asm#L4901),
   which indexes [`@cdbJumpTable`](../sub-68k/prog0_bios/prog0_bios.asm#L4911).
   The implementation checks the normalized function number and returns
   without dispatching values outside `$80`–`$98`.

The function constants are defined in
[`bios.asm`](../sub-68k/common/constants/bios.asm#L33). Queued-command
state entries are selected in [`initCdb`'s `@loc_2AE4` table](../sub-68k/prog0_bios/prog0_bios.asm#L5195).
These are asynchronous state-machine entry points, not necessarily
complete synchronous implementations of each operation.

## Queued drive, music, and CD-ROM calls

| Function | Number | Description (manual and code) | Initial CDD handler |
| --- | ---: | --- | --- |
| `MSCSTOP` | `$02` | Stops CD-DA music playback. | [`loc_2F06`](../sub-68k/prog0_bios/prog0_bios.asm#L5719) |
| `MSCPAUSEON` | `$03` | Pauses music; the drive can enter standby after the pause interval. | [`loc_34A8`](../sub-68k/prog0_bios/prog0_bios.asm#L6353) |
| `MSCPAUSEOFF` | `$04` | Clears the music pause and resumes playback. | [`loc_34BC`](../sub-68k/prog0_bios/prog0_bios.asm#L6362) |
| `MSCSCANFF` | `$05` | Starts fast-forward music scan. | [`loc_3314`](../sub-68k/prog0_bios/prog0_bios.asm#L6166) |
| `MSCSCANFR` | `$06` | Starts fast-reverse music scan. | [`loc_3300`](../sub-68k/prog0_bios/prog0_bios.asm#L6159) |
| `MSCSCANOFF` | `$07` | Ends scan and returns to normal playback or pause, according to prior state. | [`loc_32F2`](../sub-68k/prog0_bios/prog0_bios.asm#L6153) |
| `ROMPAUSEON` | `$08` | Pauses CD-ROM data reading. | [`loc_3790`](../sub-68k/prog0_bios/prog0_bios.asm#L6654) |
| `ROMPAUSEOFF` | `$09` | Clears the data-read pause and resumes access. | [`loc_379E`](../sub-68k/prog0_bios/prog0_bios.asm#L6660) |
| `DRVOPEN` | `$0A` | Opens the drive tray through the CDD command state machine. | [`loc_2E44`](../sub-68k/prog0_bios/prog0_bios.asm#L5629) |
| `DRVINIT` | `$10` | Initializes/rechecks the drive and disc state. | [`loc_2C78`](../sub-68k/prog0_bios/prog0_bios.asm#L5420) |
| `MSCPLAY` | `$11` | Plays the designated song number. | [`loc_303E`](../sub-68k/prog0_bios/prog0_bios.asm#L5845) |
| `MSCPLAY1` | `$12` | Plays the designated song number once. | [`loc_3022`](../sub-68k/prog0_bios/prog0_bios.asm#L5833) |
| `MSCPLAYR` | `$13` | Repeats playback of the designated song number. | [`loc_3030`](../sub-68k/prog0_bios/prog0_bios.asm#L5839) |
| `MSCPLAYT` | `$14` | Plays the designated song from the supplied time position. | [`loc_2FD6`](../sub-68k/prog0_bios/prog0_bios.asm#L5807) |
| `MSCSEEK` | `$15` | Seeks to the beginning of the designated song and pauses there. | [`loc_3008`](../sub-68k/prog0_bios/prog0_bios.asm#L5825) |
| `MSCSEEKT` | `$16` | Seeks to the designated time position and stops there. | [`loc_2FBC`](../sub-68k/prog0_bios/prog0_bios.asm#L5799) |
| `ROMREAD` | `$17` | Reads CD-ROM data beginning at the supplied logical sector; the manual says CDC reading is started automatically. | [`loc_36D6`](../sub-68k/prog0_bios/prog0_bios.asm#L6580) |
| `ROMSEEK` | `$18` | Seeks the data position and pauses. | [`loc_3686`](../sub-68k/prog0_bios/prog0_bios.asm#L6557) |
| `MSCSEEK1` | `$19` | Seeks to the beginning of the designated song and plays it once. | [`loc_3002`](../sub-68k/prog0_bios/prog0_bios.asm#L5822) |
| `ROMREADN` | `$20` | Reads the requested number of sectors from the start sector; code computes an end position and shares the range-read setup. | [`loc_36C0`](../sub-68k/prog0_bios/prog0_bios.asm#L6572), then [`loc_36DE`](../sub-68k/prog0_bios/prog0_bios.asm#L6583) |
| `ROMREADE` | `$21` | Reads from the supplied start sector through end sector; code uses the same range-read setup as `ROMREADN`. | [`loc_36DE`](../sub-68k/prog0_bios/prog0_bios.asm#L6583) |

`ROMREADN` is implemented as a shared flow: `loc_36C0` adjusts the end
position using the requested start and count, then branches to
`loc_36DE`, which configures and starts the sector read. The boot module
uses the API by setting `D0` to `ROMREADN` and calling `_CDBIOS` in
[`readSectorsFromDisc`](../sub-68k/prog0_bios/include/submodules/cdboot.asm#L545);
that caller then polls CDC status, transfers and acknowledges sectors.

## Immediate status and control calls

The immediate jump table has one four-byte branch per function from
`$80` through `$98`, in order:

| Function | Number | Description (manual and code) | Direct target |
| --- | ---: | --- | --- |
| `CDBCHK` | `$80` | Checks whether a queued drive/music/data command is busy; carry is set while the pending bit is set. | [`_cdbchk`](../sub-68k/prog0_bios/prog0_bios.asm#L4967) |
| `CDBSTAT` | `$81` | Writes the 32-byte BIOS status record, including drive, LED, CDD, volume, and CDC header status. | [`_cdbstat`](../sub-68k/prog0_bios/prog0_bios.asm#L4974) |
| `CDBTOCWRITE` | `$82` | Installs a caller-provided TOC table unless its first longword is the end marker. | [`_cdbtocwrite`](../sub-68k/prog0_bios/prog0_bios.asm#L5009) |
| `CDBTOCREAD` | `$83` | Returns TOC time/address and track type for the requested track. | [`_cdbtocread`](../sub-68k/prog0_bios/prog0_bios.asm#L5019) |
| `CDBPAUSE` | `$84` | Sets the drive pause/standby delay used by the drive state machine. | [`_cdbpause`](../sub-68k/prog0_bios/prog0_bios.asm#L5038) |
| `FDRSET` | `$85` | Sets system volume, or master volume when `D1` bit 15 is set; hardware update is deferred. | [`_fdrset`](../sub-68k/prog0_bios/include/submodules/volume.asm#L30) |
| `FDRCHG` | `$86` | Ramps volume toward a target using the supplied slope. | [`_fdrchg`](../sub-68k/prog0_bios/include/submodules/volume.asm#L131) |
| `CDCSTART` | `$87` | Starts CDC data reading from the current position and resets CDC buffering/state. | [`_cdcstart`](../sub-68k/prog0_bios/prog0_bios.asm#L2829) |
| `CDCSTARTP` | `$88` | Starts/reconfigures CDC reading using mode flags from `D1`; unlike `CDCSETMODE`, it resets buffering and configures the CDC. This entry is not in the manual call list. | [`_cdcstartp`](../sub-68k/prog0_bios/prog0_bios.asm#L2834) |
| `CDCSTOP` | `$89` | Aborts CDC reading/transfers and disables the CDC interrupt. | [`_cdcstop`](../sub-68k/prog0_bios/prog0_bios.asm#L2794) |
| `CDCSTAT` | `$8A` | Reports whether a prepared CDC frame is available, using carry for empty/non-empty. | [`_cdcstat`](../sub-68k/prog0_bios/prog0_bios.asm#L2367) |
| `CDCREAD` | `$8B` | Prepares one buffered frame for transfer and configures the CDC transfer length/address. | [`_cdcread`](../sub-68k/prog0_bios/prog0_bios.asm#L2403) |
| `CDCTRN` | `$8C` | Transfers one CDC frame to the caller's buffers; carry indicates incomplete/failed transfer. | [`_cdctrn`](../sub-68k/prog0_bios/prog0_bios.asm#L2518) |
| `CDCACK` | `$8D` | Acknowledges completion of a CDC frame transfer. | [`_cdcack`](../sub-68k/prog0_bios/prog0_bios.asm#L2630) |
| `SCDINIT` | `$8E` | Initializes subcode flags and the P, pack, and Q-code ring buffers in the supplied scratch RAM. | [`_scdinit`](../sub-68k/prog0_bios/prog0_bios.asm#L3399) |
| `SCDSTART` | `$8F` | Starts subcode capture in the requested mode, clears buffered data, and enables the SCD interrupt. | [`_scdstart`](../sub-68k/prog0_bios/prog0_bios.asm#L3462) |
| `SCDSTOP` | `$90` | Stops subcode capture and disables the SCD interrupt. | [`_scdstop`](../sub-68k/prog0_bios/prog0_bios.asm#L3452) |
| `SCDSTAT` | `$91` | Returns the current subcode status words/counters. | [`_scdstat`](../sub-68k/prog0_bios/prog0_bios.asm#L3508) |
| `SCDREAD` | `$92` | Reads one 24-byte subcode pack from the pack buffer; community analysis identifies this path as CD+G R-W data, not a raw subcode frame. | [`_scdread`](../sub-68k/prog0_bios/prog0_bios.asm#L3572) |
| `SCDPQ` | `$93` | Reads a 12-byte Q-code record from the Q-code buffer. | [`_scdpq`](../sub-68k/prog0_bios/prog0_bios.asm#L3525) |
| `SCDPQL` | `$94` | Reads the latest buffered Q-code record, waiting for the latest entry when needed. | [`_scdpql`](../sub-68k/prog0_bios/prog0_bios.asm#L3522) |
| `LEDSET` | `$95` | Sets the user LED mode; modes 0–7 cancel system-controlled display behavior. | [`_ledset`](../sub-68k/prog0_bios/prog0_bios.asm#L5029) |
| `CDCSETMODE` | `$96` | Updates software flags from the low nibble of `D1` that affect how `CDCTRN` fetches data; it does not itself reconfigure CDC registers. Absent from the manual call list. | [`_cdcsetmode`](../sub-68k/prog0_bios/prog0_bios.asm#L2677) |
| `WONDERREQ` | `$97` | Tests `D1` and sets condition codes only; no request operation is performed in this implementation. | [`_wonderreq`](../sub-68k/prog0_bios/prog0_bios.asm#L4850) |
| `WONDERCHK` | `$98` | Always returns zero in `D0`; it does not inspect a request status. | [`_wonderchk`](../sub-68k/prog0_bios/prog0_bios.asm#L4859) |

The table's index arithmetic is in `executeCdbCommand`; its branch targets
are the direct implementation entry points. Some implementations are
short register operations, while CDC, SCD, and fader calls may call
helpers before returning.

## BIOS ring buffers: operation, capacity, and configurability

The BIOS has one shared ring-buffer implementation in
[`ringBuffer.asm`](../sub-68k/prog0_bios/include/submodules/ringBuffer.asm)
and one 16-byte header format in
[`ringbuffer.asm`](../sub-68k/prog0_bios/include/structs/ringbuffer.asm).
The header stores read/write step sizes, read/write offsets, a minimum-free
threshold, the data-area size, and a tag. Payload follows the header.
[`initRingBuffer`](../sub-68k/prog0_bios/include/submodules/ringBuffer.asm#L10)
sets both offsets to zero and installs the sizing values.
Reads and writes advance by one configured step and wrap at the data-area
size.

The write routine preserves a minimum-free gap: after advancing the write
offset, it compares the remaining free bytes against that threshold. If
there is not enough room, it advances the read offset by one step, dropping
the oldest item, and returns an overrun indication. All configured sizes
and thresholds are multiples of the step, so a queue retains
`(size - minimum-free) / step` items. The threshold reserves space; it is
not uniformly one item across all buffers. This is a lossy queue under
pressure rather than a producer-blocking queue.

| Queue | Payload / producer and consumer | Data area | Step | Minimum free | Nominal slots | Usable items |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| CDC descriptor queue ([`cdcRingBuffer`](../sub-68k/prog0_bios/include/variables/unknown.asm#L47)) | 8-byte sector metadata records; filled by the CDC update path, checked by [`_cdcstat`](../sub-68k/prog0_bios/prog0_bios.asm#L2367), and consumed by [`_cdcread`](../sub-68k/prog0_bios/prog0_bios.asm#L2403). It queues CDC-buffer descriptors, not sector payload bytes. | `$30` (48 bytes) | `$08` | `$08` | 6 | 5 |
| SCD P/Q staging ([`scdPcktBuffer`](../sub-68k/prog0_bios/include/variables/unknown.asm#L51)) | 24-byte logical steps; filled from the gate-array subcode buffer by the SCD interrupt path, then processed by [`updateSubcode`](../sub-68k/prog0_bios/prog0_bios.asm#L3876). | `$3C0` (960 bytes) | `$18` | `$A8` (168 bytes) | 40 | 33 |
| SCD pack queue ([`scdPackBuffer`](../sub-68k/prog0_bios/include/variables/unknown.asm#L52)) | 24-byte CD+G/R-W pack records; produced by [`updateSubcode`](../sub-68k/prog0_bios/prog0_bios.asm#L3876), consumed by [`_scdread`](../sub-68k/prog0_bios/prog0_bios.asm#L3572). | `$300` (768 bytes) | `$18` | `$18` | 32 | 31 |
| SCD Q-code queue ([`scdQcodBuffer`](../sub-68k/prog0_bios/include/variables/unknown.asm#L53)) | 12-byte Q-code records; populated when the selected SCD mode enables Q processing, consumed by [`_scdpq`](../sub-68k/prog0_bios/prog0_bios.asm#L3525)/[`_scdpql`](../sub-68k/prog0_bios/prog0_bios.asm#L3522). | `$60` (96 bytes) | `$0C` | `$0C` | 8 | 7 |

The CDC queue is initialized in
[`initCdc`](../sub-68k/prog0_bios/prog0_bios.asm#L2754) with an 8-byte step,
`$30`-byte data area, and 8-byte minimum-free threshold. Its header starts at
`$5A44`; the header plus its `$30` data bytes ends at `$5A84`, exactly where
[`scdFlags0`](../sub-68k/prog0_bios/include/variables/unknown.asm#L48)
begins. Its current capacity is therefore fixed in internal
BIOS RAM; enlarging it requires relocating or rearranging adjacent BIOS
state as well as changing the initialization values.

Although `$30 / 8` gives six physical descriptor slots, the queue reserves
one 8-byte step as `minFreeBytes`. When the sixth descriptor is written,
`writeRingBuffer` detects that the reserve would be consumed, advances the
read pointer, and drops the oldest descriptor. Thus at most five descriptors
remain queued at once; the sixth slot is the full/empty safety margin, not
additional retained capacity.

[`_scdinit`](../sub-68k/prog0_bios/prog0_bios.asm#L3399) takes a
caller-provided base address in `A0`, but does not take
capacity arguments. Its three fixed parameter records set the sizes above
and place the queue headers at offsets `$0000`, `$03D0`, and `$06E0` from
that base. The last configured data area ends at offset `$0750`, so callers
must provide at least `$0750` bytes of writable scratch RAM. The BIOS
initializes these queues from
[`dword_1EB6`](../sub-68k/prog0_bios/prog0_bios.asm#L3383); changing their
capacities requires changing that table and checking the offsets and
scratch allocation.
[`_scdstart`](../sub-68k/prog0_bios/prog0_bios.asm#L3462) empties all three
queues by setting each read offset to its write offset; it does not change
their configured sizes.

[`sub_203E`](../sub-68k/prog0_bios/prog0_bios.asm#L3614) advances the P/Q
staging write pointer by 24 bytes but copies 144 bytes from the gate-array
buffer at that position. The configured staging area is `$3C0` bytes, so
this copy fits within its data span. The following pack queue begins at
offset `$03D0`, immediately after the staging header and data area.

None of these capacities can be changed through the public `_CDBIOS`
calls. The CDC size is compiled into the BIOS's internal initialization;
the SCD scratch base is caller-selectable, but its queue sizes and offsets
are fixed by the BIOS. A modified BIOS can change the constants, provided
that it preserves step alignment, a nonzero free-space reserve, the
overrun/consumer assumptions, and sufficient non-overlapping RAM. The
queued CDD command slot is separate:
[`queueCdbCommand`](../sub-68k/prog0_bios/prog0_bios.asm#L5047) writes one
pending command record, not another ring buffer, so it has no ring capacity
to tune.

## Manual cross-reference

`MCDBios.pdf` documents the sub-CPU CD-BIOS call names and purposes in
its call list/reference (printed pp. 7–29). Its call convention places
the function number in `D0.w`, matching the `_CDBIOS` dispatcher. The
manual predates the 1993 BIOS source, so its list omits the later
`CDCSETMODE`, `WONDERREQ`, and `WONDERCHK` entries present in the
assembler constants and jump table.

### Manual/code differences

- The 1992 manual does not list `CDCSETMODE`, `WONDERREQ`, or `WONDERCHK`.
  The source includes `CDCSETMODE` as a working CDC flag setter. The
  Wonder entries are present but minimal: `_wonderreq` only sets condition
  codes from `D1`, and `_wonderchk` unconditionally returns zero. Their
  intended behavior cannot be established from this manual.
- The manual describes `CDCSTAT` as reporting prepared-data availability
  and labels the result `cc/cs OK/NULL`. The code clears carry when the
  ring buffer contains a frame and sets it when empty, consistent with
  that notation. `CDCREAD` likewise clears carry when it prepares a frame
  and leaves carry set when the buffer is empty; OCR damage obscures the
  manual's detailed return description, so no discrepancy is asserted.
- The manual labels `CDBSTAT` output as a 32-byte table; the code writes
  the two-byte control status, two-byte LED status, 20-byte CDD status,
  four-byte volume status, and four-byte CDC header, totaling 32 bytes.
  This description agrees with the implementation.

The PDF text extraction contains OCR damage (including command-name
fragments such as `CDSTART`); treat wording-level discrepancies cautiously.
The version gap also means an absent call may reflect a later BIOS addition,
not an error in the original manual.

## Community research and practical notes

The [SpritesMind discussion on reading Mega-CD subcode](https://gendev.spritesmind.net/forum/viewtopic.php?t=1650)
adds useful hardware observations, but its contributors distinguish
measured behavior from suggestions and speculation:

- The BIOS's ordinary sector-read flow is `ROMREADN`, poll `CDCSTAT` until
  carry clears, call `CDCREAD`, transfer with `CDCTRN`, then call `CDCACK`.
  The caller must select Sub-CPU read transfer mode (`$03` at `$FF8004`)
  before `CDCREAD` if it intends to use `CDCTRN`. This sequence is also
  visible in the BIOS boot reader linked above.
- The CDC stores sector data in its own buffer. Its level-5 interrupt gives
  the Sub-CPU a buffer location, which the BIOS queues in RAM; `CDCSTAT`
  tests that BIOS queue, rather than exposing the CDC's data buffer directly.
  `CDCREAD` starts/sets up the transfer and `CDCACK` releases the completed
  transfer. These details explain why the calls are separate.
- `CDCSETMODE` changes BIOS-side flags used by the transfer routine; it is
  not equivalent to programming the CDC hardware. The forum recommends
  `CDCSTARTP` when a fresh CDC configuration is needed, and discusses
  invoking it only after the ROM-read command has reached the appropriate
  state. Treat the proposed sequencing alternatives there as guidance, not
  a universally verified recipe.
- The BIOS `SCD*` calls expose processed subcode data, not the complete
  P-W subcode stream. The discussion describes `SCDREAD` as CD+G-oriented
  R-W data and `SCDPQ`/`SCDPQL` as Q-channel data. For raw subcode capture,
  contributors identify the gate-array buffer at `$FF8100` (mirrored at
  `$FF8180`) and the top-address/overrun indicator at `$FF8069`. They
  describe copying the 98-byte subcode set during level-6 SCD interrupt
  handling and deinterleaving each byte's P-W bits; this is a hardware-level
  technique, not a documented `_CDBIOS` call sequence.
- A follow-up report attributes the apparent trailing sync bytes when
  reading a 2352-byte sector to reading beyond the valid CDC data region.
  The thread also notes that raw-sector and subcode behavior may differ
  across hardware/emulators. These observations are useful diagnostics,
  not guarantees for every BIOS or device revision.

The [Sonic Research discussion](https://sonicresearch.org/community/index.php?threads/clownmdemu-the-greatest-mega-drive-emulator-ever-someday.6571/page-4)
is about emulator frontend features and does not provide additional
CD-BIOS behavior to document.
