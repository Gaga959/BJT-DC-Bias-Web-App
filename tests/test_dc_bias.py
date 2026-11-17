import unittest
from dataclasses import replace

from dc_bias import (
    DcBiasInput,
    EmitterBiasInput,
    FixedBiasInput,
    ValidationError,
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
    classify_operating_point,
    classify_region,
)


class TestReferenceCase(unittest.TestCase):
    def test_voltage_divider_reference_case(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70))
        self.assertAlmostEqual(res.vth, 2.163934, places=6)
        self.assertAlmostEqual(res.rth, 18032.786885, places=3)
        self.assertAlmostEqual(res.ib, 12.298581e-6, places=10)
        self.assertAlmostEqual(res.ic, 1.229858e-3, places=8)
        self.assertAlmostEqual(res.ie, 1.242157e-3, places=8)
        self.assertAlmostEqual(res.vb, 1.942157, places=6)
        self.assertAlmostEqual(res.ve, 1.242157, places=6)
        self.assertAlmostEqual(res.vc, 9.294312, places=6)
        self.assertAlmostEqual(res.vce, 8.052155, places=6)
        self.assertEqual(res.region, "active")
        self.assertEqual(res.warnings, ())


BASE = DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70)


class TestValidation(unittest.TestCase):
    def assert_rejects(self, field, value, message):
        with self.assertRaises(ValidationError) as ctx:
            calculate_dc_bias(replace(BASE, **{field: value}))
        self.assertIn(message, str(ctx.exception))

    def test_zero_vcc(self):
        self.assert_rejects("vcc", 0.0, "VCC ต้องมากกว่า 0")

    def test_zero_r1(self):
        self.assert_rejects("r1", 0.0, "R1, R2, RC, RE ต้องมากกว่า 0")

    def test_negative_r2(self):
        self.assert_rejects("r2", -1.0, "R1, R2, RC, RE ต้องมากกว่า 0")

    def test_zero_beta(self):
        self.assert_rejects("beta", 0.0, "β ต้องมากกว่า 0")

    def test_vbe_not_below_vcc(self):
        self.assert_rejects("vbe", 12.0, "VBE ต้องมากกว่า 0 และน้อยกว่า VCC")


class TestRegion(unittest.TestCase):
    def test_cutoff_clamps_currents(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 1e3, 2.2e3, 1e3, 100.0, 0.70))
        self.assertEqual(res.region, "cutoff")
        self.assertEqual((res.ib, res.ic, res.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(res.vce, 12.0, places=9)
        self.assertTrue(any("Cutoff" in w for w in res.warnings))

    def test_saturation_warns(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 10e3, 10e3, 10e3, 100.0, 100.0, 0.70))
        self.assertLess(res.vce, 0.2)
        self.assertEqual(res.region, "saturation")
        self.assertTrue(any("Saturation" in w for w in res.warnings))

    def test_near_saturation_warns(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 1500.0, 10.0, 100.0, 0.70))
        self.assertGreaterEqual(res.vce, 0.2)
        self.assertLess(res.vce, 0.5)
        self.assertEqual(res.region, "near-saturation")
        self.assertTrue(any("Saturation" in w for w in res.warnings))

    def test_vce_boundary_at_02_is_near_saturation(self):
        self.assertEqual(classify_region(2.0, 0.7, 0.199)[0], "saturation")
        self.assertEqual(classify_region(2.0, 0.7, 0.2)[0], "near-saturation")
        self.assertEqual(classify_region(2.0, 0.7, 0.5)[0], "active")

    def test_cutoff_checked_before_saturation(self):
        self.assertEqual(classify_region(0.5, 0.7, 0.1)[0], "cutoff")


class TestFixedBias(unittest.TestCase):
    def test_reference_case(self):
        res = calculate_fixed_bias(FixedBiasInput(12.0, 1e6, 2.2e3, 100.0, 0.70))
        self.assertAlmostEqual(res.ib, 11.3e-6, places=12)
        self.assertAlmostEqual(res.ic, 1.13e-3, places=12)
        self.assertAlmostEqual(res.ie, 1.1413e-3, places=12)
        self.assertAlmostEqual(res.vb, 0.70, places=9)
        self.assertEqual(res.ve, 0.0)
        self.assertAlmostEqual(res.vc, 9.514, places=9)
        self.assertAlmostEqual(res.vce, 9.514, places=9)
        self.assertEqual(res.region, "active")
        self.assertEqual(res.warnings, ())

    def test_zero_rb_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed_bias(FixedBiasInput(12.0, 0.0, 2.2e3, 100.0, 0.70))
        self.assertIn("RB ต้องมากกว่า 0", str(ctx.exception))

    def test_zero_rc_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed_bias(FixedBiasInput(12.0, 1e6, 0.0, 100.0, 0.70))
        self.assertIn("RC ต้องมากกว่า 0", str(ctx.exception))


class TestClassifyOperatingPoint(unittest.TestCase):
    def test_cutoff_when_ib_not_positive(self):
        self.assertEqual(classify_operating_point(0.0, 9.0)[0], "cutoff")

    def test_saturation_boundaries(self):
        self.assertEqual(classify_operating_point(1e-5, 0.199)[0], "saturation")
        self.assertEqual(classify_operating_point(1e-5, 0.2)[0], "near-saturation")
        self.assertEqual(classify_operating_point(1e-5, 0.5)[0], "active")


class TestEmitterBias(unittest.TestCase):
    def test_reference_case(self):
        res = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 1e3, 100.0, 0.70))
        self.assertAlmostEqual(res.ib, 1.026339691e-5, places=12)
        self.assertAlmostEqual(res.ic, 1.026339691e-3, places=12)
        self.assertAlmostEqual(res.ie, 1.036603088e-3, places=12)
        self.assertAlmostEqual(res.ve, 1.036603088, places=8)
        self.assertAlmostEqual(res.vb, 1.736603088, places=8)
        self.assertAlmostEqual(res.vc, 9.742052679, places=8)
        self.assertAlmostEqual(res.vce, 8.705449591, places=8)
        self.assertEqual(res.region, "active")

    def test_larger_re_lowers_ic(self):
        one_k = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 1e3, 100.0, 0.70))
        two_k = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 2e3, 100.0, 0.70))
        self.assertLess(two_k.ic, one_k.ic)
        self.assertAlmostEqual(two_k.ic, 0.9400998336e-3, places=12)
        self.assertAlmostEqual(two_k.vce, 8.032778702, places=8)

    def test_zero_re_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 0.0, 100.0, 0.70))
        self.assertIn("RE ต้องมากกว่า 0", str(ctx.exception))
