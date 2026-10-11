"""Activated campaign clock. No CLI override or resume extension."""

STARTED = 1791694165
TARGET = 1791730165
DEADLINE = 1791737365
# Reserve bounded Docker inspections/stop grace plus process cleanup before the cap.
STOP_MARGIN = 300
WORK_CUTOFF = DEADLINE - STOP_MARGIN
