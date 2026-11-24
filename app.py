"""Flask web layer for the BJT amplifier simulator (Lab 04).

Two families of results live here and must never be mixed:

* **Analytical** — ``dc_bias.py`` (Lab 3), approximate β/VBE model.
* **SPICE** — ``spice_engine.py`` + real ngspice runs for the CE reference.

Every SPICE number shown in the page comes from a run in this request; when
the engine is missing or fails the page reports the error instead of showing
stale or fabricated data.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from flask import Flask, render_template, request

import spice_engine
from dc_bias import (
    VCE_NEAR_SAT,
    VCE_SAT,
    BiasResult,
    DcBiasInput,
    DcBiasResult,
    EmitterBiasInput,
    FixedBiasInput,
    ValidationError,
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)
from plotting import bode_svg, tran_svg
from spice_engine import (
    CeParams,
    SpiceError,
    SpiceInputError,
    SpiceUnavailableError,
)

DASH = "—"

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

MODE_TABS = {
    "divider": "Divider",
    "fixed": "Fixed",
    "emitter": "Emitter",
}

ANALYSIS_LABELS = {
    "dc": "DC",
    "ac": "AC",
    "tran": "Transient",
}

ANALYSIS_HINTS = {
    "dc": "Operating point (.op) — VB, VE, VC, VCE, IC",
    "ac": "Frequency response (.ac) — Gain (dB) และ Phase",
    "tran": "Waveform (.tran) — Vin / Vout ตามเวลา",
}

UNITS: dict[str, tuple[str, float]] = {
    "kohm": ("kΩ", 1e3),
    "ohm": ("Ω", 1.0),
    "mohm": ("MΩ", 1e6),
}
DEFAULT_UNIT = "kohm"

DEFAULT_FORMS: dict[str, dict[str, str]] = {
    "divider": {
        "vcc": "12",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
        "cin": "10",
        "cout": "10",
        "rl": "10",
        "amp": "10",
        "freq": "1000",
    },
    "fixed": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.70",
    },
    "emitter": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
    },
}

RESISTOR_FIELDS = {
    "divider": ("r1", "r2", "rc", "re", "rl"),
    "fixed": ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}

DEFAULT_FORM = DEFAULT_FORMS["divider"]

REGION_LABELS = {
    "active": "Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
    "near-saturation": "Near-saturation",
}


# --------------------------------------------------------------------------
# parsing helpers
# --------------------------------------------------------------------------

def _parse_float(raw: str | None, label: str) -> float:
    text = (raw or "").strip()
    if not text:
        raise ValueError(f"กรุณากรอก {label} เป็นตัวเลข")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"กรุณากรอก {label} เป็นตัวเลข") from exc
    if not math.isfinite(value):
        raise ValueError(f"กรุณากรอก {label} เป็นตัวเลข")
    return value


def _unit_symbol(unit: str) -> str:
    return UNITS.get(unit, UNITS[DEFAULT_UNIT])[0]


def _field_unit(form: Mapping[str, str], key: str) -> str:
    return (form.get(f"{key}_unit") or DEFAULT_UNIT).strip()


def _to_ohms(raw: str | None, unit: str, label: str) -> float:
    value = _parse_float(raw, label)
    if unit not in UNITS:
        raise ValueError(f"หน่วยของ {label} ไม่ถูกต้อง")
    return value * UNITS[unit][1]


def _mode_from(raw: str | None) -> str | None:
    text = (raw or "").strip()
    return text if text in MODE_LABELS else None


def _analysis_from(raw: str | None) -> str:
    text = (raw or "").strip()
    return text if text in ANALYSIS_LABELS else "dc"


def _unit_options(form: Mapping[str, str], key: str) -> list[dict[str, str]]:
    current = _field_unit(form, key)
    return [
        {"value": code, "symbol": symbol, "selected": " selected" if code == current else ""}
        for code, (symbol, _factor) in UNITS.items()
    ]


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------

def _format_result(result: DcBiasResult | BiasResult) -> dict[str, str]:
    return {
        "vb": f"{result.vb:.3f}",
        "ve": f"{result.ve:.3f}",
        "vc": f"{result.vc:.3f}",
        "vce": f"{result.vce:.3f}",
        "ic": f"{result.ic * 1e3:.3f}",
        "ie": f"{result.ie * 1e3:.3f}",
        "ib": f"{result.ib * 1e6:.2f}",
        "region": REGION_LABELS[result.region],
    }


def _workings(mode: str, result: DcBiasResult | BiasResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if mode == "divider":
        rows.append({"label": "VTH", "value": f"{result.vth:.3f} V"})
        rows.append({"label": "RTH", "value": f"{result.rth / 1e3:.2f} kΩ"})
    rows.append({"label": "IB", "value": f"{result.ib * 1e6:.2f} µA"})
    rows.append({"label": "IE", "value": f"{result.ie * 1e3:.3f} mA"})
    return rows


def _diagram_labels(form: Mapping[str, str], mode: str = "divider") -> dict[str, str]:
    """Labels for the schematic: raw input text with that field's own unit."""

    def label(key: str) -> str:
        text = (form.get(key) or "").strip()
        if not text:
            return DASH
        return f"{text} {_unit_symbol(_field_unit(form, key))}".strip()

    beta = (form.get("beta") or "").strip()
    labels = {
        "vcc": f"{(form.get('vcc') or '').strip()} V".strip() if (form.get("vcc") or "").strip() else DASH,
        "beta": f"β = {beta}" if beta else DASH,
        "cin": f"{(form.get('cin') or '').strip()} µF".strip() if (form.get("cin") or "").strip() else DASH,
        "cout": f"{(form.get('cout') or '').strip()} µF".strip() if (form.get("cout") or "").strip() else DASH,
    }
    for key in RESISTOR_FIELDS.get(mode, ()):
        labels[key] = label(key)
    return labels


def _status_note(result: DcBiasResult | BiasResult) -> dict[str, str]:
    """Short status sentence for the results panel, derived from the region."""
    if result.region == "active":
        return {
            "tone": "ok",
            "text": f"Active region — VCE = {result.vce:.2f} V > {VCE_SAT:g} V ทำงานในช่วงขยาย",
        }
    if result.region == "near-saturation":
        return {
            "tone": "warn",
            "text": f"Near Saturation — VCE = {result.vce:.2f} V ต่ำกว่า {VCE_NEAR_SAT:g} V ผลอาจคลาดเคลื่อน",
        }
    if result.region == "saturation":
        return {
            "tone": "danger",
            "text": f"Saturation — VCE = {result.vce:.2f} V ต่ำกว่า {VCE_SAT:g} V ค่าที่ได้ไม่น่าเชื่อถือ",
        }
    return {
        "tone": "danger",
        "text": "Cutoff — กระแสเป็นศูนย์ ทรานซิสเตอร์ยังไม่นำกระแส",
    }


def _nice_hz(value: float | None) -> str:
    if value is None:
        return "ไม่พบในช่วงที่กวาด"
    if value >= 1e6:
        return f"{value / 1e6:.2f} MHz"
    if value >= 1e3:
        return f"{value / 1e3:.2f} kHz"
    return f"{value:.2f} Hz"


def _volts(value: float) -> str:
    return f"{value:.3f} V" if abs(value) >= 1 else f"{value * 1e3:.2f} mV"


# --------------------------------------------------------------------------
# SPICE
# --------------------------------------------------------------------------

def _ce_params(form: Mapping[str, str]) -> CeParams:
    """Build validated SI parameters from the form (units converted here)."""
    return CeParams(
        vcc=_parse_float(form.get("vcc"), "VCC"),
        r1=_to_ohms(form.get("r1"), _field_unit(form, "r1"), "R1"),
        r2=_to_ohms(form.get("r2"), _field_unit(form, "r2"), "R2"),
        rc=_to_ohms(form.get("rc"), _field_unit(form, "rc"), "RC"),
        re=_to_ohms(form.get("re"), _field_unit(form, "re"), "RE"),
        rl=_to_ohms(form.get("rl"), _field_unit(form, "rl"), "RL"),
        cin=_parse_float(form.get("cin"), "CIN") * 1e-6,
        cout=_parse_float(form.get("cout"), "COUT") * 1e-6,
        beta=_parse_float(form.get("beta"), "β"),
        amplitude=_parse_float(form.get("amp"), "แอมพลิจูด") * 1e-3,
        frequency=_parse_float(form.get("freq"), "ความถี่"),
    )


def _engine_state() -> dict[str, object]:
    binary = spice_engine.find_ngspice()
    return {
        "available": binary is not None,
        "path": str(binary) if binary else "",
        "version": spice_engine.engine_version(binary) if binary else "",
        "model": spice_engine.MODEL_NAME,
    }


def _empty_sim(analysis: str) -> dict[str, object]:
    return {
        "analysis": analysis,
        "status": "idle",
        "error": None,
        "op": None,
        "ac": None,
        "tran": None,
        "plot": "",
        "run": None,
        "engine": _engine_state(),
    }


def _run_simulation(form: Mapping[str, str], analysis: str) -> dict[str, object]:
    sim = _empty_sim(analysis)
    try:
        params = _ce_params(form)
        if analysis == "dc":
            op, run = spice_engine.run_op(params)
            sim["op"] = {
                "vb": f"{op.vb:.3f}",
                "ve": f"{op.ve:.3f}",
                "vc": f"{op.vc:.3f}",
                "vce": f"{op.vce:.3f}",
                "ic": f"{op.ic * 1e3:.3f}",
                "ib": f"{op.ib * 1e6:.2f}",
                "ie": f"{op.ie * 1e3:.3f}",
            }
        elif analysis == "ac":
            ac, run = spice_engine.run_ac(params)
            sim["ac"] = {
                "gain_db": f"{ac.midband_gain_db:.2f}",
                "gain": f"{ac.midband_gain:.2f}",
                "phase": f"{ac.phase_deg:.1f}",
                "f_low": _nice_hz(ac.f_low),
                "f_high": _nice_hz(ac.f_high),
                "start": _nice_hz(ac.start_hz),
                "stop": _nice_hz(ac.stop_hz),
                "points": len(ac.points),
            }
            sim["plot"] = bode_svg(ac.points)
        else:
            tran, run = spice_engine.run_tran(params)
            sim["tran"] = {
                "vin_peak": _volts(tran.vin_peak),
                "vout_peak": _volts(tran.vout_peak),
                "gain": f"{tran.gain:.2f}",
                "inverted": tran.inverted,
                "t_start": f"{tran.t_start * 1e3:.2f} ms",
                "t_stop": f"{tran.t_stop * 1e3:.2f} ms",
                "points": len(tran.points),
            }
            sim["plot"] = tran_svg(tran.points)
        sim["status"] = "ok"
        sim["run"] = {
            "engine": run.engine,
            "version": run.version,
            "model": run.model,
            "duration": f"{run.duration_s * 1e3:.0f} ms",
            "netlist": run.netlist,
            "log": run.log_tail,
        }
    except SpiceUnavailableError as exc:
        sim["status"] = "error"
        sim["error"] = str(exc)
    except SpiceInputError as exc:
        sim["status"] = "error"
        sim["error"] = f"ค่าอินพุตไม่ถูกต้อง — {exc}"
    except SpiceError as exc:
        sim["status"] = "error"
        sim["error"] = f"การจำลองล้มเหลว — {exc}"
    except ValueError as exc:
        sim["status"] = "error"
        sim["error"] = str(exc)
    return sim


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _render(
    mode: str,
    form: Mapping[str, str],
    *,
    analysis: str = "dc",
    error: str | None = None,
    result: DcBiasResult | BiasResult | None = None,
    values: dict[str, str] | None = None,
    status: dict[str, str] | None = None,
    workings: list[dict[str, str]] | None = None,
    sim: dict[str, object] | None = None,
) -> str:
    sim = sim or _empty_sim(analysis)
    form = {**DEFAULT_FORMS[mode], **form}
    return render_template(
        "index.html",
        form=form,
        mode=mode,
        mode_label=MODE_LABELS[mode],
        tabs=MODE_TABS,
        analysis=analysis,
        analysis_labels=ANALYSIS_LABELS,
        analysis_hint=ANALYSIS_HINTS[analysis],
        resistor_fields=RESISTOR_FIELDS[mode],
        unit_options={key: _unit_options(form, key) for key in RESISTOR_FIELDS[mode]},
        diagram=_diagram_labels(form, mode),
        error=error,
        result=result,
        values=values,
        status=status,
        workings=workings,
        sim=sim,
        spice_supported=(mode == "divider"),
    )


def _analytical(form: Mapping[str, str], mode: str) -> tuple[DcBiasResult | BiasResult, dict[str, str], dict[str, str], list[dict[str, str]]]:
    unit_ok = all(_field_unit(form, key) in UNITS for key in RESISTOR_FIELDS[mode])
    if not unit_ok:
        bad = next(key for key in RESISTOR_FIELDS[mode] if _field_unit(form, key) not in UNITS)
        raise ValueError(f"หน่วยของ {bad.upper()} ไม่ถูกต้อง")

    vcc = _parse_float(form.get("vcc"), "VCC")
    beta = _parse_float(form.get("beta"), "β")
    vbe = _parse_float(form.get("vbe"), "VBE")

    if mode == "divider":
        result: DcBiasResult | BiasResult = calculate_dc_bias(
            DcBiasInput(
                vcc=vcc,
                r1=_to_ohms(form.get("r1"), _field_unit(form, "r1"), "R1"),
                r2=_to_ohms(form.get("r2"), _field_unit(form, "r2"), "R2"),
                rc=_to_ohms(form.get("rc"), _field_unit(form, "rc"), "RC"),
                re=_to_ohms(form.get("re"), _field_unit(form, "re"), "RE"),
                beta=beta,
                vbe=vbe,
            )
        )
    elif mode == "fixed":
        result = calculate_fixed_bias(
            FixedBiasInput(
                vcc=vcc,
                rb=_to_ohms(form.get("rb"), _field_unit(form, "rb"), "RB"),
                rc=_to_ohms(form.get("rc"), _field_unit(form, "rc"), "RC"),
                beta=beta,
                vbe=vbe,
            )
        )
    else:
        result = calculate_emitter_bias(
            EmitterBiasInput(
                vcc=vcc,
                rb=_to_ohms(form.get("rb"), _field_unit(form, "rb"), "RB"),
                rc=_to_ohms(form.get("rc"), _field_unit(form, "rc"), "RC"),
                re=_to_ohms(form.get("re"), _field_unit(form, "re"), "RE"),
                beta=beta,
                vbe=vbe,
            )
        )
    return result, _format_result(result), _status_note(result), _workings(mode, result)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        mode = request.args.get("mode", "divider")
        analysis = _analysis_from(request.args.get("analysis"))
        if mode not in MODE_LABELS:
            return _render(
                "divider",
                DEFAULT_FORMS["divider"],
                analysis=analysis,
                error="โหมดวงจรไม่ถูกต้อง",
            )
        return _render(mode, DEFAULT_FORMS[mode], analysis=analysis)

    @app.post("/calculate")
    def calculate():
        form = request.form
        mode = _mode_from(form.get("mode"))
        if mode is None:
            return _render(
                "divider",
                DEFAULT_FORMS["divider"],
                error="โหมดวงจรไม่ถูกต้อง",
            )
        try:
            result, values, status, workings = _analytical(form, mode)
        except (ValidationError, ValueError) as exc:
            return _render(mode, form, error=f"{MODE_LABELS[mode]} — {exc}")

        return _render(
            mode,
            form,
            result=result,
            values=values,
            status=status,
            workings=workings,
        )

    @app.post("/simulate")
    def simulate():
        form = request.form
        mode = _mode_from(form.get("mode"))
        analysis = _analysis_from(form.get("analysis"))
        if mode is None:
            return _render(
                "divider",
                DEFAULT_FORMS["divider"],
                analysis=analysis,
                error="โหมดวงจรไม่ถูกต้อง",
            )
        if mode != "divider":
            return _render(
                mode,
                form,
                analysis=analysis,
                error="การจำลอง SPICE รองรับเฉพาะวงจร CE Voltage Divider",
            )

        sim = _run_simulation(form, analysis)

        analytical = None
        analytical_values = None
        analytical_status = None
        workings = None
        try:
            analytical, analytical_values, analytical_status, workings = _analytical(form, mode)
        except (ValidationError, ValueError):
            analytical = None

        return _render(
            mode,
            form,
            analysis=analysis,
            sim=sim,
            result=analytical,
            values=analytical_values,
            status=analytical_status,
            workings=workings,
            error=None if sim["status"] == "ok" else str(sim.get("error") or ""),
        )

    return app


app = create_app()
