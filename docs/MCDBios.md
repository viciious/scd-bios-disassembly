# Mega-CD BIOS Manual


MEGA-CD BIOS
MANUAL
SEGA ENTERPRISES, LTD.

# Contents

1. CD SYSTEM CONTROL PROCESS SUMMARY 1-1 Hardware Summary
1
1-2 Process Summary
2
1-3
CD System Control Chart
3
1-4
CD System Memory Map
4
2. BIOS CALL SUMMARY 2-1 BIOS Call Functions
5
2-2 BIOS Call List
7
2-3
BIOS Call Type Chart
9
2-4
Drive Control System Process Chart
10
3. BIOS CALL REFERENCE 3-D Drive (Mechanism) 3-M CD-DA (Music) 3-R CD-ROM (Data) 3-B CD-BIOS (Other Functions) 3-F Fader (Fader) 3-C CDC (Decoder) 3-S SCD (Subcode) 3-L LED (LED Display)
4. SYSTEM BOOTSTRAP SEQUENC 4-1
CD Boot System Mode 1 (Boot fro
30
4-2
CD Boot System Mode 2 (Boot fr
30
4-3
Booting Application Programs
31
33
5. JUMP TABLE AND USER CAL 5-1 Structure of the Jump Table
33
5-2 BIOS Call Sequence
33
5-3
User Call Sequence
34
5-4 Exception Processi
nce
35
36
6. BOOT SYSTEM 6-1 CD-Boot
36
7. BACK-UP 7-1 Back-
38
38

# 1. CD System Control Process Summary

The CD system control process operates on top of the SUB-CPU. It mediates between direct hardware control processes and user processes.

## 1-1 Hardware Summary

- [COD] Compact Disk Driver
  Hardware to reproduce music, data. A 4 bit CPU is dedicated exclusively to controlling hardware.
- [CDC] CD Data Controller
  Chip to output data after standard CD-ROM error correction has been Contains 16K bytes buffer memory which can contain up to 5 frames o ecode
- [SCD] Subcode (Functions contained within the MEGA-CD Gate Array)
  Functions to read supplementary data (Subcode) corftned i he CD Contains 128 bytes of buffer memory in MEGA-CD Gate
- [FDR] Fader
  output the CD drive.
  Controls the volume of music data (CD-DA) bei
- [LED] Light Emitting Diod
  Functions to show the status of t Consists of one green and one r
- [Back-up RAM]
  Battery backed back-up lAM Holds up to 8K bytes
  ation.
- [SDC]
  PCM sound qener
  40

## 1-2 Process Summary

- Initial Process
  This operation is initiated when the CPU is reset. Initializes required hardware and control processes. Requires over 100 msec while interrupts are disabled.
- System Control Process
  Controls the execution of system and user processes. Manages interrupt vectors and BIOS call entries.
- CD-Boot Process
  Loads programs from the CD and boots the system.
- CD-BIOS Control Process
  Operates the control processes of hardware according to the commands made by th application.
- CDD Control Process
  Controls the CD drive hardware.
- CDC Control Process
  Error correction is made to data output fr
- SCD Control Process
  D drive and stored in the MEGA-CD erformed.
  Reads out the Subcode data which Gate Array buffer. Error checking a
- FDR Control Process
  Controls the audio volume direct music data output from the CD drive.
- LED Control Prcicess
  Controls the on/off state of the C.D drive's status LED's.
- Back-urn-Aft/40 PrOtess
  In orde
  allow the
  Iioned usage of the RAM by multiple applications, a common I/O
  proces
  used for indu rtput.
  B-10c Ails are made according to the needs of the application.

## 1-3 CD System Control Chart

Processes which are fixed in the MEGA-CD interface ROM. (These operate when supplied by RAM.)
Shows the control relationship
0—
Shows the data flow
[USER PROCESS]
[SYSTEM PROCESS]
[HARDWA
INITIAL PROCESS
SYSTEM CONTROL PROCESS
1
CD-BOOT PROCESS
1
1
t
USER PROCESS
CDD
CD
ONTROL PROCESS
CDC
SCD
SCD CONTROL PROCESS
FDR
FDR CONTROL PROCESS
LED
LED CONTROL PROCESS
Back-up RAM I/O Process
Back-up RAM
SDC CONTROL PROCESS
SDC
SOUND-BIOS CONTROL PROCESS it

## 1-4 CD System Memory Map

SUB-CPU
`$000000`
Vector
`$000100`
Write protect area
CDBIOS ID
`$000200`
CD System Program
`$005400`
Work
`$005C00`
Heap Stack
`$005E80`
Common Work
`$005EE0`
Jump Table
`$006000`
User Header
`$006020`
User Program
`$07FFFF`

# 2. BIOS Call Summary

BIOS Call Functions
- Purpose
  The programmer issues commands to the program (BIOS) that controls and manages the operations of hardware necessary to carry out tasks such as playing music or reading d with the CD drive. In addition, there are programs which can manage back-up RAM and b from the CD disc.
- Caution
  After the initialization process, level 2 (software V-INT) and level 4 (CDD) interrupts become enabled. After that, depending on the CD-ROM related BIOS calls, level 5 (CDC) and level 6 (SCD) interrupts either become enabled or dis
  hen dealing s mentioned
  If these interrupts are disabled, the BIOS cannot operate norm with the interrupt mask control port, never change the ena above. (Use bit operation commands.)
  In addition, the interrupt disable status cre for short time periods (on the microseco periods (on the millisecond order), ope
  ister will not be problem tended for longer time a will run into difficulties.
  On the other hand, never set an interr
  n the current level. After changing
  the interrupt level, it is necessary to ret
  the level to
  previous position.
  The CD-BIOS is managed within level 4 interru
  anagement. Therefore, BIOS calls should
  not be made while interrupt m
  ement above level 4 is in effect (Interrupts above level 4 are
  CD system exclusive. Ac
  ibited to the user.)
  BIOS, LED, Fader, SCD, and CDC rl ed calls are executed immediately. However, for DRIVE, CD-DA, ancl,CD-ROM relate calls, there is a lag time between the receipt of the command and t
  Acutio
  mmand.(This is managed by a level 4 interrupts with
  13.3 msec in
  It is necess execution o
  e application level in order to handle power failures during the related functions. This is especially critical when directories are falL. e can destroy data from other applications. In addition, we ry protect functions. By using these functions, it may be possible to
  amaged data. Design the application software to protect the memory when emory protect functions.
  , u code, and boot system related calls should not normally be used on the application

- Call Method
  A parameter selected by a command is set in a register and then the BIOS call entry is called.
  Parameters important to several functions are set up in a table, and the parameter table's header address is set in register `a0`.I. In addition, parameters necessary for the functions are set in the other registers.
  The function numbers are set register `d0`.w.
  The CD-BIOS entry address is called. Registers other than `d0`/`d1`/`a0`/`a1` are stored if they are not utilized as return value The entry addresses and the function numbers are provided by an "include" (For details regarding each function, refer to the BIOS call reference.)
- Example
```asm
parameter_table_1:
dw
PARAMETER_10, PARAMETER_11...
bios_call_example1:
lea.l
parameter_table_1 (pc), a0
move.w #FUNCTION NUMBER_1, d0
jsr
bios_entry_address
rts
bios_call_example_2:
move.w #PARAMETER_20, d1
move.w #PARAMETER_21, d2
move.w #FUNCTION NU
jsr
bios_entry_add
rts
```

## 2-2 BIOS Call List

| Abbreviation | Summary |
| --- | --- |
| DRVINIT | Close loading tray and read TOC. |
| DRVOPEN | Open loading tray. |
| MSCSTOP | Stop music playing. |
| MSCPLAY | Play music from designated song number. |
| MSCPLAY1 | Play music from designated song number once. |
| MSCPLAYR | Repeat playing of designated song number. |
| MSCPLAYT | Play music from designated song number at designated ti |
| MSCSEEK | Stop at the beginning of designated song number. |
| MSCSEEK1 | Stop at the beginning of designated song number and play only once. |
| MSCSEEKT | Stop at a designated time. |
| MSCPAUSEON | Pause music playing temporarily. |
| MSCPAUSEOFF | Clear pause and restart music playing. |
| MSCSCANFF | Play music fast-forward. |
| MSCSCANFR | Play music fast-reverse. |
| MSCSCANOFF | Cancel high speed music playing and restersic p |
| ROMREAD | Begin data read from designatedi4cal sector. |
| ROMREADN | Read data a designated number of sectors b nning at a designated logical sector. |
| ROMREADE | Read data between two desig gical *otg.r/ |
| ROMSEEK | Stop at designated logical s |
| ROMPAUSEON | Pause data read. |
| ROMPAUSEOFF | Clear pause an start dat |
| CDBCHK | Check to see Jequest comma een received. |
| CDBSTAT | Read status. |
| CDBTOCREAD | Read TOC da |
| CDBTOCWRITE | Write data to able. |
| CDBPAUSE | Determine when ode will change to stand-by mode. |
| FDRSET |  |
| FDRCHG | k.44 ue at specified speed. |
| CDCSTART |  |
| CDCSTOP |  |
| CDCSTAT | eck to if data is ready. |
| CDCREAD | data read. |
| CDCTRN | ead data with SUB-CPU. |
| CDCACK | E+ data read. |
| SCDINIT | Inito'lize for Subcode read. St reading Subcode. |
| SCDREAD | Check to see if Subcode is ready. Read Subcode. |
| SCDPQ | Get P,Q code from Subcode |
| SCDPQL | Get last P,Q code from Subcode |
| LEDSET | Set LED mode |
| CBTINIT | Initialize the boot system. Cancel booting. |
| CBTINT | Call the routine to manage interrupts. |
| CBTOPENDISC | Request to open the loading tray. |
| CBTOPENSTAT | Check the completion of the request to open the loading tray. |
| CBTCHKDISC | Request to check whether a boot can be done or not. |
| CBTCHKSTAT | Check boot completion and return disc type. |
| BRMINT | Prepare for read/write of back-up RAM. |
| BRMSTAT | Return usage status of back-up RAM. |
| BRMSERCH | Get information from back-up RAM's control file. |
| BRMREAD | Read data from back-up RAM. |
| BRMWRITE | Write data to back-up RAM. |
| BRMDEL | Erase back-up RAM data. |
| BRMFORMAT | Format |
| BRMDIR | Get a directory. |
| BRMVERIFY | Check the data written to the back-up RAM. |

## 2-3 BIOS Call Type Chart

SYSTEM CONTROL PROCESS
CD-BIOS CONTROL PROCESS
Drive control related CD-DA music related CD-ROM data related
CD-BIOS and other functions related CDB... Fader related Decoder related Subcode related LED related

Drive Control System Process Chart
RESET
(0)
(2)
TOC READING
OPEN
(1)
(1
(0)
PAUSE
PLAY
NO DISC
READ
(0)
PLAY, READ
(11
(2)
(1)
STOP
TOC READING
' OPEN
( 0) — AUTO — DREN — DR NIT — MSPAUSEON 7-5atScPAy FF MSCP,LA x, MSC
Kx
MSCSCANOrMS SCANFR
7)
MSCSCANOFF
( 8)
R MREADx, ROMSEEK
(
MPAUSEON ROMPAUSEOFF MSCSTOP
*NP

# 3. BIOS Call Reference

3
- How to read this reference:
  Abbreviation
  Name

**ENTRY:** Entry address-

Address to call.

**IN:**

Function number- The abbreviation of the function is defined. Other parame ers
to be set when called. Contents of the parameter table.
Contents of the parameter table

**OUT:**

Return value.

**BREAK:** Non-stored register.

**FUNC:**

Explanation of function.

**NOTE:** Notes.

**BUG:**

Known bugs.

**SAMPLE:** Examples.

- Note
  (HEX):
  Hexadecimal values
  (`$00`, `$01`...`$09`, `$0a`..$ f, `$10`.,..)
  (BCD):
  BCD values
  (`$00`, `$01`...`$09`, `$10`...`$15`.416
  cc/cs:
  carry clear/carry set
  The constants found this reference are defined in the

### 3-D Drive (Mechanism)

#### `DRVINIT` — Initialize drive

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdbios |  |
| IN |  | function number (DRVINIT) |
| IN | `a0`.I | table address |
| IN | startTNO.b | The first track number where the TOC data in the TOC resides. Normally 101" (hex). |
| IN | endTNO.b | Last track number. Normally, if 1ff (hex) is designated, all of„the tracks on the disk will be read to the last track. |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Reads the designated TOC after the loading tray is closed. A 2 secon | se occurs after the TOC read. If bit 7 of startTNO is set, the first song is atd.tically played after the TOC read. If there is no disk, it waits until DRVOP requested. |
| NOTE | At a minimum, more than one track of TOC data must be read |  |

**SAMPLE:**

```asm
table:
db
$01, $ff
subroutine:
lea.l
table (pc), a0
move.w
#DRVINIT, d0
jsr
_cdbios
rts
```

#### `DRVOPEN`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number ( |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Opens loading tow. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
JSr ,
#DRVOPEN, d0
_cdbios
```

### 3-M CD-DA (Music)

#### `MSCSTOP` — Stop music

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdbios |  |
| IN | -d-0.w | function number (MSCSTOP) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Stop music playing. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w
#MSCSTOP, d0
jsr
cdbios
```

#### `MSCPLAY`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCPLAY) |
| IN | `a0`.I | table address |
| IN | TNO.w | Song number to play. |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Plays music from designated song nu |  |
| NOTE |  |  |

**SAMPLE:**

```asm
table:
dw
$0
subroutine:
lea.l
ta
move.w
#M
jsr
_cdb
rts
```

#### `MSCPLAY1` — Play music 1

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSPLAY1) |
| IN | `a0`.I | table address |
| IN | TNO.w | Song number play |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Replays the music of the designated song number once. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
table:
dw
$0002
subroutine:
lea.l
table (pc), a0
move.w
#MSCPLAY1, d0
jsr
_cdbios
rts
```

#### `MSCPLAYR` — Repeat musi

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCPLAYR) |
| IN | `a0`.I | table address |
| IN | TNO.w | Song number to play |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Repeats the music playi |  |
| NOTE |  |  |

**SAMPLE:**

```asm
lea.l
move.w
jsr
rts ti
Music playing time
ENTRY
```

#### `MSCPLAYT`

| Field | Value | Description |
| --- | --- | --- |
| IN |  | umber (MSCPLAYT) dress Time to begin playing mm:ss:ff:00 (BCD) |
| OUT |  | Non BREAK `d0`/d al UNC: Plays music beginning at the designated time. |

```asm
NOT
E:
table:
d1
$00020000
subroutine:
)
lea.l
table (pc, a0
#MSPLAYT
, d0
move.w
jsr
_cdbios
rts
```

#### `MSCSEEK` — Seek music

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCSEEK) |
| IN | `a0`.I | table address Goes to the beginning of the designated song number and pauses. |
| IN | TNO.w | Song number to seek |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  |  |
| NOTE |  |  |

**SAMPLE:**

```asm
table:
dw
$0002
subroutine:
lea.l
table (pc), a0
move.w
#MSCSEEK, d0
jsr
_cdbios
rts
```

#### `MSCSEEK1` — Seek one so

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | c10.w | function number (MSCSEEK1) |
| IN | `a0`.I | table address |
| IN | TNO.W | Song number to seek. |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Goes to the beginning of t | and pausing. After pausing, plays the song only once. |
| NOTE |  |  |

**SAMPLE:**

```asm
dw
subroutine:
(pc), a0
EK1, d0
lea]
move
jsr
rts
```

#### `MSCSEEKT` — :Seek music titOe

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCSEEKT) |
| IN | `a0`.I | table address --+ |
| IN | time.I | Time to seek mm:ss:ff:00 (BCD) |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Stops at the designated time. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
table:
d1
$00020000
subroutine:
lea.l
table (pc), a0
move.w
#MSCSEEKT, d0
jsr
cdbios
rts
```

#### `MSCPAUSEON` — Music pausem

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCPAUSEON) |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Stops playing of music and pauses. |  |
| NOTE | Since an extended pause is | et period of time, the ause occurs). drive will stop. (The same |

**SAMPLE:**

```asm
move.w
jsr
cdbi
```

#### `MSCPAUSEOFF` — sic pause o

| Field | Value | Description |
| --- | --- | --- |
| Content | (MSCPAUSEOFF) |  |
| ENTRY |  |  |
| IN |  |  |
| OUT |  |  |
| BREAK |  |  |
| FUNC |  | _cdbios `d0`.w func None `d0`/`d1`/`a0`/01 Cletili-s pa and re arts playing of music. |
| NOTE |  | the m iyng is stopped and while in stand-by mode, this subroutine eeks the pause time and starts playing the music again. move.w' #MSCPAUSEOFF, `d0` id cdbios |

#### `MSCSCANFF` — Music forward scan

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCSCANFF) |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Plays fast forward scan of music. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w
jsr
```

#### `MSCSCANFR` — Music reverse scan

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MSCSCANFR) |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Play fast reverse scan of music |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w
jsr
cdbios
```

#### `MSCSCANOFF`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (MS |
| OUT |  | None |
| BREAK | de/`d1`/`a0`/al |  |
| FUNC | Stop fast scan playing of m | from a pause, the drive will pa |
| NOTE |  |  |

#### `ROMREAD` — Read ROM

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | de.w | function number (ROMREAD) |
| IN | `a0`.I | table address |
| IN | sector.I | Logical sector number to begin read |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Reads data from the designated logical sector. |  |
| NOTE | Since CDCSTART is automatically executed, in order to stop the rea | necessary to execute CDCSTOP. |

#### `ROMREADN` — Read ROM number

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (ROMREADN) |
| IN | `a0`.I | table address ' |
| IN | sector.I | Logical sector number to begin reqt1 |
| IN | number.I | Number of sectors to read. |
| OUT | None | A .41t. |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Reads the designated number | r begin rpng at. i nated logical sector. |
| NOTE | CDSTART is automatically, | cute. er the si., ed number of sectors are read, the music automati is executed. |

#### `ROMREADE`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdbios |  |
| IN | -d-0.w | functi r (ROMREADE) |
| IN | `a0`.I | table address --- startsectori Logical tor number to begin read endsectoril Logical ctor number where read ends |
| OUT |  | Norke |
| BREAK | , \`50ictlia0:ai |  |
| FUNC | , Reads da between one designated logical sector and another designated logical | sector. , |
| NOTE | t CDSTART is automatically executed. After the sectors are read, CDCSTOP is | „ SAMPL'E. 4 .4 See BIOS load sample ticallye'xecuted. ( |

#### `ROMSEEK`

| Field | Value |
| --- | --- |

#### `ROMSEEK`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (ROMSEEK) |
| IN | `a0`.I | table address --± |
| IN | sector.I | Logical sector number to seek |
| OUT |  | None |
| BREAK | d 0/d 1 /`a0`/al |  |
| FUNC | Seeks designated logical sector and pause. |  |
| NOTE |  |  |

#### `ROMPAUSEON`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (ROMPAUSEON) |
| OUT |  | None |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Stop data read and pause. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w #ROMPAUSEON, dø
jsr
_cdbios
```

#### `ROMPAUSEOFF` — _cdbios

| Field | Value | Description |
| --- | --- | --- |
| Content | de.w function number (R |  |
| Content | None |  |
| Content | `d0`/`d1`/`a0`/al |  |
| Content | Clears pause and restarts |  |
| ENTRY |  |  |
| IN |  |  |
| OUT |  |  |
| BREAK |  |  |
| FUNC |  |  |
| NOTE |  |  |

### 3-B CD-BIOS (Other Functions)

#### `CDBCHK` — Check CD-BIOS

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDBCHK) |
| OUT |  | cc/cs COMPLETE/BUSY |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Checks to see if request commands to the CD-BIOS control (DRIVE, CD-DA, | CD-ROM related) have been completed. |
| NOTE |  |  |

**SAMPLE:**

```asm
loop:
move.w
#CDBCHK,d0
jsr
_cdbios
bcs.s
loop
```

#### `CDBSTAT`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDBSTAT) |
| OUT |  | `a0`.I pointer of status table (32byte) -± bios_status.w [drv1msc101rom] drive control statu led.w [real (0000 00GR)Imode 0-7)] LED s cdd_status.20 [status1 report1control 1absolute time (mms L) 1relative L) 'start tr lend trac I versi GS 1reado start time] driv stat volume.I [mastf volumelvolume] Fader volume header.I [min1 sjc Iframe1mode4realtime)] data read status Contents of bios_status 1xxx xxxx xxxx xxx 0100 0000 xxxx xxxx tray 0010 000 xx xxxx : reading TOC 0001 x xxxx : no disk 0000 xxxx xx xxxx : finished reading TOC 0000 0000 xxxx Axx : stopped 0000 0001 xxxx xxxx : playing music, data .4) on 11 4 xxxx : scanning music OW'xxx xxxx : paused 000 xxxx xxxx : seeking for play x 0000 0000 : data read complete 0000 0001 : reading data 0000 0101 : reading data paused 0000 1000 : seek for read s will change if the drive goes into "not ready" status after a drive control BIOS call is requested. tents of led B1T15-10 : 0 BIT9 : Green LED ON (1)/OFF (0) BIT8 : Red LED ON (1)/OFF (0) B117-0 : LED blink mode (refer to LEDSET) |

Contents of cdd_status (BP: Byte position)
BP0
: Status code
BP1
: Report code
BP2
: Disk control code
(*1)
BP3
: Song number (hex) (*1)
BP4-7 : Absolute time (BCD) minutes, seconds, frame, flag 9P8-1 1: Relative time (BCD) minutes, seconds, frame, flag BP12 : First song number BP13 : Last song number BP.14 : Drive version BP15 : Flag (*3) BIT3: Unused (0)
BI12: 0:Music 1:Data BIT1: Emphasis ON (1)/OFF (0) BIT& Mute ON, -12dB (1)/OFF (0)
BP16-19: Start time of read out area.
Ignored when -1. The flag is set in real time. The flag is in the read-in area.
Ne Contents of volume
BIT31-16: Master volume (`$0` -`$400`) BIT15-0 : Volume ($vvvf vvv: `$0`- `$400` f: E
xContents of header
Time written in the frame which precedes the

**BREAK:** `d0`/`d1`/`a0`/`a1`

**FUNC:** Reads the status of the CD BIOS The _cds

d in `a0` .I

**NOTE:**

_cdstat is rewritten each time this function

**SAMPLE:**

| Field | Value |
| --- | --- |

**SAMPLE:**

```asm
move.w
#CDBST
jsr
_cdbios
```

#### `CDBTOCREAD` — TOC read

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function num er (CDBTOC ) dl .w TOC# (hex number to be read |
| OUT |  | `d0` .I time info byte is TNO) if error,' kw byte is `d1`.b track types `$00` -DA track `$FF` çvCD-ROM track |
| BREAK | `d0`/ |  |
| FUNC | R | formation. If a song number is requested without it being read in the I occur. When an error occurs, the time information will be either iously read or the time at the beginning of the disk. NOT uld not be read during a TOC read. #`$01`, `d1` |

```asm
move.w
#CDBTOCREAD, d0
jsr
```

| Field | Value | Description |
| --- | --- | --- |
| FUNC |  | _cdbios |

#### `CDBTOCWRITE` — CD-BIOS TOC write

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDBTOCWRITE) |
| IN | `a0`.I | pointer to time information table (min:sec:frame:tno (bcd)) frame-bit7 0: CD-DA track 1: CD-ROM track The time information table format consists of minutes, seconds, and frames represented by 3 bytes of BCD code. A one byte song number is attached to the end. The data for one song consists of these four bytes. |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Write data to TOC table. |  |
| NOTE |  | On disks with large amounts of TOC information, it is possible to rewrit":-,,,, OC table directly in order to shorten the TOC read time. The TOC table sh. iot be written while a TOC read is in progress. |

**SAMPLE:**

```asm
table:
d1
$00028001, $10000002, $20000003, ENDOFTOCITBL
subroutine:
lea.l
table (pc), a0
move.w
#CDBTOCWRITE, d0
jsr
cdbios
rts
```

#### `CDBPAUSE`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (C dl .w max. pause time |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | determines when the pause | ge to stand-by mode. |
| NOTE | When -1 is set, stand-by mode | tered except during debugging. In the released version4et this entry within the range: 4500-65534 (`$1194` `$FFFE`). |

F Fader (Fader)

#### `FDRSET` — Set Fader

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (FDRSET) dl .w volume `$0000` (small) - `$0400` (large) : volume `$8000` (small) - `$8400` (large) : master volume |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | Sets audio volume levels. If BIT15 of volume is set, the master volume changed. |
| NOTE |  | It takes several milliseconds (0 - 13 msec) before the audio volume ac to change. It takes several more milliseconds (0 - 23 msec) before the reaches the designated level. Since volume cannot be set to exceed the va by the master volume, this command is used to enable the user master volume or to allow the program to change the volume. |

**SAMPLE:**

```asm
move.w
move.w
jsr
#$0400, d1
#FDRSET, d0
_cdbios
```

#### `FDRCHG` — change

| Field | Value | Description |
| --- | --- | --- |
| Content | .3 msec |  |
| Content | (set once) |  |
| Content | om one volume level to another. |  |
| ENTRY | _cdbios |  |
| IN | de.w | function number (FDRC |
| IN | `d1`.I | H: att. target data (0 400) Vo L: change speed ( `$0400`) (step `$0001` (slow) - 200 (fast), `$04` |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Change audio volume level |  |
| NOTE |  | Effect time varies according to v settings. |

**SAMPLE:**

```asm
move4
000004, d1
move. X
#F
HG, d0
jsr
cdbi
```

### 3-C CDC (Decoder)

#### `CDCSTART`

| Field | Value |
| --- | --- |

#### `CDCSTART`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDCSTART) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC |  | Begins data readout from current logical sector. |
| NOTE | The actual read begins 2 - 4 sectors prior to the designated sector. When | stopping the read, CDCSTOP must always be executed. Read during playing, otherwise meaningless data may be read. |

#### `CDCSTOP`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN |  | caw function number (CDCSTOP) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Stops data read. |  |
| NOTE | The sector currently being read is thrown out. |  |

#### `CDCSTAT`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdbios |  |
| IN | -d-0.w | function number (CDC T) |
| OUT |  | cc/cs OK/NULL (Prepared dta present/not present |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Checks to see if data has be'Ar) prepared. |  |
| NOTE | Buffers up to 5 frames. |  |

#### `CDCREAD`

| Field | Value |
| --- | --- |

#### `CDCREAD`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios - |  |
| IN | de.w | Junction DCREAD) |
| OUT |  | ccj. A 0 der time (mmssffMD) Prepar ta present minutes/seconds/frame/mode NULL present |
| BREAK | d | 1/aø/`a1` '..011:5,isfqv 41, prepares to read one frame worth of data. Before executing this functIø. qsure to set the CDC mode (device destination). Moreover, after reading the ata, always execute CDCACK. When returned by cs, it is not necessary to execute CDCACK. See BIOS load sample PROPERTY OF SEGA |

#### `CDCTRN` — CDC transfer

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDCTRN) |
| IN | `a0`.I | point to destination data buffer (size: 2336 bytes) al .1 pointer to header buffer (size: 4 bytes) |
| OUT |  | cc/cs ok/not complete (all data transferred/data transfer not complete) `a0`.I next pointer to destination data buffer al .1 next pointer to header buffer |
| BREAK | `d0`/`d1`/`a0`/al | 44* |
| FUNC | Reads one frame worth of data with the SUB-CPU. |  |
| NOTE | This function can only be called when the CDC mode (device destinatio | et to the SUB-CPU read. |

#### `CDCACK`

| Field | Value |
| --- | --- |

#### `CDCACK` — nowledge

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (CDCACK) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Ends one frame worth of data read. |  |
| NOTE |  | It is necessary to call this function after |

-
-3 S SCD (Subcode)

#### `SCDINIT` — Subcode initialization

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (SCDINIT) |
| IN | `a0`.I | pointer to scratch RAM (`$750`) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | Initialization is done before reading Subcode. |
| NOTE |  |  |

**SAMPLE:**

```asm
lea.l
scratchRAM, a0
move.w
#SCDINIT, d0
jsr
cdbios
```

#### `SCDSTART`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | del.w | function number (SCDSTART) dl .w Subcode processing mode (0-3) 0: 1:__ RSTUVW PQ PQRSTUVW |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Starts reading Subcode. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w
jsr
```

#### `SCDSTOP`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (SCDSTOP) |
| OUT |  | none |
| BREAK | d | Ja0 al re. |
| FUNC |  | t.p Subcode |
| NOTE | . | SAMPLE. move.w #SCDSTOP, `d0` _cdbios |

#### `SCDSTAT` — Subcode state

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdbios |  |
| IN | -d-0.w | function number (SCDSTAT) |
| OUT |  | `d0`.I errqcodecrc / errpackcirc /scdflag / restrcnt `d1`.I erroverrun / errpacketbufful / errqcodebufful / errpackbufful |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Returns error status of Subcode. |  |
| NOTE |  |  |

**SAMPLE:**

```asm
move.w
#SCDSTAT, d0
jsr
cdbios
```

#### `SCDREAD` — Subcode read

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (SCDREAD) |
| IN | `a0`.I | pointer to Subcode buffer (size: 24 bytes) |
| OUT |  | cc/cs OK/NULL prepared data available/no data present `a0`.I pointer of Subcode buffer |
| BREAK | a/di/al |  |
| FUNC | Reads R-W codes from Subcode (1 pack) |  |
| NOTE |  |  |

**SAMPLE:**

```asm
buffer:
ds
24
subroutine:
lea.l
buffer,
move.w
#SCDR
jsr
cdbios,
bcs.s
not read
bcc.s
ready
```

#### `SCDPQ` — Subcode PQ

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (SCDPQ) |
| IN | `a0`.I | pointer to Q code buffer (size: 12 bytes) |
| OUT |  | cc/cs OK/NULL `a0`.I pointer to 0 code buffer |
| BREAK | `d0`/`d1`/`a1` |  |
| FUNC | Retrieves P and 0 codes from the Subcode. |  |
| NOTE | 6 | 2 34 5 67 8 9 CONTROL ADDRESS1 TNO I X MIN SEC FRAME PI AMIN ASEC AFRAME CRC CONTROL ADDRESS2 DATA 0 P AFRAME CR CONTROL ADDRESS3 DATA P AFRAME CR CONTROL Bit2 0: music 1 : data Bit0 0: normal 1 : pre-emphasis ADDRESS 0 reserved 1 mode-1 time 2 mode-2 catalog number 3 mode-3 International-Stan rd7Recording-C 4- reserved 0: music or data 1 : start flag (pause) CRC 0: no error other: error exist |
| ENTRY | cdbios |  |

**SAMPLE:**

```asm
ds
subroutine:
qbuff
#SC
lea.l
move.w
jsr
bcs.s
bcc.s
cdbio
not read
ready
Subcode PQL
```

#### `SCDPQL`

| Field | Value | Description |
| --- | --- | --- |
| IN | `d0`.v | funciton numbigr (SCDPQL) ,a03,_pointe fde buffer (size: 12 bytes) |
| OUT | / cc/cs OPULL | `a0`.I poitto 0 code buffer BREA `d0`/`d1`/`a1` s the last code. 'qbuffer: |

```asm
ds
12
subroutine:
lea.l
qbuffer, a0
move.w
#SCDPQL, d0
jsr
cdbios
bcs.s
not ready
bcc.s
```

| Field | Value | Description |
| --- | --- | --- |
| OUT |  | ready |

3 L LED (LED Display)

#### `LEDSET`

| Field | Value |
| --- | --- |

#### `LEDSET`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdbios |  |
| IN | `d0`.w | function number (LEDSET) dl .w mode number blinking mode of LED |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Sets a LED mode | When the mode number is set to 0 through 7, system control is cancelle mode# H Greenli Red 4 system control (reset x I x not used CD-ROM driver) LEDREADY(0) o * CD ready & no disc LEDDISCIN(1) o x CD ready & disc OK LEDACCESS(2) o o CD access LEDSTANDBY(3) * x standby mode LEDERROR(4) * * (reserved) LEDMODE5(5) * o (res. ed) LEDMODE6(6) x * (res ) LEDMODE7(7) x o (resery LEDSYSTEM ret off bnk1ng |
| NOTE | Since the status of the LEDs show the stditis of Cb the drivdt, | do not use this subroutine exc |

**SAMPLE:**

```asm
move.w
#LEDR
move.w
#LEDS
jsr
_cdbios
```

# 4. System Bootstrap Sequencing

## 4-1 CD Boot System Mode 1 (Boot from cartridge)

- MAIN-CPU
  (0)
  Power On Boot cartridge. Initialize MEGA-DRIVE hardware. Transfer CD-SYSTEM program to SUB-CPU side. Transfer SUB-CPU application program. Reset release SUB-CPU Initialize application program. Wait for SUB-CPU application program to run. (Wait for initialization on SUB-CPU side.) Execute application program.
- SUP-CPU
  (0) Power on reset.
  B-CPU 4.1"ation program, reset
  44,4,41
  When rebooting, the same
  After transferring the CD-SYSTEM program and th released by the MAIN-CPU. Initialize CD-SYSTEM program. Initialize SUB-CPU application program. Run CD-SYSTEM program. (Begin interrupt p Run SUB-CPU application program The choice to reboot can be sele process at power on is carried
  CD Boot System M
  from CD-DISC)
  At Power ON
- MAIN-CPU
  (0)
  are. m to SUB-CPU side. am to SUB-CPU. m (IP) and system program (SP) load program) FL).
  Power On. Boot/from BOOT Initialize MEGA-DRIVE har Transfer-SYEM Tranpe (lni lization pr Re t release S Wa `sr` IP to bp Ira
  erred.
  fter ) Wait for app (8) Execute app
  plete,.execute. rogram transfer. ion program.

- SUB-CPU
  (0)
  Power on reset. After transferring the CD-SYSTEM program and the CD-BOOT program, reset is released by the MAIN-CPU. Initialize CD-SYSTEM program. Initialize CD-BOOT program. Run CD-SYSTEM program. (Begin interrupt processing.) Run CD-BOOT program. After loading IP, transfer to MAIN side. Execute SP after loading. Load application program. Also transfer to MAIN side. Execute application program.

## 4-3 Booting Application Programs

- MAIN-CPU Side
- In CD boot system mode 1 (boot from cartridge), the application program
  from the boot program.
- In the case of CD boot system mode 2 (boot from CD), a subprogr
  the initial program's header.
- SUB-CPU Side
- In CD boot system mode 1, a user header is attached to 'the heade
  the SUB-CPU
  application program.
- In CD boot system mode 2, a user head
  to thqfead3Pof the CD BOOT
  program. A subprogram header is att ed to the sy''ç pro
  header.
- User Header Specifications
  (0) __L_TEXT:
  ; module name, flag ; version, type ; ptr. next module ; module size ; start address ; work RAM size
```asm
db
'MAIN
dw
$01004-
d1
0
\,.
d1
_ j_S_TEXT+ hSdata
d1
„start— L_MXT
d1
LSdata-i- rSbss
_start:
dw
```
  0- _start calll- _start a112- _start 4 1J sercal13- _start 0
  ; end mark (zero)

) Module name, flag. 11 character ASCII code. The first four letters are set to "MAIN." The flag is fixed at 0. (2) Version
`$0000`-`$0099`:
prerelease version
`$0100`-
release version
Type
: 0: normal type
Link module pointer `$00000000`:
no link module
Module size (ROM size) Total number of bytes of data to be initialized with the program code. Start address A relative address given by a subprogram header in order to set a jump table Work RAM address Total number of bytes of initialized and uninitialized data. Data table set to the jump table usercal10:
initialization routine
usercal11:
main routine
usercal12:
level 2 interrupt routine
_usercal13: user defined routine (cannot be called from the system)

# 5. Jump Table and User Calls

,

## 5-1 Structure of the Jump Table

The Jump Table is the area where the CD-SYSTEM program and application program commonly access, communicate, and control.
They have the following characteristics:
- By executing CD-BIOS calls through this area, it will not be necessary to change t
  application program when the CD-BIOS is upgraded.
- Enables the change of processing exceptions.
- By using links such as these during execution (dynamic links), the efficiency of ap
  program development will be increased.
  The common area address is defined in the include file 'cabios.i'. By includi
  o the
  source program and assembling, it will be possible to use the jump table.

## 5-2 BIOS Call Sequence

d '_buram', it is
By setting parameters in registers and calling BIOS entrie possible to use the BIOS functions.

## 5-3 User Call Sequence

- Contents
  In order to call user programs from the CD-SYSTEM program (including the boot system), four entries _usercal10,_usercal11,_usercall2, and _usercall3 have been prepared in the jump table.
  (0) ,_usercal10: An initialization routine entry. It is called prior to the enabling of level 2 interrupt processing. ,_usercal11: A main routine entry. Sets the '_usermode' value to the `d0`.w register and ge call When returning, it waits for level 2 interrupt processing to finish and gets ca ,_usercal12: A level 2 interrupt routine entry. Gets called after CD-SYSTEM processing. ,_usercal13: An user defined routine entry. Does not get called by the system.
- Application Methods
  It is possible to either use a sub program header (refer to 4-3) orippwritairectl
  e jump
  table entry has 6 bytes. By writing code here, it is possib& to cotitrol the exa programs.
  The codes which the CD-SYSTEM can write here are p, rts'
- EXAMPLE
  leve13:
  irrIP
  0,1
  2,3
  `$0000`
  4,5
  rectly, use one of the two methods below.
  ble interrupts while writing the 6 bytes. e in the order of addresses and jump codes.
  ere a "rte" is written, the next 2-5 bytes may have dubious written in them.

## 5-4 Exception Processing

The exception processing vector area (`$0`-`$FF`) is in a write protected area. Therefore, it is set up so that jumps are made to the jump table area. The jump destination after initialization is a return. Or alternatively, it is set in the error processing routine (Error processing only goes through the reset process.) By rewriting the jump destination, it is possible to change exception processing. However, the following entries are exclusive to the CD-SYSTEM; therefore, they must not be changed. _1eve12, Jeve14, Jeve15,_1eve16 When a fatal error occurs, call SP by doing a hard initialization. Let the MAIN-OP
ow bout
the fatal error by means of SP.
fr

# 6. Boot System

"I CD-Boot (Boot System)

#### `CBTINIT` — CD Boot Initial

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdboot |  |
| IN |  | deLw function number (CBTINIT) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | Initializes the boot system. Cancel booting. |
| NOTE |  |  |
| SAMPLE |  |  |

```asm
move.w
jsr
#CBTINIT, d0
_cdboot
```

#### `CBTINT` — CD Boot Int

| Field | Value | Description |
| --- | --- | --- |
| Content | Ag |  |
| ENTRY | _cdboot |  |
| IN | `d0`.w | function number (CBTINT) |
| OUT |  | none |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | Calls the routine to manage interrupts. |
| NOTE | Call this entry every 16.6 ms |  |
| SAMPLE |  |  |

```asm
move.w
jsr
#CB
_cd
```

#### `CBTOPENDISC` — oot Open Disc

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | cdboot |  |
| IN | dø.w | functiontomber (CDTOPENDISC) |
| OUT |  | cc/cs OK/ |
| BREAK | `d0`/`d1`/a |  |
| FUNC | Requests to open the lo4ing tray. | 1 |
| NOTE | U es Df:VOPEN of ' cdbios. Returns BUSY only when interrupts are being | died bRy C SAMPK #CBTOPENDISC, `d0` cdboot |

#### `CBTOPENSTAT` — CD Boot Open Status

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdboot |  |
| IN | `d0`.w | function number (CBTOPENSTAT) |
| OUT |  | cc/cs COMPLETE/BUSY |
| BREAK | dø/`d1`/`a0`/`a1` |  |
| FUNC | Checks the completion of the request to open the loading tray. |  |
| NOTE |  |  |
| SAMPLE |  |  |

```asm
loop:
move.w
#CBTOPENSTAT, des
jsr
_cdboot
bcs.s
loop
```

#### `CBTCHKDISC` — CD Boot Check Disc

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdboot |  |
| IN |  | caw function number (CBTCHKDISC) `a0` pointer to scratch RAM(`$800`) |
| OUT |  | cc/cs OK/BUSY |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Requests to check whether a boot can be do |  |
| NOTE | Returns BUSY only when interrupts are bei |  |
| SAMPLE |  |  |

```asm
move.w
jsr
#CBTCHKDISC
_cdboot
```

#### `CBTCHKSTAT`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _cdboot |  |
| IN | de.w | function number (C |
| OUT |  | cc/cs COMPLETE/BUSY `d0`.w disc type 4 |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Checks bo 0mpH 1 and returns disk type |  |
| NOTE |  | disc type -1: not y 0: no dis c disc rom disc : mixed disc game system disc game data disc game boot disc game disc |

```asm
hoop:
move.w
#CBTCHKSTAT, d0
jsr
_cdboot
bcs.s
```

| Field | Value | Description |
| --- | --- | --- |
| NOTE |  | loop 1- |

# 7. Back-up RAM

## 7-1 Back-up RAM

| Entry | Description |
| --- | --- |
| Item | MEGA-CD I/F Board (Development board) |
| Text | At the time of power on, WRITE PROTECT is in effect. SUB-CPU side \`$800000\` (WORD ACCESS) |
| Text | )4800001 in case of Byte Access. |
| Text | bite |
| Text | 2M RAM |
| Text | 7 0: Disable (Writing) |
| Text | bitl |
| Text | Included inside the Back-up RAM |
| Text | _J 1: Enable (Writing) |
| Text | Since this function is implemented only for the development board, please do no released version. |
| Text | Precaution |
| Text | 1. If BIOS is called when WRITE PROTECT is on, the following occ |

#### `BRMINT` — If not formatted, treated as if no RAM were present.

| Field | Value |
| --- | --- |
| Content | BRAMFORMAT |
| Content | Returns error. |
| Content | ,CD BRAMVERIFY |
| Content | Returns "no match" unless the same filenam,e d contents have been written. |
| Content | 2. A file of more than 8 KB size can be used for t |
| Content | ack-up RAMndge. |
| Content | k- p RAM Initiazation |

#### `BRMINT`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number |
| IN | `a0`.I | pointer to scratc Temporary work al .1 pointer to display e: 12 bytes) strings. |
| OUT |  | Pointer to the buffer cc/cs OK/ERROR cc: SEGA ed RAM is present of back-up ram $ )1100(000) bytes cs: N Iformatted no RAM e of back-up ram 0: No RAM Not formatted Other format o display strings |
| FUNC | , rep | rite into and read from Back-up RAM. Makes the table for the data profThSction. OTE. Do not destroy the scratch RAM during the BRMXXX functions. |

```asm
E:
lea.l
scratch_RAM, a0
lea.l
systemname, a1
move.w
#BRMINT, d0
jsr
_buram
bcs.s
backupRAMformat
bcc.s
```

| Field | Value | Description |
| --- | --- | --- |
| FUNC |  | OK |

#### `BRMSTAT` — Back-up RAM Status

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMSTAT) |
| IN | `a1`.I | pointer to display string buffer (size: 12 bytes) |
| OUT |  | de.w number of blocks of free area dl .w number of files in directory |
| BREAK | none |  |
| FUNC | Returns how much Back-up RAM has been used. |  |
| NOTE | The free block are treated as one file. When treated as more than two files, | overflow error may occur when writing the directory. When the number loc and files are negative, no file can be accessed, formatting is needed. |
| SAMPLE |  |  |

```asm
move.w
#BRMSTAT. d0
jsr
buram
```

#### `BRMSERCH`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMSERCH) |
| IN | `a0`.I | pointer to parameter table file_name. 11 file name (ASCII code [ 0-9 A- zero. I 0 |
| OUT |  | cc/cs found/not found `d0`.w number of blocks `d1`.b mode 0: normal -1: d `a0`.I backup ram start add |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | Search for the desired file |
| NOTE |  | 11 ASCII characters are u |
| SAMPLE |  |  |

```asm
table:
db
'FILE_NAME__
subroutine:
lea.l
c), a0
moved #BR RCH, d0
Sr
bura
b,cs.s
not fo nd
Oks
1_
```

#### `BRMREAD` — Back-up RAM Read

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMREAD) |
| IN | `a0`.I | pointer to parameter table |
| IN | file_name.11 | file name (ASCII code [ 0-9 A-Z _ ]) |
| IN | zero.1 | 0 al .1 pointer to write buffer |
| OUT |  | cc/cs OK/ERROR `d0`.w number of blocks dl.b mode 0: normal -1: data protected |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Reads data form Back-up RAM |  |
| NOTE |  | Read size is in multiples of `$20` bytes with the data protect function a multiples of `$40` bytes with no data protect function. 11 characters of AS are used for the file name. |
| SAMPLE |  |  |

```asm
table:
db
'FILE_NAME__'
subroutine:
lea.l
table(pc), a0
lea.l
write_buffer, a1
move.w
#BRMREAD, d0
jsr
buram
```

#### `BRMWRITE`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number / MWRITE) |
| IN | `a0`.1 | pointer to param4 r table -+ file_name. 11 file n (ASCII cod 0-9 A-Z _]) |
| IN | flag.b | `$00`: n `$FF`. ode (with protect function) |
| IN | block_size.w | flag.`$00`: 40 byte flag=`$FF`: 1 block=`$20` byte data ROR complete/cannot write in the file al.' point |
| OUT |  | cc/cs 0 |
| BREAK | `d0`/`d1`/a 'al |  |
| FUNC | Writes ciat in Back- RAM |  |
| NOTE | S e siz | s of `$20` bytes with the data protect function and in I .;.c. of Prtes with no protect function. 11 characters of ASCII code are used foiikjile name. SAM table: 'FILE_NAME__', -1 `$0008` table(pc), `a0` save_data, al #BRMWRITE, `d0` subro |

```asm
e:
lea.l
lea.l
move.w
jsr
bcs.s
bcc.s
```

| Field | Value | Description |
| --- | --- | --- |
| NOTE |  | buram error complete |

#### `BRMDEL` — Back-up RAM Delete

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMDEL) |
| IN | `a0`.1 | pointer to parameter table filename. 11 file name (ASCII code [ 0-9 _]) zero. I 0 - |
| OUT |  | cc/cs deleted/file not found |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Deletes data on Back-up RAM |  |
| SAMPLE |  |  |

```asm
table:
db
'FILE_NAME__', 0
subroutine:
lea. I
table (pc), a0
move.w
#BRMDEL, d0
jsr
buram
```

#### `BRMFORMAT`

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMFORMAT) |
| OUT |  | cc/cs OK/ERROR (formatted/cannot for |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC |  | First initializes the directory, then fo |
| NOTE |  | Initialize first |
| SAMPLE |  |  |

```asm
jsr
move.w
```

#### `BRMDIR` — Back-up RAM Directory

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN | `d0`.w | function number (BRMD1R) |
| IN | `d1`.1 | H: number of files to skip when cannot read all the files in one try. L: size of directory buffer (number of files that can be read in the directory buffer.) |
| IN | `a0`.1 | pointer to parameter table file_name. 11 Template file name (ASCII code [ 0-9 A-Z _*]) |
| IN | zero.1 | 0 al .1 pointer to directory buffer |
| OUT |  | cc/cs OK/FULL (complete/too much to read into directory buffer) |
| BREAK | `d0`/`d1`/`a0`/al |  |
| FUNC | Reads directory |  |
| NOTE |  |  |
| SAMPLE |  | table: 'FILE_NAME__', 0 |

```asm
db
subroutine:
table (pc), a0
directorybuffer, a1
#DIRECTORYBUFFERSIZE. d1
#BRMDIR, d0
lea.l
lea.l
moveq.1
move.w
jsr
bcs.s
buram
4
dirbufferfull
```

#### `BRMVERIFY` — Back-up RAM Verify

| Field | Value | Description |
| --- | --- | --- |
| ENTRY | _buram |  |
| IN |  | caw function number (BRMVERIFY) |
| IN | `a0`.I | pointer to parameter table |
| IN | file_name.11 | File name (ASCII code [ 0-9 A-Z_ ]) |
| IN | flag.b | `$00`: normal `$FF`: encode (with protect function) |
| IN | block_size.w | flag$00: 1 block---`$40` byte flag$FF: 1 block.`$20` byte al .1 pointer to save data |
| OUT |  | cc/cs OK/ERROR `d0`.w Error No. -1: Data does not match 0: File not found |
| BREAK | `d0`/`d1`/`a0`/`a1` |  |
| FUNC | Checks data written on back-up RAM. |  |
| NOTE | Save size is in multiples of `$20` bytes with the data protect function and i | multiples of `$40` bytes with no data protect function. 11 characters of ASC ode are used for the file name. |
| SAMPLE |  |  |

```asm
table:
db
"FILE NAME__", -1
dw
$0008
subroutine:
lea.l
table(pc), a
lea.l
save_d
move.w
#BRM
jsr
_bura
bcs.s
error
bra.s
compl
error:
tst.w
de
beq.s
I filenotfound
bne.s
d error
```

### MEGA-CD load sample

```asm
loadsub
IN
d1.1
load size (byte)
a1
load start address on disc
MAXERRWAITCNTO equ (60*10)
MAXERRWAITCNT1 equ 6
loadsub:
enter_subroutine
lea.l
cbtreadsct(a5), a0
move.I
Isr.1
Isr.1
move.I
a1 , d0
#8, d0
#3, d0
d0, (a0)
; read start sector#
divu.w
#75, d0
swap
d0
call
hex2bcd
move.b
d0, cdbfrm (a5)
move.I
Isr.1
Isr.1
d1, d0
#8, d0
#3, d0
#$07ff, , d1
?11
#1, d0
and.w
beq.s
addq.I
?11:
d size (number of sector)
move .1
move.w
d0, 4 (a0)
d0, cbtreadc n5)
?retry:
sct(a5), a0
DN, d0
#R0
_cdbios
#MAXE
RWAITCNTO, d7
lea.l
move.w
callf
move.w
?null:
itd7
?loop:
move.w
DCSTAT, d0
dbios
Ilf
di
<42?,
cs.s
ove.b
ove.w
allf
bcs.s
, ?null'
?retry
#CDCMDSUBCPU, pcdcmode
#CDCREAD, d0
_cdbios
?retry
;check header
Isr.w
#8, d0
cmp.b
cdbfrm(a5), d0
bne.s
?retry
movea.I
ploadbuf(a5), a0
lea.l
cbthdrbuf(a5), a1
move.w
#CDCTRN, d0
callf
_cdbios
bcs.s
?retry
;check header
move.I
cbthdrbuf(a5), d0
Isr.w
#8, d0
cmp.b
cdbfrm(a5), d0
bne.s
?retry
moveq.1
#1, d1
move.w
#PBITCCRZERO, ccr
abcd
d1 , d0
cmpi.b
#$75, d0
bcs.s
?cl
moveq.I
#0, d0
?cl:
move.b
d0, cdbfrm(a5)
move.l
a0, ploadbuf(a5)
move.w
#CDCACK, d0
callf
_cdbios
move.w
#MAXERRWAITCNT1, d7
addq.I
#1, cbtreadsct(a5)
subq.I
#1, cbtreadnum
subq.w
#1, cbtreadcn
bne.s
?loop
leave_subroutine
```

SEGA ENTERPRISES, LTD.
2-12, HANEDA 1-CHOME, OHTA-KU, TOKYO 144, JAPAN
