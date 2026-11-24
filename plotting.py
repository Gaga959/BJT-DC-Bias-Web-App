"""Server-side SVG plots for the Lab 04 simulator.

The plots are drawn from real ngspice data only. They are plain strings so the
template can embed them without any JavaScript or chart library.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from spice_engine import AcPoint, TranPoint

TEAL = "#0f766e"
ORANGE = "#c2410c"
GRID = "#dbe4ee"
AXIS = "#64748b"
TEXT = "#334155"


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _nice_freq(hz: float) -> str:
    if hz >= 1e6:
        return f"{hz / 1e6:g} MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:g} kHz"
    return f"{hz:g} Hz"


def _nice_volt(value: float, unit: str) -> str:
    return f"{value:g} {unit}"


def _ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high <= low:
        return [low]
    step = (high - low) / count
    return [low + step * i for i in range(count + 1)]


def _fmt(value: float, digits: int = 1) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _polyline(points: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _frame(width: int, height: int, top: int, left: int, right: int, bottom: int) -> tuple[float, float]:
    return (width - left - right, height - top - bottom)


def bode_svg(points: Sequence[AcPoint], width: int = 620) -> str:
    """Magnitude (dB) and phase (deg) against a log frequency axis."""
    if len(points) < 2:
        return '<p class="plot-empty">ไม่มีข้อมูล AC</p>'

    left, right, top = 52, 16, 14
    mag_h, phase_h, gap = 132, 88, 34
    height = top + mag_h + gap + phase_h + 34
    plot_w, _ = _frame(width, height, top, left, right, 0)

    f0, f1 = points[0].frequency, points[-1].frequency
    log0, log1 = math.log10(f0), math.log10(f1)

    def x_of(freq: float) -> float:
        return left + (math.log10(freq) - log0) / (log1 - log0) * plot_w

    mags = [p.gain_db for p in points]
    phases = [p.phase_deg for p in points]
    mag_low, mag_high = min(mags), max(mags)
    pad = max(1.0, (mag_high - mag_low) * 0.12)
    mag_low, mag_high = mag_low - pad, mag_high + pad

    def y_mag(value: float) -> float:
        return top + mag_h - (value - mag_low) / (mag_high - mag_low) * mag_h

    phase_top = top + mag_h + gap
    ph_low, ph_high = -200.0, 200.0
    if min(phases) < ph_low or max(phases) > ph_high:
        ph_low, ph_high = min(phases) - 20, max(phases) + 20

    def y_ph(value: float) -> float:
        return phase_top + phase_h - (value - ph_low) / (ph_high - ph_low) * phase_h

    out: list[str] = [
        f'<svg class="plot" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Bode plot: ขนาดเกนและเฟสตามความถี่ จาก ngspice">'
    ]

    # decade grid + labels
    start_decade = math.ceil(log0)
    for decade in range(start_decade, math.floor(log1) + 1):
        gx = x_of(10.0 ** decade)
        out.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{phase_top + phase_h:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{gx:.1f}" y="{phase_top + phase_h + 16:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{AXIS}">{_esc(_nice_freq(10.0 ** decade))}</text>'
        )

    # magnitude grid
    for value in _ticks(mag_low, mag_high, 4):
        gy = y_mag(value)
        out.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{left + plot_w:.1f}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{left - 8}" y="{gy + 3.5:.1f}" text-anchor="end" font-size="10" fill="{AXIS}">{_fmt(value)}</text>'
        )

    # phase grid
    for value in _ticks(ph_low, ph_high, 2):
        gy = y_ph(value)
        out.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{left + plot_w:.1f}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{left - 8}" y="{gy + 3.5:.1f}" text-anchor="end" font-size="10" fill="{AXIS}">{_fmt(value)}</text>'
        )

    out.append(f'<text x="{left}" y="{top - 2}" font-size="10.5" fill="{TEXT}" font-weight="600">Gain |Vout/Vin| (dB)</text>')
    out.append(f'<text x="{left}" y="{phase_top - 6}" font-size="10.5" fill="{TEXT}" font-weight="600">Phase (deg)</text>')

    out.append(
        f'<polyline fill="none" stroke="{TEAL}" stroke-width="2" points="'
        + _polyline([(x_of(p.frequency), y_mag(p.gain_db)) for p in points])
        + '"/>'
    )
    out.append(
        f'<polyline fill="none" stroke="{ORANGE}" stroke-width="2" points="'
        + _polyline([(x_of(p.frequency), y_ph(p.phase_deg)) for p in points])
        + '"/>'
    )

    out.append(f'<line x1="{left}" y1="{phase_top + phase_h}" x2="{left + plot_w}" y2="{phase_top + phase_h}" stroke="{AXIS}" stroke-width="1"/>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{phase_top + phase_h}" stroke="{AXIS}" stroke-width="1"/>')
    out.append(
        f'<text x="{left + plot_w}" y="{height - 4}" text-anchor="end" font-size="10" fill="{AXIS}">Frequency (log)</text>'
    )
    out.append("</svg>")
    return "".join(out)


def tran_svg(points: Sequence[TranPoint], width: int = 620) -> str:
    """Input and output waveforms against time."""
    if len(points) < 2:
        return '<p class="plot-empty">ไม่มีข้อมูล Transient</p>'

    left, right, top, bottom = 56, 16, 22, 44
    height = 300
    plot_w, plot_h = _frame(width, height, top, left, right, bottom)

    t0, t1 = points[0].time, points[-1].time
    peak = max(max(abs(p.vin) for p in points), max(abs(p.vout) for p in points))
    scale, unit = (1e3, "mV") if peak < 1.0 else (1.0, "V")

    lo = min(min(p.vin, p.vout) for p in points) * scale
    hi = max(max(p.vin, p.vout) for p in points) * scale
    pad = max(0.5, (hi - lo) * 0.1)
    lo, hi = lo - pad, hi + pad

    def x_of(t: float) -> float:
        return left + (t - t0) / (t1 - t0) * plot_w

    def y_of(v: float) -> float:
        return top + plot_h - (v * scale - lo) / (hi - lo) * plot_h

    out: list[str] = [
        f'<svg class="plot" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Transient waveform: Vin และ Vout ตามเวลา จาก ngspice">'
    ]

    for value in _ticks(lo, hi, 4):
        gy = y_of(value / scale)
        out.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{left + plot_w:.1f}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{left - 8}" y="{gy + 3.5:.1f}" text-anchor="end" font-size="10" fill="{AXIS}">{_fmt(value, 2)}</text>'
        )

    for i in range(6):
        t = t0 + (t1 - t0) * i / 5
        gx = x_of(t)
        out.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{top + plot_h}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{gx:.1f}" y="{top + plot_h + 16:.1f}" text-anchor="middle" font-size="10" fill="{AXIS}">'
            f'{_fmt(t * 1e3, 2)}</text>'
        )

    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>')
    out.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>')

    out.append(
        f'<polyline fill="none" stroke="{TEAL}" stroke-width="1.8" points="'
        + _polyline([(x_of(p.time), y_of(p.vin)) for p in points])
        + '"/>'
    )
    out.append(
        f'<polyline fill="none" stroke="{ORANGE}" stroke-width="1.8" points="'
        + _polyline([(x_of(p.time), y_of(p.vout)) for p in points])
        + '"/>'
    )

    out.append(f'<text x="{left}" y="{top - 6}" font-size="10.5" fill="{TEXT}" font-weight="600">Voltage ({unit})</text>')
    out.append(f'<text x="{left + plot_w}" y="{height - 4}" text-anchor="end" font-size="10" fill="{AXIS}">Time (ms)</text>')

    # legend
    legend_y = height - 18
    out.append(f'<line x1="{left + 8}" y1="{legend_y}" x2="{left + 34}" y2="{legend_y}" stroke="{TEAL}" stroke-width="2"/>')
    out.append(f'<text x="{left + 40}" y="{legend_y + 4}" font-size="10.5" fill="{TEXT}">Vin</text>')
    out.append(f'<line x1="{left + 96}" y1="{legend_y}" x2="{left + 122}" y2="{legend_y}" stroke="{ORANGE}" stroke-width="2"/>')
    out.append(f'<text x="{left + 128}" y="{legend_y + 4}" font-size="10.5" fill="{TEXT}">Vout</text>')
    out.append("</svg>")
    return "".join(out)
