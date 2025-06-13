import pandas as pd
import plotly.graph_objects as go
from collections import Counter
import io
import streamlit as st

# Colunas que você não quer mostrar na pré-visualização
colunas_ignoradas = {
    "Mess 1", "Knock", "A/C Input", "Start Input", "Outputs 1",
    "Outputs 2", "Lambda 2", "Mess 2", "Strobo Angle", "ACC %",
    "ACP %", "dACC %", "0", "0_1"
}

def deduplicar_nomes(colunas):
    """
    Garante nomes únicos de coluna, adicionando sufixos _1, _2...
    """
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
    Divide o CSV em blocos sempre que encontrar uma linha começando com "Mess",
    gera um DataFrame para cada bloco e aplica todas as transformações.
    Retorna (lista_de_logs, None) ou (None, erro).
    """
    try:
        # 1) Leitura e limpeza das linhas
        content   = arquivo.getvalue().decode("utf-8")
        raw_lines = [l for l in content.splitlines() if l.strip()]
        logs      = []
        i = 0

        # 2) Loop principal: busca cada linha de cabeçalho "Mess"
        while i < len(raw_lines):
            line = raw_lines[i].strip()
            if line.startswith("Mess"):
                # 2.1) Deduplica nomes de colunas e extrai "Mess X"
                headers   = deduplicar_nomes(line.split(";"))
                nome_mess = headers[0]  # e.g. "Mess 1"

                # 2.2) Coleta as linhas de dados até o próximo "Mess" ou EOF
                j = i + 1
                segmento = []
                while j < len(raw_lines) and not raw_lines[j].strip().startswith("Mess"):
                    segmento.append(raw_lines[j])
                    j += 1

                # 2.3) Lê o bloco como CSV
                df = pd.read_csv(io.StringIO("\n".join(segmento)), sep=";", names=headers)

                # 3) Converte tudo para numérico (comma→dot)
                for col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(",", ".", regex=False),
                        errors="coerce"
                    )

                # 4) Suas transformações originais
                if "Batt Volt." in df.columns:
                    df["Batt Volt."] = (df["Batt Volt."] / 10).round(1)
                for col_temp in ["CLT", "IAT"]:
                    if col_temp in df.columns:
                        df[col_temp] = (df[col_temp] - 273.15).round(0)
                for col in ["Lambda 1", "Lambda Target"]:
                    if col in df.columns:
                        df[col] = (df[col] / 1000).round(2)
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

                # VE Corrigido
                if {"Lambda Corr", "VE Value"}.issubset(df.columns):
                    df["VE Corrigido"] = None
                    mask = (df["Lambda Loop"] != 0) if "Lambda Loop" in df.columns else True
                    df.loc[mask, "VE Corrigido"] = (
                        (df.loc[mask, "Lambda Corr"] / 1000 * df.loc[mask, "VE Value"])
                        * combustivel_extra
                    ).round(0).astype("Int64")

                # Correção percentual
                if "Lambda Corr" in df.columns:
                    def calc_corr(row):
                        if row.get("Lambda Loop", 1) == 0:
                            return None
                        lc = row["Lambda Corr"] / 1000
                        if pd.isna(lc):
                            return None
                        pct = (lc - 1) * 100
                        sinal = "+" if pct > 0 else "-"
                        return f"{sinal}{abs(pct):.2f}%"
                    df["Correção (%)"] = df.apply(calc_corr, axis=1)

                # 5) Prepara DataFrame visível
                vis_cols = [c for c in df.columns if c not in colunas_ignoradas]
                df_vis   = df[vis_cols]

                # 6) Armazena o bloco
                logs.append({
                "nome": nome_mess,
                "key":  f"{nome_mess.replace(' ','_')}_{len(logs)+1}",
                "df": df,
                "df_visivel": df_vis
            })

                # 7) Avança para o próximo bloco
                i = j
            else:
                i += 1

        return logs, None

    except Exception as e:
        return None, e


def gerar_grafico(df, colunas):
    fig = go.Figure()
    for col in colunas:
        # se for VE Value e existir VE Corrigido, só plota os válidos
        if col == "VE Value" and "VE Corrigido" in df.columns:
            mask   = df["VE Corrigido"].notna()
            x_plot = df.index[mask]
            y_plot = df.loc[mask, "VE Value"]
        else:
            x_plot = df.index
            y_plot = df[col]

        fig.add_trace(go.Scatter(
            x=x_plot,
            y=y_plot,
            mode='lines',
            name=col,
            hovertemplate=f"<b>{col}</b><br>Valor: %{{y}}<extra></extra>",
            connectgaps=False
        ))

    fig.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=30, b=40),
        hovermode='x unified',
        xaxis_title="Tempo (pontos de log)",
        yaxis_title="Valor",
        template='plotly_white'
    )
    st.plotly_chart(fig, use_container_width=True)
