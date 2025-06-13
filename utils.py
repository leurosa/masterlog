import plotly.graph_objects as go
import streamlit as st

def gerar_grafico(df, colunas, rpm_col="RPM"):
    """
    Dual-axis: RPM no eixo direito; outras séries no esquerdo,
    mas escaladas para que o valor máximo de cada série atinja o topo.
    Hover mostra o valor real.
    """
    # Identifica as séries do lado esquerdo e o fator comum
    left_cols = [c for c in colunas if c != rpm_col]
    # Se não tiver série esquerda, só plota RPM normal
    if not left_cols:
        # plot RPM no eixo direito
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df[rpm_col], name=rpm_col, yaxis="y1", mode="lines"
        ))
        fig.update_layout(yaxis_title=rpm_col)
        st.plotly_chart(fig, use_container_width=True)
        return

    # 1) Encontra max individuais e max global
    max_vals   = {c: df[c].max() for c in left_cols}
    global_max = max(max_vals.values())

    # 2) Prepare traces
    fig = go.Figure()
    for col in left_cols:
        factor = global_max / max_vals[col] if max_vals[col] != 0 else 1
        y_scaled = df[col] * factor

        fig.add_trace(go.Scatter(
            x=df.index,
            y=y_scaled,
            name=col,
            yaxis="y1",
            mode="lines",
            connectgaps=False,
            # passa o valor real para hover via customdata
            customdata=df[col],
            hovertemplate=(
                f"<b>{col}</b><br>"
                "Valor real: %{customdata}<br>"
                "Escalado: %{y:.2f}<extra></extra>"
            )
        ))

    # 3) Plota RPM normalmente no eixo direito
    if rpm_col in colunas and rpm_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[rpm_col],
            name=rpm_col,
            yaxis="y2",
            line=dict(color="crimson", width=2),
            mode="lines",
            connectgaps=False,
            hovertemplate=f"<b>{rpm_col}</b><br>Valor: %{{y}}<extra></extra>"
        ))

    # 4) Layout com eixos e escalas
    fig.update_layout(
        xaxis=dict(title="Tempo (pontos de log)"),
        yaxis=dict(
            title="Séries escaladas",
            side="left",
            showgrid=True,
            range=[0, global_max * 1.05]
        ),
        yaxis2=dict(
            title=rpm_col,
            overlaying="y",
            side="right",
            showgrid=False,
            autorange=True
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=30, b=40),
        height=450,
        hovermode="x unified",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
