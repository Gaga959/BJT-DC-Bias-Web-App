"""ngspice adapter for the reference CE voltage-divider amplifier.

Pure engineering layer: it knows SPICE, not HTTP. Every value crossing this
boundary is SI (V, ohm, F, A, Hz) and every number returned here comes from a
real ngspice run — nothing is mocked or hard-coded.

Circuit (Lab 4 reference)::

    VCC --+-- R1 --+-- base ... Q1 (NPN) ... collector --+-- RC -- VCC
          |        |                                     |
          |        R2                                    +-- COUT -- out -- RL -- GND
          |        |
         GND      GND      emitter -- RE -- GND
    VIN -- CIN -- base
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

MODEL_NAME = "QNPN (generic, IS=1e-14, VAF=100, BF จาก β ในฟอร์ม)"
MODEL_CARD = "NPN(IS=1e-14 BF={beta} VAF=100 RB=10 RC=1 RE=0.5)"

DEFAULT_TIMEOUT_S = 30.0

_NODE_VB = "v(base)"
_NODE_VE = "v(emit)"
_NODE_VC = "v(coll)"
_DEV_IC = "@q1[ic]"
_DEV_IB = "@q1[ib]"


class SpiceError(RuntimeError):
    """Base class for every simulation failure surfaced to the UI."""


class SpiceUnavailableError(SpiceError):
    """ngspice executable could not be located."""


class SpiceInputError(SpiceError):
    """Circuit parameters are outside the supported range."""


class SpiceRunError(SpiceError):
    """ngspice was found but the run or its output could not be used."""


@dataclass(frozen=True)
class CeParams:
    """Reference CE amplifier parameters in SI units."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    beta: float
    amplitude: float  # peak volts of the sine source
    frequency: float  # Hz

    @property
    def model_name(self) -> str:
        return MODEL_NAME


@dataclass(frozen=True)
class OpResult:
    vb: float
    ve: float
    vc: float
    vce: float
    ic: float
    ib: float
    ie: float


@dataclass(frozen=True)
class AcPoint:
    frequency: float
    gain_db: float
    phase_deg: float


@dataclass(frozen=True)
class AcResult:
    points: tuple[AcPoint, ...]
    midband_gain_db: float
    midband_gain: float
    phase_deg: float
    f_low: float | None
    f_high: float | None
    start_hz: float
    stop_hz: float


@dataclass(frozen=True)
class TranPoint:
    time: float
    vin: float
    vout: float


@dataclass(frozen=True)
class TranResult:
    points: tuple[TranPoint, ...]
    vin_peak: float
    vout_peak: float
    gain: float
    inverted: bool
    t_start: float
    t_stop: float


@dataclass(frozen=True)
class RunInfo:
    """Provenance for one run, shown in the UI next to the numbers."""

    analysis: str
    engine: str
    version: str
    model: str
    duration_s: float
    netlist: str
    log_tail: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def _candidate_paths() -> list[Path]:
    exe = "ngspice_con.exe" if os.name == "nt" else "ngspice"
    roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "ngspice" / "Spice64" / "bin",
        Path("C:/Program Files/ngspice/Spice64/bin"),
        Path("C:/Program Files (x86)/ngspice/Spice64/bin"),
        Path("/usr/bin"),
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin"),
    ]
    found: list[Path] = []
    for root in roots:
        if not root:
            continue
        candidate = root / exe
        if candidate.is_file():
            found.append(candidate)
    return found


def find_ngspice() -> Path | None:
    """Return the ngspice console binary, honouring ``NGSPICE_BIN`` first."""
    override = os.environ.get("NGSPICE_BIN", "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return path
        if path.is_dir():
            for name in ("ngspice_con.exe", "ngspice_con", "ngspice"):
                candidate = path / name
                if candidate.is_file():
                    return candidate
        return None

    for name in ("ngspice_con", "ngspice_con.exe", "ngspice"):
        located = shutil.which(name)
        if located:
            return Path(located)

    candidates = _candidate_paths()
    return candidates[0] if candidates else None


def engine_version(binary: Path) -> str:
    try:
        done = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_no_window(),
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    text = (done.stdout or "") + (done.stderr or "")
    match = re.search(r"ngspice-[\w.\-]+", text)
    return match.group(0) if match else "unknown"


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(params: CeParams) -> None:
    """Reject values that would produce a meaningless netlist."""
    checks = (
        (params.vcc, "VCC", 0.0, 60.0),
        (params.r1, "R1", 0.0, 1e9),
        (params.r2, "R2", 0.0, 1e9),
        (params.rc, "RC", 0.0, 1e9),
        (params.re, "RE", 0.0, 1e9),
        (params.rl, "RL", 0.0, 1e9),
        (params.cin, "CIN", 0.0, 1e6),
        (params.cout, "COUT", 0.0, 1e6),
        (params.beta, "β", 0.0, 1e4),
        (params.amplitude, "แอมพลิจูด", 0.0, 5.0),
        (params.frequency, "ความถี่", 0.0, 1e7),
    )
    for value, label, low, high in checks:
        if not (low < value <= high):
            raise SpiceInputError(
                f"{label} ต้องมากกว่า {low:g} และไม่เกิน {high:g}"
            )


# --------------------------------------------------------------------------
# netlist
# --------------------------------------------------------------------------

def _num(value: float) -> str:
    return f"{value:.6g}"


def _header(params: CeParams) -> str:
    return "\n".join(
        [
            "* ENG29 2121 Lab 04 - CE voltage divider reference",
            f".param VCC={_num(params.vcc)} R1={_num(params.r1)} R2={_num(params.r2)}",
            f".param RC={_num(params.rc)} RE={_num(params.re)} RL={_num(params.rl)}",
            f".param CIN={_num(params.cin)} COUT={_num(params.cout)}",
            f".param AMP={_num(params.amplitude)} FREQ={_num(params.frequency)}",
            f".param BETA={_num(params.beta)}",
            "VCC vcc 0 dc {VCC}",
            "VIN in 0 dc 0 ac 1 sin(0 {AMP} {FREQ})",
            "R1 vcc base {R1}",
            "R2 base 0 {R2}",
            "RC vcc coll {RC}",
            "RE emit 0 {RE}",
            "CIN in base {CIN}",
            "COUT coll out {COUT}",
            "RL out 0 {RL}",
            "Q1 coll base emit QNPN",
            ".model QNPN " + MODEL_CARD.format(beta=_num(params.beta)),
        ]
    )


def build_netlist(params: CeParams, analysis: str) -> str:
    """Return a batch netlist for ``op``, ``ac`` or ``tran``."""
    if analysis == "op":
        control = "op\nprint " + " ".join([_NODE_VB, _NODE_VE, _NODE_VC, _DEV_IC, _DEV_IB])
    elif analysis == "ac":
        control = (
            "set wr_singlescale\n"
            "set wr_vecnames\n"
            "ac dec 25 1 10meg\n"
            "wrdata ac.dat db(v(out)/v(in)) ph(v(out)/v(in))"
        )
    elif analysis == "tran":
        step, stop = tran_window(params.frequency)
        control = (
            "set wr_singlescale\n"
            "set wr_vecnames\n"
            f"tran {_num(step)} {_num(stop)}\n"
            "wrdata tran.dat v(in) v(out)"
        )
    else:
        raise SpiceInputError(f"ไม่รู้จักการวิเคราะห์ {analysis}")

    return "\n".join(
        [
            _header(params),
            ".control",
            "set noaskquit",
            control,
            ".endc",
            ".end",
            "",
        ]
    )


def tran_window(frequency: float) -> tuple[float, float]:
    """Time step and stop time covering five cycles at 200 samples/cycle."""
    period = 1.0 / frequency
    return (period / 200.0, period * 5.0)


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------

def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _run(params: CeParams, analysis: str, timeout: float) -> tuple[str, Path, float, str, Path]:
    binary = find_ngspice()
    if binary is None:
        raise SpiceUnavailableError(
            "ไม่พบ ngspice — ตั้งค่า NGSPICE_BIN หรือติดตั้ง ngspice แล้วเพิ่มลง PATH"
        )

    netlist = build_netlist(params, analysis)
    workdir = Path(tempfile.mkdtemp(prefix="bjt-spice-"))
    source = workdir / "circuit.cir"
    source.write_text(netlist, encoding="ascii", errors="replace")

    started = time.perf_counter()
    try:
        done = subprocess.run(
            [str(binary), "-b", str(source.name)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_no_window(),
        )
    except subprocess.TimeoutExpired as exc:
        raise SpiceRunError(
            f"ngspice ใช้เวลาเกิน {timeout:g} วินาที — ลดความถี่หรือจำนวนจุดแล้วลองใหม่"
        ) from exc
    except OSError as exc:
        raise SpiceUnavailableError(f"เรียก ngspice ไม่สำเร็จ: {exc}") from exc
    duration = time.perf_counter() - started

    stdout = done.stdout or ""
    stderr = done.stderr or ""
    combined = stdout + stderr

    if done.returncode != 0:
        raise SpiceRunError(
            "ngspice จบด้วยรหัส " + str(done.returncode) + "\n" + _tail(combined)
        )
    if "Error" in combined or "error" in combined:
        raise SpiceRunError("ngspice รายงานข้อผิดพลาด\n" + _tail(combined))
    if "No. of Data Rows : 0" in combined:
        raise SpiceRunError("ngspice ไม่ได้ผลลัพธ์ (0 data rows)\n" + _tail(combined))

    return combined, workdir, duration, netlist, binary


def _tail(text: str, limit: int = 600) -> str:
    text = text.strip()
    return text[-limit:] if len(text) > limit else text


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_PRINT_RE = re.compile(r"^\s*([A-Za-z@][\w@()\[\].]*)\s*=\s*([-+0-9.eE]+)\s*$", re.M)


def parse_op(stdout: str) -> OpResult:
    values = {name.lower(): float(raw) for name, raw in _PRINT_RE.findall(stdout)}
    try:
        vb = values[_NODE_VB]
        ve = values[_NODE_VE]
        vc = values[_NODE_VC]
        ic = values[_DEV_IC]
        ib = values[_DEV_IB]
    except KeyError as exc:
        raise SpiceRunError(f"อ่านผล .op ไม่ครบ (ขาด {exc.args[0]})") from exc
    return OpResult(vb=vb, ve=ve, vc=vc, vce=vc - ve, ic=ic, ib=ib, ie=ic + ib)


def _read_wrdata(path: Path) -> list[list[float]]:
    if not path.is_file():
        raise SpiceRunError(f"ไม่พบไฟล์ผลลัพธ์ {path.name}")
    rows: list[list[float]] = []
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            rows.append([float(item) for item in parts])
        except ValueError:
            continue  # header line
    if not rows:
        raise SpiceRunError(f"ไฟล์ผลลัพธ์ {path.name} ว่าง")
    return rows


def parse_ac(path: Path) -> tuple[AcPoint, ...]:
    points = [
        AcPoint(frequency=row[0], gain_db=row[1], phase_deg=_normalise_phase(row[2] * 180.0 / 3.141592653589793))
        for row in _read_wrdata(path)
    ]
    return tuple(points)


def _normalise_phase(deg: float) -> float:
    while deg <= -180.0:
        deg += 360.0
    while deg > 180.0:
        deg -= 360.0
    return deg


def analyse_ac(points: tuple[AcPoint, ...]) -> AcResult:
    if not points:
        raise SpiceRunError("ผล .ac ว่าง")
    peak = max(points, key=lambda p: p.gain_db)
    reference = peak.gain_db - 3.0103
    lower = [p for p in points if p.frequency <= peak.frequency and p.gain_db >= reference]
    upper = [p for p in points if p.frequency >= peak.frequency and p.gain_db >= reference]
    f_low = lower[0].frequency if lower and lower[0] is not points[0] else None
    f_high = upper[-1].frequency if upper and upper[-1] is not points[-1] else None
    return AcResult(
        points=points,
        midband_gain_db=peak.gain_db,
        midband_gain=10 ** (peak.gain_db / 20.0),
        phase_deg=peak.phase_deg,
        f_low=f_low,
        f_high=f_high,
        start_hz=points[0].frequency,
        stop_hz=points[-1].frequency,
    )


def parse_tran(path: Path) -> tuple[TranPoint, ...]:
    return tuple(TranPoint(time=row[0], vin=row[1], vout=row[2]) for row in _read_wrdata(path))


def analyse_tran(points: tuple[TranPoint, ...]) -> TranResult:
    if not points:
        raise SpiceRunError("ผล .tran ว่าง")
    # ignore the first 20% (charging transient of the coupling capacitors)
    start = points[0].time + (points[-1].time - points[0].time) * 0.2
    steady = [p for p in points if p.time >= start] or list(points)
    vin_peak = max(abs(p.vin) for p in steady)
    vout_peak = max(abs(p.vout) for p in steady)
    inverted = False
    vin_at = max(steady, key=lambda p: p.vin)
    nearest = min(steady, key=lambda p: abs(p.time - vin_at.time))
    inverted = nearest.vout < 0.0
    return TranResult(
        points=points,
        vin_peak=vin_peak,
        vout_peak=vout_peak,
        gain=(vout_peak / vin_peak) if vin_peak else 0.0,
        inverted=inverted,
        t_start=points[0].time,
        t_stop=points[-1].time,
    )


# --------------------------------------------------------------------------
# public entry points
# --------------------------------------------------------------------------

def _provenance(analysis: str, binary: Path, duration: float, netlist: str, log: str) -> RunInfo:
    return RunInfo(
        analysis=analysis,
        engine="ngspice",
        version=engine_version(binary),
        model=MODEL_NAME,
        duration_s=duration,
        netlist=netlist,
        log_tail=_tail(log),
    )


def run_op(params: CeParams, timeout: float = DEFAULT_TIMEOUT_S) -> tuple[OpResult, RunInfo]:
    validate(params)
    log, workdir, duration, netlist, binary = _run(params, "op", timeout)
    try:
        result = parse_op(log)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return result, _provenance("op", binary, duration, netlist, log)


def run_ac(params: CeParams, timeout: float = DEFAULT_TIMEOUT_S) -> tuple[AcResult, RunInfo]:
    validate(params)
    log, workdir, duration, netlist, binary = _run(params, "ac", timeout)
    try:
        points = parse_ac(workdir / "ac.dat")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return analyse_ac(points), _provenance("ac", binary, duration, netlist, log)


def run_tran(params: CeParams, timeout: float = DEFAULT_TIMEOUT_S) -> tuple[TranResult, RunInfo]:
    validate(params)
    log, workdir, duration, netlist, binary = _run(params, "tran", timeout)
    try:
        points = parse_tran(workdir / "tran.dat")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return analyse_tran(points), _provenance("tran", binary, duration, netlist, log)
