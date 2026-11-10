"""Flask web layer for the BJT voltage-divider DC bias calculator."""

from __future__ import annotations

import math

from flask import Flask, render_template, request

from dc_bias import (
    VCE_NEAR_SAT,
    VCE_SAT,
    DcBiasInput,
    DcBiasResult,
    ValidationError,
    calculate_dc_bias,
)

DASH = "—"

DEFAULT_FORM = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
    "unit": "kohm",
}

REGION_LABELS = {
    "active": "Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
    "near-saturation": "Near-saturation",
}


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


def _to_ohms(raw: str | None, unit: str, label: str) -> float:
    value = _parse_float(raw, label)
    if unit == "kohm":
        return value * 1000.0
    if unit == "ohm":
        return value
    raise ValueError("หน่วยตัวต้านทานไม่ถูกต้อง")


def _format_result(result) -> dict[str, str]:
    return {
        "vb": f"{result.vb:.3f}",
        "ve": f"{result.ve:.3f}",
        "vc": f"{result.vc:.3f}",
        "vce": f"{result.vce:.3f}",
        "ic": f"{result.ic * 1e3:.3f}",
        "ie": f"{result.ie * 1e3:.3f}",
        "ib": f"{result.ib * 1e6:.2f}",
        "vth": f"{result.vth:.3f}",
        "rth": f"{result.rth / 1e3:.2f}",
        "region": REGION_LABELS[result.region],
    }


def _diagram_labels(form) -> dict[str, str]:
    """Labels for the schematic: raw input text with its unit, never parsed."""
    symbol = "Ω" if (form.get("unit") or "").strip() == "ohm" else "kΩ"

    def label(key: str, suffix: str) -> str:
        text = (form.get(key) or "").strip()
        if not text:
            return DASH
        return f"{text} {suffix}".strip()

    beta = (form.get("beta") or "").strip()
    return {
        "vcc": label("vcc", "V"),
        "r1": label("r1", symbol),
        "r2": label("r2", symbol),
        "rc": label("rc", symbol),
        "re": label("re", symbol),
        "beta": f"β = {beta}" if beta else DASH,
    }


def _status_note(result: DcBiasResult) -> dict[str, str]:
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
        "text": "Cutoff — VTH ≤ VBE กระแสเป็นศูนย์ ทรานซิสเตอร์ยังไม่นำกระแส",
    }


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", form=DEFAULT_FORM, error=None)

    @app.post("/calculate")
    def calculate():
        form = request.form
        try:
            unit = form.get("unit", "kohm")
            inp = DcBiasInput(
                vcc=_parse_float(form.get("vcc"), "VCC"),
                r1=_to_ohms(form.get("r1"), unit, "R1"),
                r2=_to_ohms(form.get("r2"), unit, "R2"),
                rc=_to_ohms(form.get("rc"), unit, "RC"),
                re=_to_ohms(form.get("re"), unit, "RE"),
                beta=_parse_float(form.get("beta"), "β"),
                vbe=_parse_float(form.get("vbe"), "VBE"),
            )
            result = calculate_dc_bias(inp)
        except (ValidationError, ValueError) as exc:
            return render_template("index.html", form=form, error=str(exc))

        return render_template(
            "index.html",
            form=form,
            error=None,
            result=result,
            values=_format_result(result),
        )

    return app


app = create_app()
