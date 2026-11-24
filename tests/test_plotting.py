import unittest

from plotting import bode_svg, tran_svg
from spice_engine import AcPoint, TranPoint


class TestBodeSvg(unittest.TestCase):
    def setUp(self):
        self.points = tuple(
            AcPoint(frequency=f, gain_db=20.0 - abs(i - 10) * 0.5, phase_deg=-180.0)
            for i, f in enumerate((1, 10, 100, 1e3, 1e4, 1e5))
        )

    def test_draws_axes_labels_and_trace(self):
        svg = bode_svg(self.points)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("polyline", svg)
        self.assertIn("Frequency", svg)
        self.assertIn("Gain", svg)
        self.assertIn("Phase", svg)
        self.assertIn("kHz", svg)

    def test_empty_input_renders_message(self):
        self.assertIn("ไม่มีข้อมูล", bode_svg(()))

    def test_values_change_with_data(self):
        loud = tuple(
            AcPoint(frequency=p.frequency, gain_db=p.gain_db + 6, phase_deg=p.phase_deg)
            for p in self.points
        )
        self.assertNotEqual(bode_svg(self.points), bode_svg(loud))


class TestTranSvg(unittest.TestCase):
    def setUp(self):
        self.points = tuple(
            TranPoint(time=i * 1e-4, vin=0.01 * (1 if i % 2 else -1), vout=-0.017 * (1 if i % 2 else -1))
            for i in range(20)
        )

    def test_draws_two_traces_and_units(self):
        svg = tran_svg(self.points)
        self.assertEqual(svg.count("<polyline"), 2)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)
        self.assertIn("Time (ms)", svg)
        self.assertIn("mV", svg)

    def test_empty_input_renders_message(self):
        self.assertIn("ไม่มีข้อมูล", tran_svg(()))


if __name__ == "__main__":
    unittest.main()
