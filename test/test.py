# SPDX-FileCopyrightText: (c) 2026 Rudra Joshi
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

WR_EN = 0
RD_EN = 1
FULL = 2
EMPTY = 3

DEPTH = 16


def full(dut):
    return (int(dut.uio_out.value) >> FULL) & 1


def empty(dut):
    return (int(dut.uio_out.value) >> EMPTY) & 1


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def push(dut, value):
    dut.ui_in.value = value
    dut.uio_in.value = 1 << WR_EN
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)


async def pulse_rd(dut):
    dut.uio_in.value = 1 << RD_EN
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)


async def pop(dut):
    # rd_data is combinational on the head of the queue, so read before advancing
    value = int(dut.uo_out.value)
    await pulse_rd(dut)
    return value


@cocotb.test()
async def test_reset_state(dut):
    dut._log.info("reset")
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    await reset(dut)

    assert empty(dut) == 1, "FIFO should be empty after reset"
    assert full(dut) == 0, "FIFO should not be full after reset"
    assert int(dut.uio_oe.value) == 0b0000_1100, "uio_oe should drive only full and empty"


@cocotb.test()
async def test_single_write_read(dut):
    dut._log.info("one word in, one word out")
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    await reset(dut)

    await push(dut, 0xA5)
    assert empty(dut) == 0, "should not be empty after a write"

    got = await pop(dut)
    assert got == 0xA5, f"expected 0xA5, got {got:#04x}"
    assert empty(dut) == 1, "should be empty again after reading the only word"


@cocotb.test()
async def test_fill_and_drain_in_order(dut):
    dut._log.info("fill to full, drain, check ordering")
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    await reset(dut)

    written = [(i * 17 + 3) & 0xFF for i in range(DEPTH)]

    for i, value in enumerate(written):
        assert full(dut) == 0, f"went full early, after {i} writes"
        await push(dut, value)

    assert full(dut) == 1, f"should be full after {DEPTH} writes"
    assert empty(dut) == 0, "should not be empty when full"

    read_back = []
    for _ in range(DEPTH):
        read_back.append(await pop(dut))

    assert read_back == written, f"order mismatch\n wrote {written}\n read  {read_back}"
    assert empty(dut) == 1, "should be empty after draining"
    assert full(dut) == 0, "should not be full after draining"


@cocotb.test()
async def test_overflow_and_underflow_ignored(dut):
    dut._log.info("writes while full and reads while empty are ignored")
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    await reset(dut)

    # read while empty: must not corrupt anything.
    # uo_out is X here because the memory is uninitialised, so do not sample it.
    await pulse_rd(dut)
    assert empty(dut) == 1, "still empty after a read while empty"

    for i in range(DEPTH):
        await push(dut, i)
    assert full(dut) == 1

    # write while full: must be dropped
    await push(dut, 0xFF)
    assert full(dut) == 1, "still full after a write while full"

    read_back = [await pop(dut) for _ in range(DEPTH)]
    assert read_back == list(range(DEPTH)), f"contents corrupted: {read_back}"
    assert 0xFF not in read_back, "the dropped write leaked into the FIFO"
