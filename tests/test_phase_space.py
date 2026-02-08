"""Testes iniciais para o phase space heliobiológico."""

from darwin_heliobiology.phase_space import SolarPsychodynamics


def test_phase_coordinates_returns_expected_tuple_length():
    estado = SolarPsychodynamics(6.5, -80, -12.0, 35.0, 0.2, 0.45, -2.5)

    coords = estado.phase_coordinates()

    assert len(coords) == 7
    assert coords[0] == 6.5
    assert coords[-1] == -2.5


def test_curvature_tensor_detects_entropy_and_discordance():
    estado = SolarPsychodynamics(7.0, -120, -15.0, 40.0, 0.3, 0.5, 3.0)

    tensor = estado.curvature_tensor()

    assert tensor["psycho_gravity"] > 0
    assert tensor["entropy"] > 0
    assert tensor["discordance"] >= 0


def test_epistemic_alerts_surface_clinical_warnings():
    estado = SolarPsychodynamics(7.2, -130, -20.0, 30.0, 0.2, 0.65, 2.5)

    alerts = estado.epistemic_alerts()

    assert any("CRITICAL" in alerta for alerta in alerts)
