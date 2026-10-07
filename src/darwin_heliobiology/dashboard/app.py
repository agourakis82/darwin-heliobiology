"""Aplicação Streamlit principal para o HelioMind Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from darwin_heliobiology.dashboard.components import (
    build_forecast_comparison,
    build_helio_mind_timeseries,
    build_kp_timeseries,
    build_meta_forest_plot,
)

# Configuração da página
st.set_page_config(page_title="HelioMind Dashboard", page_icon="☀️", layout="wide")


@st.cache_data
def load_omni_data(path: str | Path) -> pd.DataFrame:
    """Carrega dados OMNI2 de um arquivo parquet.

    Parameters
    ----------
    path:
        Caminho para o arquivo parquet com dados OMNI2.

    Returns
    -------
    pd.DataFrame
        DataFrame com dados carregados.
    """
    path = Path(path)
    if not path.exists():
        st.error(f"Arquivo não encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    return df


@st.cache_data
def compute_helio_mind(df: pd.DataFrame) -> pd.DataFrame:
    """Computa o HelioMind Index para cada linha do DataFrame.

    Parameters
    ----------
    df:
        DataFrame OMNI2 com colunas necessárias.

    Returns
    -------
    pd.DataFrame
        DataFrame com coluna 'helio_mind_score' adicionada.
    """
    # Filtrar colunas necessárias
    required_cols = ["kp_index", "dst_nt", "bz_gsm_nt", "speed_kms", "proton_density_pcm3"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Colunas necessárias ausentes: {set(required_cols) - set(df.columns)}")
        return pd.DataFrame()

    # Para demonstração, calcula um índice simplificado
    # Em produção, usar compute_helio_mind_index com estruturas apropriadas

    # Kp normalizado (0-9 escala)
    kp_norm = df["kp_index"].clip(0, 9) / 9.0

    # Dst normalizado (storm intensity)
    dst_norm = (-df["dst_nt"].clip(upper=0)) / 78.0  # p99 calibrado

    # Bz sul normalizado
    bz_norm = (-df["bz_gsm_nt"].clip(upper=0)) / 8.7  # p99 calibrado

    # Pressão vento solar normalizada
    pressure = df["proton_density_pcm3"] * df["speed_kms"] ** 2
    pressure_norm = pressure / 4_364_643.0  # p99 calibrado

    # HelioMind Score (pesos default do helio_index.py)
    helio_score = (
        0.35 * kp_norm.fillna(0)
        + 0.25 * dst_norm.fillna(0)
        + 0.20 * bz_norm.fillna(0)
        + 0.15 * pressure_norm.fillna(0)
    ).clip(0, 1)

    result = df.copy()
    result["helio_mind_score"] = helio_score.values

    return result


def main() -> None:
    """Função principal da aplicação Streamlit."""
    st.title("☀️ HelioMind Dashboard")
    st.markdown(
        "Monitoramento em tempo real de atividade solar e seus impactos em "
        "parâmetros neurofisiológicos."
    )

    # Sidebar com configurações
    with st.sidebar:
        st.header("Configurações")

        omni_path = st.text_input(
            "Caminho OMNI2",
            value="data/raw/nasa_omni/omni2_hourly.parquet",
            help="Caminho para o arquivo parquet com dados OMNI2 horários.",
        )

        st.markdown("---")
        st.markdown("### Sobre")
        st.markdown("""
            Este dashboard utiliza dados públicos da NASA/NASA OMNIWeb para
            monitorar a atividade solar e computar o HelioMind Index.

            Fontes:
            - [NASA OMNIWeb](https://omniweb.gsfc.nasa.gov/)
            - [NOAA SWPC](https://www.swpc.noaa.gov/)
            """)

    # Carregar dados
    if not omni_path:
        st.warning("Por favor, forneça o caminho para os dados OMNI2.")
        return

    df = load_omni_data(omni_path)

    if df.empty:
        st.warning("Nenhum dado carregado. Verifique o caminho do arquivo.")
        return

    st.success(
        f"Carregados {len(df):,} registros de {df['timestamp'].min()} até {df['timestamp'].max()}"
    )

    # Computar HelioMind
    df_with_helio = compute_helio_mind(df)

    # Tabs para diferentes visualizações
    tab_solar, tab_heliomind, tab_meta = st.tabs(["Solar", "HelioMind", "Meta-Análise"])

    # Tab Solar
    with tab_solar:
        st.subheader("Índice Kp - Atividade Geomagnética")

        # Filtro de período
        if "timestamp" in df.columns:
            min_date = df["timestamp"].min().date()
            max_date = df["timestamp"].max().date()

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Data inicial",
                    min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="solar_start",
                )
            with col2:
                end_date = st.date_input(
                    "Data final", max_date, min_value=min_date, max_value=max_date, key="solar_end"
                )

            mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
            df_filtered = df[mask].copy()
        else:
            df_filtered = df.copy()

        if not df_filtered.empty:
            fig_kp = build_kp_timeseries(df_filtered)
            st.plotly_chart(fig_kp, use_container_width=True)

            # Estatísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Kp Médio", f"{df_filtered['kp_index'].mean():.2f}")
            with col2:
                st.metric("Kp Máximo", f"{df_filtered['kp_index'].max():.2f}")
            with col3:
                storm_hours = (df_filtered["kp_index"] >= 5).sum()
                st.metric("Horas de Tempestade (Kp≥5)", f"{storm_hours:,}")

    # Tab HelioMind
    with tab_heliomind:
        st.subheader("HelioMind Index - Acoplamento Sol ↔ Neurofisiologia")

        if "timestamp" in df_with_helio.columns:
            min_date = df_with_helio["timestamp"].min().date()
            max_date = df_with_helio["timestamp"].max().date()

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Data inicial", min_date, min_value=min_date, max_value=max_date, key="hm_start"
                )
            with col2:
                end_date = st.date_input(
                    "Data final", max_date, min_value=min_date, max_value=max_date, key="hm_end"
                )

            mask = (df_with_helio["timestamp"].dt.date >= start_date) & (
                df_with_helio["timestamp"].dt.date <= end_date
            )
            df_filtered = df_with_helio[mask].copy()
        else:
            df_filtered = df_with_helio.copy()

        if not df_filtered.empty:
            fig_hm = build_helio_mind_timeseries(df_filtered)
            st.plotly_chart(fig_hm, use_container_width=True)

            # Classificação
            current_score = df_filtered["helio_mind_score"].iloc[-1]
            if current_score < 0.33:
                classification = "🟢 Estável"
            elif current_score < 0.66:
                classification = "🟡 Vigilância"
            else:
                classification = "🔴 Alerta"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score Atual", f"{current_score:.3f}")
            with col2:
                st.metric("Classificação", classification)
            with col3:
                alert_hours = (df_filtered["helio_mind_score"] >= 0.66).sum()
                st.metric("Horas em Alerta", f"{alert_hours:,}")

    # Tab Meta-Análise
    with tab_meta:
        st.subheader("Meta-Análise de Efeitos Heliobiológicos")

        st.markdown("""
            Esta aba demonstra a visualização de forest plots para meta-análise de
            efeitos solares em diversos desfechos de saúde.

            Dados de exemplo (risco relativo de eventos cardiovasculares durante tempestades geomagnéticas).
            """)

        # Dados de exemplo
        example_labels = [
            "Cardíaco (Wang 2023)",
            "AVC (Stoupel 2022)",
            "Pressão Arterial (Vencato 2021)",
            "Depressão (Kay 2024)",
            "Mortalidade (Dimitrova 2020)",
        ]
        example_effects = [1.15, 1.08, 1.22, 1.05, 1.12]
        example_cis = [(1.05, 1.26), (0.98, 1.19), (1.10, 1.35), (0.97, 1.14), (1.02, 1.23)]

        fig_forest = build_meta_forest_plot(example_effects, example_cis, example_labels)
        st.plotly_chart(fig_forest, use_container_width=True)

        st.markdown("---")
        st.subheader("Comparação de Previsões (Demo)")

        # Gerar dados de exemplo para comparação de previsões
        if "kp_index" in df.columns:
            df_sample = df.tail(168).copy()  # Última semana
            df_sample = df_sample.reset_index(drop=True)

            actual = df_sample["kp_index"]
            kairos_pred = actual * 0.95 + 0.2  # Simula previsão Kairos
            neural_pred = actual * 0.98 + 0.1  # Simula previsão Neural

            fig_comp = build_forecast_comparison(actual, kairos_pred, neural_pred)
            st.plotly_chart(fig_comp, use_container_width=True)


if __name__ == "__main__":
    main()
