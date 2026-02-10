"""Componentes de visualização para o dashboard Streamlit."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def build_kp_timeseries(
    df: pd.DataFrame,
    *,
    title: str = "Índice Kp (Planetary K-index)",
    height: int = 400,
) -> go.Figure:
    """Constrói gráfico de linha temporal para o índice Kp.

    Parameters
    ----------
    df:
        DataFrame com colunas 'timestamp' e 'kp_index'.
    title:
        Título do gráfico.
    height:
        Altura do gráfico em pixels.

    Returns
    -------
    go.Figure
        Objeto de figura Plotly pronto para exibição.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["kp_index"],
            mode="lines",
            name="Kp",
            line=dict(color="#FF6B6B", width=2),
        )
    )

    # Linhas de referência para classificação de tempestades geomagnéticas
    fig.add_hline(
        y=5.0,
        line_dash="dash",
        line_color="orange",
        annotation_text="G1 (Menor)",
        annotation_position="right",
    )
    fig.add_hline(
        y=7.0,
        line_dash="dash",
        line_color="red",
        annotation_text="G3 (Forte)",
        annotation_position="right",
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis_title="Tempo",
        yaxis_title="Índice Kp",
        height=height,
        template="plotly_white",
        hovermode="x unified",
    )

    return fig


def build_helio_mind_timeseries(
    df: pd.DataFrame,
    *,
    title: str = "HelioMind Index",
    height: int = 400,
) -> go.Figure:
    """Constrói gráfico temporal para o HelioMind Index com linhas de alerta.

    Parameters
    ----------
    df:
        DataFrame com colunas 'timestamp' e 'helio_mind_score'.
    title:
        Título do gráfico.
    height:
        Altura do gráfico em pixels.

    Returns
    -------
    go.Figure
        Objeto de figura Plotly pronto para exibição.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["helio_mind_score"],
            mode="lines",
            name="HelioMind Score",
            line=dict(color="#4ECDC4", width=2),
            fill="tozeroy",
            fillcolor="rgba(78, 205, 196, 0.2)",
        )
    )

    # Linhas de alerta baseadas na classificação
    fig.add_hline(
        y=0.33,
        line_dash="dot",
        line_color="green",
        annotation_text="Estável",
        annotation_position="right",
    )
    fig.add_hline(
        y=0.66,
        line_dash="dot",
        line_color="orange",
        annotation_text="Vigilância",
        annotation_position="right",
    )

    # Região de alerta
    fig.add_hrect(
        y0=0.66,
        y1=1.0,
        fillcolor="rgba(255, 0, 0, 0.1)",
        layer="below",
        line_width=0,
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis_title="Tempo",
        yaxis_title="HelioMind Score (0-1)",
        yaxis=dict(range=[0, 1]),
        height=height,
        template="plotly_white",
        hovermode="x unified",
    )

    return fig


def build_forecast_comparison(
    actual: pd.Series,
    kairos_pred: pd.Series,
    neural_pred: pd.Series,
    *,
    title: str = "Comparação de Previsões",
    height: int = 400,
) -> go.Figure:
    """Compara valores observados com previsões de diferentes modelos.

    Parameters
    ----------
    actual:
        Série pandas com valores observados.
    kairos_pred:
        Série pandas com previsões do modelo Kairos.
    neural_pred:
        Série pandas com previsões do modelo NeuralForecast.
    title:
        Título do gráfico.
    height:
        Altura do gráfico em pixels.

    Returns
    -------
    go.Figure
        Objeto de figura Plotly pronto para exibição.
    """
    fig = go.Figure()

    # Valores observados
    fig.add_trace(
        go.Scatter(
            x=actual.index,
            y=actual.values,
            mode="lines",
            name="Observado",
            line=dict(color="#333333", width=2),
        )
    )

    # Previsão Kairos
    fig.add_trace(
        go.Scatter(
            x=kairos_pred.index,
            y=kairos_pred.values,
            mode="lines",
            name="Previsão Kairos",
            line=dict(color="#FF6B6B", width=2, dash="dash"),
        )
    )

    # Previsão NeuralForecast
    fig.add_trace(
        go.Scatter(
            x=neural_pred.index,
            y=neural_pred.values,
            mode="lines",
            name="Previsão Neural",
            line=dict(color="#4ECDC4", width=2, dash="dot"),
        )
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis_title="Tempo",
        yaxis_title="Valor",
        height=height,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return fig


def build_meta_forest_plot(
    effect_sizes: list[float],
    cis: list[tuple[float, float]],
    labels: list[str],
    *,
    title: str = "Forest Plot - Meta-Análise",
    height: int = 400,
) -> go.Figure:
    """Constrói forest plot para meta-análise de efeitos.

    Parameters
    ----------
    effect_sizes:
        Lista de tamanhos de efeito (ex: odds ratio, risco relativo).
    cis:
        Lista de tuplas (lower, upper) para intervalos de confiança.
    labels:
        Lista de rótulos para cada estudo.
    title:
        Título do gráfico.
    height:
        Altura do gráfico em pixels.

    Returns
    -------
    go.Figure
        Objeto de figura Plotly pronto para exibição.
    """
    y_positions = list(range(len(labels)))
    lower_bounds = [ci[0] for ci in cis]
    upper_bounds = [ci[1] for ci in cis]

    fig = go.Figure()

    # Linha de nulo (effect size = 1.0 para razões, 0.0 para diferenças)
    null_line = 1.0 if any(es > 1.5 for es in effect_sizes) else 0.0
    fig.add_vline(
        x=null_line,
        line_dash="dash",
        line_color="gray",
        annotation_text="Nulo",
        annotation_position="top",
    )

    # Intervalos de confiança
    for i, (y, effect, lower, upper) in enumerate(
        zip(y_positions, effect_sizes, lower_bounds, upper_bounds)
    ):
        fig.add_trace(
            go.Scatter(
                x=[lower, upper],
                y=[y, y],
                mode="lines",
                line=dict(color="black", width=2),
                showlegend=False,
                hoverinfo="none",
            )
        )

        # Pontos centrais
        fig.add_trace(
            go.Scatter(
                x=[effect],
                y=[y],
                mode="markers",
                marker=dict(size=10, color="#FF6B6B"),
                name=f"Estudo {i + 1}" if i == 0 else None,
                showlegend=(i == 0),
                hovertemplate=f"<b>{labels[i]}</b><br>Efeito: {effect:.3f}<br>CI 95%: [{lower:.3f}, {upper:.3f}]<extra></extra>",
            )
        )

    fig.update_yaxes(
        ticktext=labels,
        tickvals=y_positions,
        categoryorder="array",
        categoryarray=y_positions[::-1],
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis_title="Tamanho de Efeito",
        yaxis_title="",
        height=height,
        template="plotly_white",
        showlegend=True,
    )

    return fig
