import pandas as pd
import plotly.graph_objects as go
from collections import Counter
import io
import streamlit as st
import math

# Colunas que você não quer mostrar na pré-visualização
COLUNAS_IGNORADAS = {
    "Mess 1", "Knock", "A/C Input", "Start Input", "Outputs 1",
    "Outputs 2", "Lambda 2", "Mess 2", "Strobo Angle", "ACC %",
    "ACP %", "dACC %", "0", "0_1"
}

def deduplicar_nomes(colunas):
    """Garante nomes únicos de coluna, adicionando sufixos _1, _2..."""
    contagem = Counter()
    novas = []
    for nome in colunas:
        contagem[nome] += 1
        if contagem[nome] == 1:
            novas.append(nome)
        else:
            novas.append(f"{nome}_{contagem[nome]-1}")
    return novas

def processar_multiplos_logs(arquivo, combustivel_extra=1.0):
    """
    Divide o CSV em blocos ao encontrar 'Mess...', retorna (logs, None) ou (None, erro).
    Cada log é dict com: nome, key, df (completo) e df_visivel.
    """
    try:
        content   = arquivo.getvalue().decode("utf-8")
        raw_lines = [l for l in content.splitlines() if l.strip()]
        logs = []; i = 0

        while i < len(raw_lines):
            line = raw_lines[i].strip()
            if line.startswith("Mess"):
                headers   = deduplicar_nomes(line.split(";"))
                nome_mess = headers[0]
                j = i + 1; bloco = []
                while j < len(raw_lines) and not raw_lines[j].strip().startswith("Mess"):
                    bloco.append(raw_lines[j]); j += 1

                df = pd.read_csv(io.StringIO("\n".join(bloco)), sep=";", names=headers)
                for c in df.columns:
                    df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")

                # ajustes originais
                if "Batt Volt." in df: df["Batt Volt."] = (df["Batt Volt."] / 10).round(1)
                for tcol in ("CLT","IAT"):
                    if tcol in df: df[tcol] = (df[tcol] - 273.15).round(0)
                for lcol in ("Lambda 1","Lambda Target"):
                    if lcol in df:
                        df[lcol] = (df[lcol]/1000).round(2)
                        df[lcol] = df[lcol].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

                if {"Lambda Corr","VE Value"}.issubset(df.columns):
                    df["VE Corrigido"] = None
                    mask = df.get("Lambda Loop", pd.Series(1,index=df.index)) != 0
                    df.loc[mask,"VE Corrigido"] = (
                        df.loc[mask,"Lambda Corr"]/1000 * df.loc[mask,"VE Value"] * combustivel_extra
                    ).round(0).astype("Int64")

                if "Lambda Corr" in df.columns:
                    def pct(r):
                        if r.get("Lambda Loop",1)==0 or pd.isna(r["Lambda Corr"]): return None
                        val=(r["Lambda Corr"]/1000-1)*100; s="+" if val>0 else "-"
                        return f"{s}{abs(val):.2f}%"
                    df["Correção (%)"] = df.apply(pct,axis=1)

                vis = df[[c for c in df.columns if c not in COLUNAS_IGNORADAS]]
                logs.append({
                    "nome": nome_mess,
                    "key": f"{nome_mess.replace(' ','_')}_{len(logs)+1}",
                    "df": df,
                    "df_visivel": vis
                })
                i = j
            else:
                i += 1

        return logs, None

    except Exception as e:
        return None, e

def gerar_grafico(df, colunas, rpm_col="RPM"):
    # divide colunas
    left_cols = [c for c in colunas if c != rpm_col]

    fig = go.Figure()

    # traça cada série no eixo log (y1)
    for c in left_cols:
        serie = pd.to_numeric(df[c], errors="coerce")
        # evita zeros no log (substitui por NaN)
        serie = serie.replace(0, pd.NA)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=serie,
            name=c,
            yaxis="y1",
            mode="lines",
            connectgaps=True,
            hovertemplate=f"<b>{c}</b><br>Valor: %{{y}}<extra></extra>"
        ))

    # plota RPM no eixo direito normal
    if rpm_col in colunas and rpm_col in df.columns:
        rpm = pd.to_numeric(df[rpm_col], errors="coerce")
        fig.add_trace(go.Scatter(
            x=df.index,
            y=rpm,
            name=rpm_col,
            yaxis="y2",
            line=dict(color="crimson", width=2),
            mode="lines",
            connectgaps=True,
            hovertemplate=f"<b>{rpm_col}</b><br>Valor: %{{y}}<extra></extra>"
        ))

    # layout com log scale no y1
    fig.update_layout(
        xaxis=dict(title="Tempo (pontos de log)"),
        yaxis=dict(
            title="Valores (escala log)",
            type="log",
            side="left",
            showgrid=True,
            gridcolor="#999999",
            zeroline=False
        ),
        yaxis2=dict(
            title=rpm_col,
            overlaying="y",
            side="right",
            showgrid=False,
            autorange=True
        ),
        legend=dict(
            orientation="v",
            x=0,
            y=1,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(0,0,0,0.2)"
        ),
        margin=dict(l=50, r=50, t=30, b=40),
        height=450,
        hovermode="x unified",
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)
