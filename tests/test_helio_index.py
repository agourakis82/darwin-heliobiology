from __future__ import annotations

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
    assert result.metadata["window_hours"] == 24
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

    assert result.score == 0.0
    assert result.alerts == []
    assert result.classification == "estavel"
