"""Formalização do phase space heliobiológico.

Cada instância de :class:`SolarPsychodynamics` captura o estado geomagnético e
biomarcadores psíquicos sincronizados, devolvendo coordenadas explícitas dentro do
manifold Ψ = (atividade solar, estado neurofisiológico, risco psicodinâmico).

O módulo segue os princípios de Fenomenologia Codificada do manifesto:
- funções como proposições
- estética como compressão epistemológica
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(slots=True)
class SolarPsychodynamics:
    """Representa o estado acoplado Sol-mente em um timestamp.

    Parameters
    ----------
    kp_index:
        Intensidade geomagnética (Kp) em tempo quase real.
    dst_index:
        Indicador de tempestade (Dst, nT). Valores negativos indicam distúrbios.
    bz_gsm:
        Componente sul-norte do campo magnético interplanetário (nT).
    heart_rate_variability:
        Variância da HRV (ms²) agregada de wearables (indicador autonômico).
    mood_score:
        Escore subjetivo/emocional (ex.: PHQ-9 normalizado para 0..1).
    suicidality_index:
        Probabilidade inferida de ideação/ação (0..1) proveniente de avaliações clínicas.
    circadian_shift:
        Deslocamento médio do relógio circadiano (horas), deduzido de actigrafia.
    """

    kp_index: float
    dst_index: float
    bz_gsm: float
    heart_rate_variability: float
    mood_score: float
    suicidality_index: float
    circadian_shift: float

    def phase_coordinates(self) -> Tuple[float, float, float, float, float, float, float]:
        """Geodésica no manifold Ψ.

        Retorna as coordenadas que alimentam modelos downstream – mantendo
        transparência ontológica para futuros agentes.
        """

        return (
            self.kp_index,
            self.dst_index,
            self.bz_gsm,
            self.heart_rate_variability,
            self.mood_score,
            self.suicidality_index,
            self.circadian_shift,
        )

    def curvature_tensor(self) -> Dict[str, float]:
        """Mapeia curvaturas epistemológicas do estado atual.

        - ``psycho_gravity`` monitora a força de acoplamento solar-mental.
        - ``entropy`` mede dispersão nas métricas clínicas/solares.
        - ``discordance`` quantifica divergência entre sinais autonômicos e humor auto-relatado.
        """

        psycho_gravity = abs(self.bz_gsm) * max(self.suicidality_index, 0.01)
        entropy = max(self.kp_index * 0.1, 0.01) + max(1 - self.heart_rate_variability / 1000, 0)
        discordance = abs(self.mood_score - (1 - self.heart_rate_variability / 1000))

        return {
            "psycho_gravity": round(psycho_gravity, 3),
            "entropy": round(entropy, 3),
            "discordance": round(discordance, 3),
        }

    def epistemic_alerts(self) -> List[str]:
        """Gera alertas interpretáveis com foco em saúde mental."""

        alerts: List[str] = []

        if self.kp_index >= 6 and self.suicidality_index >= 0.4:
            alerts.append(
                "CRITICAL: tempestade geomagnética coincidindo com risco suicida elevado."
            )

        if self.dst_index <= -50 and self.heart_rate_variability < 50:
            alerts.append("ALTA TENSÃO AUTONÔMICA: Dst tempestuoso + HRV deprimida.")

        if abs(self.circadian_shift) >= 2 and self.mood_score <= 0.3:
            alerts.append(
                "DISRUPÇÃO CIRCADIANA: desalinhamento >2h associado a humor severamente negativo."
            )

        if not alerts:
            alerts.append("Neutral: estado dentro de faixa homeostática.")

        return alerts
