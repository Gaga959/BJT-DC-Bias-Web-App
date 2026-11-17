"""Flask web layer for the BJT DC bias calculator (three bias modes)."""

from __future__ import annotations

import math
from collections.abc import Mapping

from flask import Flask, render_template, request

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

DEFAULT_FORMS = {
    "divider": {
        "vcc": "12",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
        "unit": "kohm",
    },
    "fixed": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.70",
        "unit": "kohm",
    },
    "emitter": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
        "unit": "kohm",
    },
}

DEFAULT_FORM = DEFAULT_FORMS["divider"]

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
    if unit == "mohm":
        return value * 1_000_000.0
    raise ValueError("หน่วยตัวต้านทานไม่ถูกต้อง")


def _mode_from(raw: str | None) -> str | None:
    text = (raw or "").strip()
    return text if text in MODE_LABELS else None


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
    """Labels for the schematic: raw input text with its unit, never parsed."""
    symbol = {"ohm": "Ω", "mohm": "MΩ"}.get((form.get("unit") or "").strip(), "kΩ")

    def label(key: str, suffix: str) -> str:
        text = (form.get(key) or "").strip()
        if not text:
            return DASH
        return f"{text} {suffix}".strip()

    beta = (form.get("beta") or "").strip()
    labels = {
        "vcc": label("vcc", "V"),
        "beta": f"β = {beta}" if beta else DASH,
    }
    if mode == "divider":
        labels.update(
            r1=label("r1", symbol),
            r2=label("r2", symbol),
            rc=label("rc", symbol),
            re=label("re", symbol),
        )
    elif mode == "fixed":
        labels.update(rb=label("rb", symbol), rc=label("rc", symbol))
    else:
        labels.update(
            rb=label("rb", symbol),
            rc=label("rc", symbol),
            re=label("re", symbol),
        )
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


def _render(
    mode: str,
    form: Mapping[str, str],
    *,
    error: str | None = None,
    result: DcBiasResult | BiasResult | None = None,
    values: dict[str, str] | None = None,
    status: dict[str, str] | None = None,
    workings: list[dict[str, str]] | None = None,
) -> str:
    return render_template(
        "index.html",
        form=form,
        mode=mode,
        mode_label=MODE_LABELS[mode],
        tabs=MODE_TABS,
        diagram=_diagram_labels(form, mode),
        error=error,
        result=result,
        values=values,
        status=status,
        workings=workings,
    )


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        mode = request.args.get("mode", "divider")
        if mode not in MODE_LABELS:
            return _render(
                "divider",
                DEFAULT_FORMS["divider"],
                error="โหมดวงจรไม่ถูกต้อง",
            )
        return _render(mode, DEFAULT_FORMS[mode])

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
            unit = form.get("unit", "kohm")
            vcc = _parse_float(form.get("vcc"), "VCC")
            beta = _parse_float(form.get("beta"), "β")
            vbe = _parse_float(form.get("vbe"), "VBE")

            if mode == "divider":
                result = calculate_dc_bias(
                    DcBiasInput(
                        vcc=vcc,
                        r1=_to_ohms(form.get("r1"), unit, "R1"),
                        r2=_to_ohms(form.get("r2"), unit, "R2"),
                        rc=_to_ohms(form.get("rc"), unit, "RC"),
                        re=_to_ohms(form.get("re"), unit, "RE"),
                        beta=beta,
                        vbe=vbe,
                    )
                )
            elif mode == "fixed":
                result = calculate_fixed_bias(
                    FixedBiasInput(
                        vcc=vcc,
                        rb=_to_ohms(form.get("rb"), unit, "RB"),
                        rc=_to_ohms(form.get("rc"), unit, "RC"),
                        beta=beta,
                        vbe=vbe,
                    )
                )
            else:
                result = calculate_emitter_bias(
                    EmitterBiasInput(
                        vcc=vcc,
                        rb=_to_ohms(form.get("rb"), unit, "RB"),
                        rc=_to_ohms(form.get("rc"), unit, "RC"),
                        re=_to_ohms(form.get("re"), unit, "RE"),
                        beta=beta,
                        vbe=vbe,
                    )
                )
        except (ValidationError, ValueError) as exc:
            return _render(mode, form, error=f"{MODE_LABELS[mode]} — {exc}")

        return _render(
            mode,
            form,
            result=result,
            values=_format_result(result),
            status=_status_note(result),
            workings=_workings(mode, result),
        )

    return app


app = create_app()
