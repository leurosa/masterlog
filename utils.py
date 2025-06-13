import pandas as pd
import plotly.graph_objects as go
from collections import Counter
import io
import streamlit as st

colunas_ignoradas = {
    "Mess 1", "Knock", "A/C Input", "Start Input", "Outputs 1",
    "Outputs 2", "Lambda 2", "Mess 2", "Strobo Angle", "ACC %", "ACP %", "dACC %", "0", "0_1"
}

def deduplicar_nomes(colunas):
    contagem = Counter()
    novas_colunas = []
    for nome in colunas:
        contagem[nome] += 1
        if contagem[nome] == 1:
            novas_colunas.append(nome)
        else:
            novas_colunas.append(f"{nome}_{contagem[nome] - 1}")
    return novas_colunas

def processar_multiplos_logs(arquivo):
    try:
        content = arquivo.getvalue().decode("utf-8")
        raw_lines = content.splitlines()

        logs = []
        i = 0
        while i < len(raw_lines):
            if raw_lines[i].strip().startswith("NEW_LOG"):
                if i + 1 >= len(raw_lines):
                    break  # Arquivo mal formatado

                # 🕒 Extrair hora do NEW_LOG
                partes = raw_lines[i].strip().split()
                hora_log = partes[1] if len(partes) > 1 else "??:??:??"

                header_line = raw_lines[i + 1]
                headers = deduplicar_nomes(header_line.split(';'))

                # Dados começam na linha i + 2
                j = i + 2
                while j < len(raw_lines) and not raw_lines[j].startswith("NEW_LOG"):
                    j += 1

                dados_csv = '\n'.join(raw_lines[i + 2:j])
                df = pd.read_csv(io.StringIO(dados_csv), sep=';', names=headers)

                for col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')

                # Converter CLT e IAT de Kelvin para Celsius
                for col_batt in ["Batt Volt."]:
                    if col_batt in df.columns:
                        df[col_batt] = (df[col_batt]/10).round(1)    
                        
                # Converter CLT e IAT de Kelvin para Celsius
                for col_temp in ["CLT", "IAT"]:
                    if col_temp in df.columns:
                        df[col_temp] = (df[col_temp] - 273.15).round(0) 

                for col in ["Lambda 1", "Lambda Target"]:
                    if col in df.columns:
                        df[col] = (df[col] / 1000).round(2)
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

                mascara_malha_fechada = df["Lambda Loop"] != 0 if "Lambda Loop" in df.columns else pd.Series([True] * len(df))

                if {"Lambda Corr", "VE Value"}.issubset(df.columns):
                    df["VE Corrigido"] = None
                    df.loc[mascara_malha_fechada, "VE Corrigido"] = (
                        (df.loc[mascara_malha_fechada, "Lambda Corr"] / 1000 * df.loc[mascara_malha_fechada, "VE Value"])
                    ).round(0).astype('Int64')

                if "Lambda Corr" in df.columns:
                    def calcular_correcao(row):
                        if "Lambda Loop" in row and row["Lambda Loop"] == 0:
                            return None
                        try:
                            lambda_corr = row["Lambda Corr"] / 1000
                            if pd.isna(lambda_corr):
                                return None
                            correcao_percentual = (lambda_corr - 1) * 100
                            sinal = "+" if correcao_percentual > 0 else "-"
                            return f"{sinal}{abs(correcao_percentual):.2f}%"
                        except:
                            return None
                    df["Correção (-Tirando +Colocando Comb.)"] = df.apply(calcular_correcao, axis=1)

                colunas_visiveis = [col for col in df.columns if col not in colunas_ignoradas]
                df_visivel = df[colunas_visiveis]

                logs.append({
                    "df": df,
                    "df_visivel": df_visivel,
                    "nome": f"Log {len(logs) + 1} - {hora_log}"
                })

                i = j
            else:
                i += 1

        return logs, None
    except Exception as e:
        return None, e


def gerar_grafico(df, colunas):
    fig = go.Figure()
    for col in colunas:
        if col == "VE Value" and "VE Corrigido" in df.columns:
            mascara = df["VE Corrigido"].notna()
            x_plot = list(df.index[mascara])
            y_plot = df.loc[mascara, "VE Value"]
        else:
            y_plot = df[col]
            x_plot = list(df.index)
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
