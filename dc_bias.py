"""BJT voltage-divider bias: DC operating point calculations.

All inputs and outputs use SI units (volts, ohms, amperes). The model is the
forward-active approximation with constant beta and constant VBE.
"""

from __future__ import annotations

from dataclasses import dataclass


class ValidationError(ValueError):
    """Raised when an input value is outside the supported physical range."""


VCE_SAT = 0.2
VCE_NEAR_SAT = 0.5


@dataclass(frozen=True)
class DcBiasInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class DcBiasResult:
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class FixedBiasInput:
    vcc: float
    rb: float
    rc: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]


def classify_region(vth: float, vbe: float, vce: float) -> tuple[str, tuple[str, ...]]:
    """Return the operating region and any warnings for the computed point."""
    if vth <= vbe:
        return (
            "cutoff",
            ("Cutoff: VTH ≤ VBE ทำให้ IB ≤ 0 — แบบจำลอง Forward-Active ใช้ไม่ได้",),
        )
    if vce < VCE_SAT:
        return (
            "saturation",
            (
                "Saturation: VCE < 0.2 V — ค่าที่ได้ไม่น่าเชื่อถือ "
                "เพราะ VCE ควรใกล้ VCE(sat) ประมาณ 0.2 V",
            ),
        )
    if vce < VCE_NEAR_SAT:
        return (
            "near-saturation",
            ("Near Saturation: VCE < 0.5 V — ผลอาจคลาดเคลื่อนจากแบบจำลอง",),
        )
    return ("active", ())


def classify_operating_point(ib: float, vce: float) -> tuple[str, tuple[str, ...]]:
    """Return the operating region for bias modes without a VTH term."""
    if ib <= 0:
        return (
            "cutoff",
            ("Cutoff: IB ≤ 0 — แบบจำลอง Forward-Active ใช้ไม่ได้",),
        )
    if vce < VCE_SAT:
        return (
            "saturation",
            (
                "Saturation: VCE < 0.2 V — ค่าที่ได้ไม่น่าเชื่อถือ "
                "เพราะ VCE ควรใกล้ VCE(sat) ประมาณ 0.2 V",
            ),
        )
    if vce < VCE_NEAR_SAT:
        return (
            "near-saturation",
            ("Near Saturation: VCE < 0.5 V — ผลอาจคลาดเคลื่อนจากแบบจำลอง",),
        )
    return ("active", ())


def calculate_dc_bias(inp: DcBiasInput) -> DcBiasResult:
    if inp.vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0")
    if inp.r1 <= 0 or inp.r2 <= 0 or inp.rc <= 0 or inp.re <= 0:
        raise ValidationError("R1, R2, RC, RE ต้องมากกว่า 0")
    if inp.beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")
    if not 0 < inp.vbe < inp.vcc:
        raise ValidationError("VBE ต้องมากกว่า 0 และน้อยกว่า VCC")

    vth = inp.vcc * inp.r2 / (inp.r1 + inp.r2)
    rth = inp.r1 * inp.r2 / (inp.r1 + inp.r2)
    ib = (vth - inp.vbe) / (rth + (inp.beta + 1.0) * inp.re)
    ic = inp.beta * ib
    ie = (inp.beta + 1.0) * ib
    ve = ie * inp.re
    vb = ve + inp.vbe
    vc = inp.vcc - ic * inp.rc
    vce = vc - ve

    region, warnings = classify_region(vth, inp.vbe, vce)
    if region == "cutoff":
        ib = ic = ie = 0.0
        ve = 0.0
        vb = vth
        vc = inp.vcc
        vce = inp.vcc

    return DcBiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def calculate_fixed_bias(inp: FixedBiasInput) -> BiasResult:
    if inp.vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0")
    if inp.rb <= 0:
        raise ValidationError("RB ต้องมากกว่า 0")
    if inp.rc <= 0:
        raise ValidationError("RC ต้องมากกว่า 0")
    if inp.beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")
    if not 0 < inp.vbe < inp.vcc:
        raise ValidationError("VBE ต้องมากกว่า 0 และน้อยกว่า VCC")

    ib = (inp.vcc - inp.vbe) / inp.rb
    ic = inp.beta * ib
    ie = (inp.beta + 1.0) * ib
    ve = 0.0
    vb = inp.vbe
    vc = inp.vcc - ic * inp.rc
    vce = vc

    region, warnings = classify_operating_point(ib, vce)
    return BiasResult(
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )
