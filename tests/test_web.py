import unittest

from app import _diagram_labels, _status_note, _to_ohms, create_app
from dc_bias import DcBiasInput, calculate_dc_bias


class TestHomePage(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_home_returns_form(self):
        res = self.client.get("/")
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', body)
        self.assertIn('name="unit"', body)
        self.assertIn("Calculate DC Bias", body)


class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_valid_input_shows_computed_values(self):
        res = self.client.post("/calculate", data=self.valid)
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        for expected in ("1.942", "1.242", "9.294", "8.052", "1.230"):
            self.assertIn(expected, body)

    def test_zero_resistor_shows_validation_error(self):
        data = dict(self.valid, r1="0")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_input_shows_error(self):
        data = dict(self.valid, vcc="abc")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("เป็นตัวเลข", res.get_data(as_text=True))

    def test_result_changes_with_input(self):
        res = self.client.post("/calculate", data=dict(self.valid, vcc="24"))
        self.assertIn("3.778", res.get_data(as_text=True))

    def test_kohm_and_ohm_differ(self):
        kohm = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        ohm = self.client.post("/calculate", data=dict(self.valid, r1="100", unit="ohm")).get_data(as_text=True)
        self.assertIn("12.30", kohm)
        self.assertIn("12298.58", ohm)

    def test_empty_beta_shows_error(self):
        body = self.client.post("/calculate", data=dict(self.valid, beta="")).get_data(as_text=True)
        self.assertIn("เป็นตัวเลข", body)

    def test_nan_beta_is_rejected(self):
        body = self.client.post("/calculate", data=dict(self.valid, beta="nan")).get_data(as_text=True)
        self.assertIn("เป็นตัวเลข", body)
        self.assertNotIn("badge-active", body)

    def test_to_ohms_converts_kohm(self):
        self.assertEqual(_to_ohms("100", "kohm", "R1"), 100_000.0)

    def test_to_ohms_passes_ohm(self):
        self.assertEqual(_to_ohms("100", "ohm", "R1"), 100.0)


class TestResultsPresentation(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_shows_intermediate_values_in_details(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        for expected in ("วิธีคำนวณ", "VTH", "RTH", "2.164", "18.03", "12.30"):
            self.assertIn(expected, body)
        self.assertIn("<details", body)

    def test_shows_active_badge_and_units(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        self.assertIn("Active", body)
        for unit in ("V", "mA", "µA", "kΩ"):
            self.assertIn(unit, body)

    def test_cutoff_warning_is_visible(self):
        data = dict(self.valid, r2="1")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Cutoff", body)

    def test_stylesheet_linked(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("static/style.css", body)


class TestDiagramLabels(unittest.TestCase):
    def test_defaults_use_kohm_unit(self):
        labels = _diagram_labels({"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "kohm"})
        self.assertEqual(labels["vcc"], "12 V")
        self.assertEqual(labels["r1"], "100 kΩ")
        self.assertEqual(labels["beta"], "β = 100")

    def test_ohm_unit_changes_suffix(self):
        labels = _diagram_labels({"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "ohm"})
        self.assertEqual(labels["r1"], "100 Ω")

    def test_blank_field_becomes_dash(self):
        labels = _diagram_labels({"vcc": "12", "r1": "", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "kohm"})
        self.assertEqual(labels["r1"], "—")


class TestStatusNote(unittest.TestCase):
    def test_active_is_ok(self):
        note = _status_note(calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70)))
        self.assertEqual(note["tone"], "ok")
        self.assertIn("Active", note["text"])

    def test_cutoff_is_danger_not_ok(self):
        note = _status_note(calculate_dc_bias(DcBiasInput(12.0, 100e3, 1e3, 2.2e3, 1e3, 100.0, 0.70)))
        self.assertEqual(note["tone"], "danger")
        self.assertIn("Cutoff", note["text"])
        self.assertNotIn("Active", note["text"])
