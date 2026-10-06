from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from darwin_heliobiology.metrics.helio_index import compute_helio_mind_index
from darwin_heliobiology.models.solar import (
    IMFVector,
    SolarIndex,
    SolarObservation,
    SolarWindSample,
)


def _make_observation(
    *,
    base: datetime,
    kp: list[float],
    dst: list[float],
    bz: list[float],
    speeds: list[float],
    densities: list[float],
) -> SolarObservation:
    kp_series = [
        SolarIndex(timestamp=base - timedelta(minutes=len(kp) - idx), value=value, label="Kp")
        for idx, value in enumerate(kp, start=1)
    ]
    dst_series = [
        SolarIndex(timestamp=base - timedelta(hours=len(dst) - idx), value=value, label="Dst")
        for idx, value in enumerate(dst, start=1)
    ]
    imf_series = [
        IMFVector(
            timestamp=base - timedelta(minutes=len(bz) - idx),
            bx_nt=0.0,
            by_nt=0.0,
            bz_nt=value,
            bt_nt=abs(value),
        )
        for idx, value in enumerate(bz, start=1)
    ]
    wind_series = [
        SolarWindSample(
            timestamp=base - timedelta(minutes=len(speeds) - idx),
            speed_kms=speed,
            density_pcm3=density,
            temperature_k=100000.0,
        )
        for idx, (speed, density) in enumerate(zip(speeds, densities, strict=False), start=1)
    ]

    metadata = {"window_hours": 24, "retrieved_at": base.isoformat()}

    return SolarObservation(
        kp_series=kp_series,
        dst_series=dst_series,
        solar_wind=wind_series,
        imf=imf_series,
        metadata=metadata,
    )


def test_compute_heliomind_index_returns_components_within_bounds() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    observation = _make_observation(
        base=base,
        kp=[2.0, 2.3, 2.7, 3.0],
        dst=[-12.0, -18.0, -20.0],
        bz=[3.0, -2.0, 1.0],
        speeds=[360.0, 380.0, 410.0],
        densities=[4.0, 5.0, 4.5],
    )

    result = compute_helio_mind_index(observation)

    assert 0.0 <= result.score <= 1.0
    assert result.classification in {"estavel", "vigilancia", "alerta"}
    assert result.components.kp_activity >= 0.0
    assert result.components.solar_wind_pressure >= 0.0
    assert result.metadata["window_hours"] == 12
    assert result.timestamp.tzinfo is not None


def test_compute_heliomind_index_flags_high_risk_alerts() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    observation = _make_observation(
        base=base,
        kp=[7.5, 8.0, 8.3, 8.5],
        dst=[-120.0, -160.0, -180.0],
        bz=[-18.0, -15.0, -12.0],
        speeds=[650.0, 700.0, 720.0],
        densities=[8.0, 9.0, 9.5],
    )

    result = compute_helio_mind_index(observation)

    assert result.score > 0.66
    assert result.classification == "alerta"
    assert any("Kp elevado" in alert for alert in result.alerts)
    assert any("Dst" in alert for alert in result.alerts)
    assert any("Bz" in alert for alert in result.alerts)


def test_compute_heliomind_index_handles_empty_series() -> None:
    observation = SolarObservation(kp_series=[], dst_series=[], solar_wind=[], imf=[], metadata={})

    result = compute_helio_mind_index(observation)

    # Sem dado, NADA é fabricado: score NaN e classe "indisponivel" (nunca 0.0 / "estavel").
    assert math.isnan(result.score)
    assert result.alerts == []
    assert result.classification == "indisponivel"
    assert math.isnan(result.components.kp_activity)


def _obs(base, *, kp_hours, dst=(-10.0,), bz=(1.0,), n=5.0, v=400.0):
    """Observação com Kp em horas-atrás dadas (por TEMPO) e demais séries pontuais."""
    kp_series = [
        SolarIndex(timestamp=base - timedelta(hours=h), value=val, label="Kp")
        for h, val in kp_hours
    ]
    return SolarObservation(
        kp_series=kp_series,
        dst_series=[SolarIndex(timestamp=base, value=d, label="Dst") for d in dst],
        solar_wind=[
            SolarWindSample(timestamp=base, speed_kms=v, density_pcm3=n, temperature_k=1e5)
        ],
        imf=[IMFVector(timestamp=base, bx_nt=0.0, by_nt=0.0, bz_nt=b, bt_nt=abs(b)) for b in bz],
        metadata={},
    )


def test_window_is_by_time_not_by_sample_count() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    # Kp=9 há 20 h (fora da janela de 12 h) e Kp=1 nas últimas horas: só as recentes contam.
    obs = _obs(base, kp_hours=[(20.0, 9.0), (3.0, 1.0), (2.0, 1.0), (0.0, 1.0)])
    result = compute_helio_mind_index(obs)
    assert abs(result.components.kp_activity - 1.0 / 9.0) < 1e-12
    assert result.components.variability == 0.0  # std de [1,1,1] = 0 (e há ≥ 2 amostras)


def test_variability_uses_sample_std_ddof1() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    obs = _obs(base, kp_hours=[(2.0, 2.0), (1.0, 4.0)])  # std ddof=1 = sqrt(2)
    result = compute_helio_mind_index(obs)
    assert abs(result.components.variability - math.sqrt(2.0) / 1.57) < 1e-12


def test_single_kp_sample_makes_variability_absent_not_zero() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    result = compute_helio_mind_index(_obs(base, kp_hours=[(0.0, 3.0)]))
    assert math.isnan(result.components.variability)
    assert math.isnan(result.score)
    assert result.classification == "indisponivel"


def test_nan_samples_are_dropped_not_zeroed() -> None:
    base = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)
    obs = _obs(
        base, kp_hours=[(2.0, 3.0), (1.0, float("nan")), (0.0, 5.0)], bz=(float("nan"), -4.0)
    )
    result = compute_helio_mind_index(obs)
    assert abs(result.components.kp_activity - 4.0 / 9.0) < 1e-12
    assert abs(result.components.bz_reconnection - 4.0 / 8.7) < 1e-12
