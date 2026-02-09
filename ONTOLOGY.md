# ONTOLOGY — DARWIN HELIOBIOLOGY

## Entidades
- **SolarState**: vetor {Kp, Dst, Bz, solar_flux, CME_probability}.
- **PsychometricTrajectory**: séries temporais de PHQ-9, MADRS, PANSS, escalas de suicidality.
- **AutonomicRhythm**: métricas HRV, actigrafia, cortisol salivar.
- **CircadianFlux**: deslocamento de cronotipo, amplitude de melatonina.
- **RiskManifold**: embedding generativo para probabilidade de descompensação (0..1).
- **Hypothesis**: proposição falsificável que relaciona SolarState ↔ estados neuropsíquicos.

## Relações
- `SolarState --perturba--> AutonomicRhythm`
- `AutonomicRhythm --modula--> PsychometricTrajectory`
- `CircadianFlux --desloca--> PsychometricTrajectory`
- `Hypothesis --projeta--> RiskManifold`
- `RiskManifold --alerta--> ClinicalAction`
- `KairosForecaster --antecipar--> RiskManifold`
- `AletheiaValidator --corrobora--> Hypothesis`

## Geometria
- Phase space Ψ = (SolarState, AutonomicRhythm, PsychometricTrajectory, CircadianFlux, RiskManifold).
- Curvatura calculada via divergência entre sinais autonômicos e auto-relato.
- Singularidades = eventos extremos (Kp ≥ 7, Dst ≤ -100).
  - **Nota de evidência**: Kp ≥ 7 = G3 (NOAA, grau A); Dst ≤ -100 = tempestade intensa (grau A).
  - O limiar de suicidality ≥ 0.6 foi **removido** desta definição por falta de fundamento
    empírico — não existe estudo demonstrando threshold específico de risco suicida vinculado a
    atividade geomagnética. Ver `docs/SCIENTIFIC_FOUNDATIONS.md` §3.

## Invariantes
- Risco projetado deve respeitar monotonicidade: ↑ perturbação solar ⇒ não diminuir risco sem evidência.
- HRV e circadian shift possuem limites fisiológicos documentados.
- Predições precisam anexar intervalo de confiança, origem de dados (`@epistemically_logged`) e parâmetros (`smoothing_factor`, baseline).

## Instrumentação
- Exportar métricas para Prometheus (`psycho_gravity`, `entropy`, `discordance`).
- Grafana: heatmap SolarState × PsychometricTrajectory.
- Memória epistemológica: cada run registra hipótese, literatura associada, revisão posterior.
- Pipelines de ingestão baseados em `SolarAtlas` (NOAA/NASA) e normalização `psychophysiology` para HRV/mood públicos.

