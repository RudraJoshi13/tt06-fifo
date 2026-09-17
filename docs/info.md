## How it works

An 8-bit wide, 16-deep synchronous FIFO. One clock domain, active-low
asynchronous reset, no latches.

Storage is a 16 by 8 register array addressed by two pointers. Each pointer
carries one extra bit beyond the address width. That extra bit is what
separates full from empty when both pointers land on the same address:
equal pointers means empty, equal addresses with differing top bits means
full.

A write is accepted on a rising clock edge when `wr_en` is high and the FIFO
is not full. A read advances the read pointer on a rising edge when `rd_en`
is high and the FIFO is not empty. `rd_data` is combinational on the read
address, so the word at the head of the queue is visible without asserting
`rd_en`.

Writes while full and reads while empty are ignored, so neither corrupts the
pointers.

## How to test

Drive the clock, release reset, then:

1. Put a byte on `ui_in` and pulse `uio[0]` (`wr_en`) high for one clock.
   Check that `uio[3]` (`empty`) goes low.
2. Read `uo_out`, which shows the word at the head of the queue.
3. Pulse `uio[1]` (`rd_en`) high for one clock to advance to the next word.
4. Write sixteen bytes without reading and check that `uio[2]` (`full`)
   goes high on the sixteenth.
5. Read all sixteen back and confirm they come out in the order written,
   and that `empty` returns high.

The cocotb testbench in `test/` covers all of the above.

## Notes on area

The same RTL has been hardened on sky130 outside Tiny Tapeout, where it came
to 1,122 standard cells in a 135.9 by 146.62 micron die at 73.3% utilisation,
closing at 100 MHz with zero violations across nine corners.

That cell count overstates the size here. Only about 450 of those cells are
the FIFO itself, 158 sequential and 289 combinational. The rest are 409
timing repair buffers and 52 clock buffers inserted to reach 100 MHz under
deliberately tight design rule constraints. At the 50 MHz target used here,
most of that repair logic should not be needed.

## External hardware

None. The demo board's RP2040 can drive the inputs and read the outputs
directly.
