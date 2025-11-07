"""Ingestão pública de dados solares para heliobiologia computacional.

O ``SolarAtlas`` encapsula chamadas a endpoints públicos (NOAA/NASA) e devolve
estruturas de dados padronizadas. Nenhuma coleta proprietária é utilizada – o
pipeline é totalmente reprodutível e baseado em APIs abertas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Iterable, List, Optional

import requests

from darwin_heliobiology.models.solar import IMFVector, SolarIndex, SolarObservation, SolarWindSample


DEFAULT_TIMEOUT = 10


@dataclass(slots=True)
class SolarAtlas:
    """Cliente para dados solares geomagnéticos públicos.

    Parameters
    ----------
    base_url: str
        Raiz dos serviços NOAA SWPC (default: ``https://services.swpc.noaa.gov``).
    session: Optional[requests.Session]
        Sessão HTTP reutilizável para permitir injeção/mocks em testes.
    timeout: int
        Tempo máximo de requisição em segundos.
    """

    base_url: str = "https://services.swpc.noaa.gov"
    session: Optional[requests.Session] = None
    timeout: int = DEFAULT_TIMEOUT

    # --------------------------- Helpers internos ---------------------------
    def _http(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _get_json(self, path: str) -> Iterable[dict]:
        url = f"{self.base_url}{path}"
        response = self._http().get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ------------------------------ KPI séries ------------------------------
    def fetch_kp_index(self, hours: int = 24) -> List[SolarIndex]:
        """Retorna série 1-min do índice planetário Kp (últimas ``hours``)."""

        raw = list(self._get_json("/json/planetary_k_index_1m.json"))
        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

        series: List[SolarIndex] = []
        for entry in raw:
            timestamp = datetime.fromisoformat(entry["time_tag"].replace("Z", "+00:00"))
            if timestamp < cutoff:
                continue
            kp_value = float(entry.get("kp", entry.get("kp_index", entry.get("estimated_kp", 0.0))))
            series.append(SolarIndex(timestamp=timestamp, value=kp_value, label="Kp"))

        return series

    def fetch_dst_index(self, hours: int = 24) -> List[SolarIndex]:
        """Retorna série horária do índice Dst (Kyoto)."""

        raw = list(self._get_json("/products/kyoto-dst.json"))
        data = raw[1:] if raw and isinstance(raw[0], list) else raw
        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

        series: List[SolarIndex] = []
        for entry in data:
            timestamp = datetime.fromisoformat(entry[0].replace("Z", "+00:00"))
            if timestamp < cutoff:
                continue
            dst_value = float(entry[1])
            series.append(SolarIndex(timestamp=timestamp, value=dst_value, label="Dst"))

        return series

    # ----------------------- Vento solar / IMF series -----------------------
    def fetch_solar_wind(self, hours: int = 24) -> List[SolarWindSample]:
        """Recupera dados do vento solar (ACE SWEPAM 1m)."""

        raw = list(self._get_json("/json/ace/swepam_1m.json"))
        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

        samples: List[SolarWindSample] = []
        for entry in raw:
            timestamp = datetime.fromisoformat(entry["time_tag"].replace("Z", "+00:00"))
            if timestamp < cutoff:
                continue
            samples.append(
                SolarWindSample(
                    timestamp=timestamp,
                    speed_kms=float(entry.get("speed", 0.0)),
                    density_pcm3=float(entry.get("density", 0.0)),
                    temperature_k=float(entry.get("temperature", 0.0)),
                )
            )

        return samples

    def fetch_imf(self, hours: int = 24) -> List[IMFVector]:
        """Recupera componentes do campo magnético interplanetário (ACE MAG 1m)."""

        raw = list(self._get_json("/json/ace/mag_1m.json"))
        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

        vectors: List[IMFVector] = []
        for entry in raw:
            timestamp = datetime.fromisoformat(entry["time_tag"].replace("Z", "+00:00"))
            if timestamp < cutoff:
                continue
            vectors.append(
                IMFVector(
                    timestamp=timestamp,
                    bx_nt=float(entry.get("bx_gsm", 0.0)),
                    by_nt=float(entry.get("by_gsm", 0.0)),
                    bz_nt=float(entry.get("bz_gsm", 0.0)),
                    bt_nt=float(entry.get("bt", 0.0)),
                )
            )

        return vectors

    # --------------------------- Agregação geral ----------------------------
    def snapshot(self, hours: int = 24) -> SolarObservation:
        """Gera observação consolidada das últimas ``hours`` horas."""

        kp = self.fetch_kp_index(hours=hours)
        dst = self.fetch_dst_index(hours=hours)
        wind = self.fetch_solar_wind(hours=hours)
        imf = self.fetch_imf(hours=hours)

        metadata = {
            "source": "NOAA SWPC",
            "retrieved_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "window_hours": hours,
        }

        return SolarObservation(kp_series=kp, dst_series=dst, solar_wind=wind, imf=imf, metadata=metadata)

