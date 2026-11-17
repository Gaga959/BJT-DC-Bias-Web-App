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
        self.valid = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
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
        self.valid = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
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


class TestSingleScreenLayout(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_get_renders_three_panels_and_svg(self):
        body = self.client.get("/").get_data(as_text=True)
        for cls in ("panel-input", "panel-circuit", "panel-results"):
            self.assertIn(cls, body)
        self.assertIn("<svg", body)
        self.assertIn("schematic", body)

    def test_get_shows_default_labels_in_circuit(self):
        body = self.client.get("/").get_data(as_text=True)
        for text in ("12 V", "100 kΩ", "22 kΩ", "2.2 kΩ", "1 kΩ", "β = 100"):
            self.assertIn(text, body)

    def test_post_updates_circuit_labels(self):
        body = self.client.post("/calculate", data=dict(self.valid, r1="47")).get_data(as_text=True)
        self.assertIn("47 kΩ", body)
        self.assertNotIn("100 kΩ", body)

    def test_ohm_mode_updates_circuit_labels(self):
        body = self.client.post("/calculate", data=dict(self.valid, unit="ohm")).get_data(as_text=True)
        self.assertIn("100 Ω", body)
        self.assertNotIn("100 kΩ", body)

    def test_blank_field_renders_dash_not_none(self):
        body = self.client.post("/calculate", data=dict(self.valid, r2="")).get_data(as_text=True)
        self.assertIn("—", body)
        self.assertNotIn(">None<", body)

    def test_get_has_no_answer_numbers(self):
        body = self.client.get("/").get_data(as_text=True)
        for leak in ("1.942", "8.052", "9.294"):
            self.assertNotIn(leak, body)

    def test_get_shows_idle_status_and_dashes(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("status-idle", body)
        self.assertIn("—", body)

    def test_post_shows_active_status(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        self.assertIn("status-ok", body)
        self.assertIn("Active", body)

    def test_cutoff_shows_danger_status(self):
        body = self.client.post("/calculate", data=dict(self.valid, r2="1")).get_data(as_text=True)
        self.assertIn("status-danger", body)

    def test_schematic_uses_zigzag_resistors(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertGreaterEqual(body.count("res-zigzag"), 4)

    def test_schematic_wraps_transistor_in_circle(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("q1-circle", body)


class TestModeSelection(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.divider = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22",
                        "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}
        self.fixed = {"mode": "fixed", "vcc": "12", "rb": "1000",
                      "rc": "2.2", "beta": "100", "vbe": "0.70", "unit": "kohm"}
        self.emitter = dict(self.fixed, mode="emitter", re="1")

    def test_tabs_link_each_mode(self):
        body = self.client.get("/").get_data(as_text=True)
        for mode in ("divider", "fixed", "emitter"):
            self.assertIn(f'href="/?mode={mode}"', body)

    def test_fixed_form_hides_divider_fields(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        for hidden in ('name="r1"', 'name="r2"', 'name="re"'):
            self.assertNotIn(hidden, body)

    def test_emitter_form_shows_rb_and_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        for field in ('name="rb"', 'name="rc"', 'name="re"'):
            self.assertIn(field, body)
        self.assertNotIn('name="r1"', body)

    def test_fixed_result_has_mode_badge(self):
        body = self.client.post("/calculate", data=self.fixed).get_data(as_text=True)
        self.assertIn('class="mode-badge"', body)
        self.assertIn("Fixed Bias", body)
        self.assertIn("1.130", body)
        self.assertIn("9.514", body)

    def test_emitter_result_values(self):
        body = self.client.post("/calculate", data=self.emitter).get_data(as_text=True)
        self.assertIn("1.026", body)
        self.assertIn("8.705", body)

    def test_unknown_mode_is_rejected(self):
        body = self.client.post("/calculate", data=dict(self.divider, mode="inverter")).get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertIn("status-idle", body)

    def test_missing_mode_is_rejected(self):
        data = {k: v for k, v in self.divider.items() if k != "mode"}
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)

    def test_fixed_zero_rb_names_rb_and_shows_no_numbers(self):
        body = self.client.post("/calculate", data=dict(self.fixed, rb="0")).get_data(as_text=True)
        self.assertIn("RB ต้องมากกว่า 0", body)
        self.assertIn("Fixed Bias", body)
        self.assertNotIn("1.130", body)
        self.assertNotIn("9.514", body)

    def test_wrong_mode_payload_asks_for_rb(self):
        data = {k: v for k, v in self.divider.items() if k != "r1"}
        data["mode"] = "fixed"
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("กรุณากรอก RB เป็นตัวเลข", body)

    def test_divider_values_stay_identical(self):
        body = self.client.post("/calculate", data=self.divider).get_data(as_text=True)
        self.assertIn("1.230", body)
        self.assertIn("8.052", body)
