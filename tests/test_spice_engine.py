import unittest
from unittest import mock

import spice_engine
from spice_engine import (
    CeParams,
    SpiceInputError,
    SpiceUnavailableError,
    build_netlist,
    find_ngspice,
    run_ac,
    run_op,
    run_tran,
    tran_window,
    validate,
)

REFERENCE = CeParams(
    vcc=12.0,
    r1=100e3,
    r2=22e3,
    rc=2.2e3,
    re=1e3,
    rl=10e3,
    cin=10e-6,
    cout=10e-6,
    beta=100.0,
    amplitude=10e-3,
    frequency=1e3,
)

NGSPICE = find_ngspice()
requires_ngspice = unittest.skipIf(NGSPICE is None, "ngspice not installed")


class TestNetlist(unittest.TestCase):
    def test_netlist_has_every_component_and_node(self):
        text = build_netlist(REFERENCE, "op")
        for token in ("R1 vcc base", "R2 base 0", "RC vcc coll", "RE emit 0",
                      "CIN in base", "COUT coll out", "RL out 0", "Q1 coll base emit"):
            self.assertIn(token, text)
        self.assertIn(".model QNPN NPN", text)

    def test_analysis_directive_matches_mode(self):
        self.assertIn("\nop\n", build_netlist(REFERENCE, "op"))
        self.assertIn("ac dec", build_netlist(REFERENCE, "ac"))
        self.assertIn("tran ", build_netlist(REFERENCE, "tran"))
        self.assertIn("wrdata ac.dat", build_netlist(REFERENCE, "ac"))
        self.assertIn("wrdata tran.dat", build_netlist(REFERENCE, "tran"))

    def test_values_are_written_in_si(self):
        text = build_netlist(REFERENCE, "op")
        self.assertIn("R1=100000", text)
        self.assertIn("CIN=1e-05", text)

    def test_unknown_analysis_is_rejected(self):
        with self.assertRaises(SpiceInputError):
            build_netlist(REFERENCE, "noise")

    def test_tran_window_covers_five_cycles(self):
        step, stop = tran_window(1000.0)
        self.assertAlmostEqual(stop, 5e-3, places=9)
        self.assertAlmostEqual(step, 5e-6, places=12)


class TestValidation(unittest.TestCase):
    def test_reference_passes(self):
        validate(REFERENCE)

    def test_zero_resistor_is_rejected(self):
        with self.assertRaises(SpiceInputError) as ctx:
            validate(CeParams(**{**REFERENCE.__dict__, "re": 0.0}))
        self.assertIn("RE", str(ctx.exception))

    def test_negative_frequency_is_rejected(self):
        with self.assertRaises(SpiceInputError) as ctx:
            validate(CeParams(**{**REFERENCE.__dict__, "frequency": -1.0}))
        self.assertIn("ความถี่", str(ctx.exception))

    def test_absurd_amplitude_is_rejected(self):
        with self.assertRaises(SpiceInputError):
            validate(CeParams(**{**REFERENCE.__dict__, "amplitude": 50.0}))


class TestEngineDiscovery(unittest.TestCase):
    def test_missing_binary_raises_clear_error(self):
        with mock.patch.object(spice_engine, "find_ngspice", return_value=None):
            with self.assertRaises(SpiceUnavailableError) as ctx:
                run_op(REFERENCE)
        self.assertIn("ngspice", str(ctx.exception))

    @requires_ngspice
    def test_version_looks_like_ngspice(self):
        self.assertTrue(spice_engine.engine_version(NGSPICE).startswith("ngspice"))


@requires_ngspice
class TestRealRuns(unittest.TestCase):
    """These assertions come from physics, not from copied output."""

    def test_op_is_forward_active_and_near_analytical(self):
        op, run = run_op(REFERENCE)
        self.assertGreater(op.vce, 1.0)
        self.assertLess(op.vce, 12.0)
        self.assertAlmostEqual(op.ie, op.ic + op.ib, places=9)
        self.assertAlmostEqual(op.vce, op.vc - op.ve, places=9)
        # analytical reference: VB 1.942 V, VE 1.242 V, IC 1.230 mA
        self.assertLess(abs(op.vb - 1.942), 0.15)
        self.assertLess(abs(op.ve - 1.242), 0.15)
        self.assertLess(abs(op.ic - 1.230e-3), 0.15e-3)
        self.assertEqual(run.analysis, "op")
        self.assertIn("ngspice", run.version)

    def test_op_changes_when_re_changes(self):
        before, _ = run_op(REFERENCE)
        after, _ = run_op(CeParams(**{**REFERENCE.__dict__, "re": 470.0}))
        self.assertNotAlmostEqual(before.ve, after.ve, places=3)
        self.assertLess(after.ve, before.ve)

    def test_ac_has_gain_and_phase_for_every_point(self):
        ac, run = run_ac(REFERENCE)
        self.assertGreater(len(ac.points), 100)
        self.assertTrue(all(p.frequency > 0 for p in ac.points))
        # unbypassed RE gives a low, inverting midband gain
        self.assertGreater(ac.midband_gain, 1.0)
        self.assertLess(ac.midband_gain, 4.0)
        self.assertLess(abs(abs(ac.phase_deg) - 180.0), 10.0)
        self.assertEqual(run.analysis, "ac")

    def test_ac_gain_falls_when_re_grows(self):
        base, _ = run_ac(REFERENCE)
        heavier, _ = run_ac(CeParams(**{**REFERENCE.__dict__, "re": 2.2e3}))
        self.assertLess(heavier.midband_gain, base.midband_gain)

    def test_transient_inverts_and_follows_the_source(self):
        tran, run = run_tran(REFERENCE)
        self.assertTrue(tran.inverted)
        self.assertGreater(tran.vin_peak, 0.009)
        self.assertLess(tran.vin_peak, 0.011)
        self.assertAlmostEqual(tran.gain, tran.vout_peak / tran.vin_peak, places=9)
        self.assertEqual(run.analysis, "tran")

    def test_transient_amplitude_tracks_input(self):
        small, _ = run_tran(REFERENCE)
        loud, _ = run_tran(CeParams(**{**REFERENCE.__dict__, "amplitude": 20e-3}))
        ratio = loud.vout_peak / small.vout_peak
        self.assertAlmostEqual(ratio, 2.0, delta=0.25)


if __name__ == "__main__":
    unittest.main()
