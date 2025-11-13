import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO
import pydeck as pdk

# Configuração da página
st.set_page_config(
    page_title="Dashboard IBGE Cidades",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para melhorar a aparência
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #f0f2f6 0%, #ffffff 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .research-question {
        background-color: #e3f2fd;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">📊 Dashboard IBGE Cidades — Análise — Stremilit</div>', unsafe_allow_html=True)

@st.cache_data
def load_df(path="dados_lista.csv"):
    df = pd.read_csv(path, sep=",", encoding="utf-8")
    return df

# Load data
with st.spinner("🔄 Carregando dados..."):
    df = load_df()

# Helper functions
def available_year_cols(prefix):
    cols = [c for c in df.columns if c.startswith(prefix + "_")]
    def year_of(c):
        parts = c.rsplit("_", 1)
        try:
            return int(parts[-1])
        except:
            return 0
    return sorted(cols, key=year_of)

pop_cols = available_year_cols("populacao_estimada")
pib_cols = available_year_cols("pib_per_capita")
idh_cols = [c for c in df.columns if c.startswith("idh_")]
bioma_cols = [c for c in df.columns if c.startswith("bioma_")]

# ============ SIDEBAR ============
st.sidebar.markdown("## 🎯 Filtros de Análise")

# Filtros
if "estado" in df.columns:
    estados = sorted(df["estado"].dropna().unique())
    estado_sel = st.sidebar.multiselect(
        "🗺️ Estados",
        estados,
        default=estados[:5] if len(estados) > 5 else estados,
        help="Selecione um ou mais estados para análise"
    )
else:
    estado_sel = []

# Seleção de anos
st.sidebar.markdown("### 📅 Seleção de Períodos")
pop_col = st.sidebar.selectbox("Ano - População", pop_cols, index=len(pop_cols)-1) if pop_cols else None
pib_col = st.sidebar.selectbox("Ano - PIB per capita", pib_cols, index=len(pib_cols)-1) if pib_cols else None
idh_col = st.sidebar.selectbox("Ano - IDH", idh_cols, index=len(idh_cols)-1) if idh_cols else None

# Filtro de população
if pop_col:
    tmp = pd.to_numeric(df[pop_col], errors="coerce")
    max_pop = int(np.nanmax(tmp.fillna(0)))
    min_pop = st.sidebar.slider(
        "👥 População mínima",
        0, max_pop, 0,
        step=max(1, max_pop//20),
        format="%d"
    )
else:
    min_pop = 0

# Top N
top_n = st.sidebar.slider("🏆 Top N municípios", 5, 50, 15, 5)

# Apply filters
df_filtered = df.copy()
if estado_sel and "estado" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["estado"].isin(estado_sel)]
if pop_col:
    df_filtered[pop_col] = pd.to_numeric(df_filtered[pop_col], errors="coerce")
    df_filtered = df_filtered[df_filtered[pop_col].fillna(0) >= min_pop]

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.metric("📊 Registros Filtrados", f"{len(df_filtered):,}")
if pop_col:
    total_pop = int(df_filtered[pop_col].sum(min_count=1) if df_filtered[pop_col].notna().any() else 0)
    st.sidebar.metric("👥 População Total", f"{total_pop:,}")

# Export button
if st.sidebar.button("💾 Exportar CSV", use_container_width=True):
    buf = BytesIO()
    df_filtered.to_csv(buf, index=False)
    st.sidebar.download_button(
        "⬇️ Download CSV",
        data=buf.getvalue(),
        file_name="dados_filtrados.csv",
        mime="text/csv",
        use_container_width=True
    )

# ============ RESEARCH QUESTIONS ============
st.markdown("### 🔬 Perguntas de Pesquisa")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="research-question">
        <h4>1️⃣ Distribuição Populacional</h4>
        <p>Como a população se distribui entre estados e biomas brasileiros? Quais são os municípios mais populosos?</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="research-question">
        <h4>2️⃣ Desenvolvimento Econômico</h4>
        <p>Existe relação entre tamanho populacional e desenvolvimento econômico (PIB per capita)? Como varia por estado?</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="research-question">
        <h4>3️⃣ Qualidade de Vida</h4>
        <p>Como o IDH varia entre estados e regiões? Municípios maiores têm melhor qualidade de vida?</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============ TABS ============
tab1, tab2, tab3, tab4 = st.tabs([
    "🏙️ Distribuição Populacional",
    "💰 Desenvolvimento Econômico",
    "🌟 Qualidade de Vida (IDH)",
    "🗺️ Visão Geográfica"
])

# ============ TAB 1: DISTRIBUIÇÃO POPULACIONAL ============
with tab1:
    st.markdown("## 📊 Pergunta 1: Como a população se distribui?")
    
    # Gráfico 1: Top municípios por população
    st.markdown("### 🏆 Municípios Mais Populosos")
    if pop_col and "municipio" in df_filtered.columns:
        df_top = df_filtered.copy()
        df_top[pop_col] = pd.to_numeric(df_top[pop_col], errors="coerce").fillna(0)
        df_top = df_top.nlargest(top_n, pop_col)
        
        # Criar label mais informativo
        df_top['label'] = df_top['municipio'] + ' - ' + df_top['estado']
        
        fig1 = px.bar(
            df_top.sort_values(pop_col),
            x=pop_col,
            y='label',
            orientation='h',
            color='estado',
            title=f'Top {top_n} Municípios por População ({pop_col.split("_")[-1]})',
            labels={pop_col: 'População Estimada', 'label': 'Município - Estado'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig1.update_layout(
            height=600,
            showlegend=True,
            xaxis_title="População",
            yaxis_title="",
            font=dict(size=12),
            title={
                'text': f"Gráfico 1: Top {top_n} Municípios por População ({pop_col.split('_')[-1]})",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#1f77b4'}
            }
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Ranking dos {top_n} municípios com maior população estimada no ano de {pop_col.split('_')[-1]}, organizados por estado. As cores representam diferentes unidades federativas, facilitando a identificação da concentração populacional regional.</i></p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico 2: Distribuição por Estado
        st.markdown("### 🗺️ População por Estado")
        if pop_col and "estado" in df_filtered.columns:
            df_estado = df_filtered.groupby('estado')[pop_col].sum().reset_index()
            df_estado = df_estado.sort_values(pop_col, ascending=False)
            
            fig2 = px.bar(
                df_estado,
                x='estado',
                y=pop_col,
                color=pop_col,
                color_continuous_scale='Blues',
                title='População Total por Estado',
                labels={pop_col: 'População Total', 'estado': 'Estado'}
            )
            fig2.update_layout(
                height=400, 
                showlegend=False,
                title={
                    'text': "Gráfico 2: População Total por Estado",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Soma total da população por unidade federativa. A intensidade da cor azul indica o volume populacional, permitindo identificar rapidamente os estados mais populosos do Brasil.</i></p>", unsafe_allow_html=True)
    
    with col2:
        # Gráfico 3: Distribuição por Bioma
        st.markdown("### 🌳 População por Bioma")
        bioma_col = bioma_cols[-1] if bioma_cols else None
        if bioma_col and pop_col:
            df_bioma = df_filtered.copy()
            df_bioma[bioma_col] = df_bioma[bioma_col].fillna("Sem informação")
            df_bioma_grouped = df_bioma.groupby(bioma_col)[pop_col].sum().reset_index()
            
            fig3 = px.pie(
                df_bioma_grouped,
                values=pop_col,
                names=bioma_col,
                title='Distribuição Populacional por Bioma',
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4
            )
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            fig3.update_layout(
                height=400,
                title={
                    'text': "Gráfico 3: Distribuição Populacional por Bioma",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Distribuição percentual da população brasileira entre os principais biomas nacionais. Cada fatia representa a proporção populacional em Amazônia, Cerrado, Mata Atlântica, Caatinga, Pampa e Pantanal.</i></p>", unsafe_allow_html=True)

# ============ TAB 2: DESENVOLVIMENTO ECONÔMICO ============
with tab2:
    st.markdown("## 💰 Pergunta 2: População e Desenvolvimento Econômico")
    
    # Gráfico 4: Scatter População x PIB
    st.markdown("### 📈 Relação População × PIB per capita")
    if pop_col and pib_col and "municipio" in df_filtered.columns:
        df_scatter = df_filtered.copy()
        df_scatter[pop_col] = pd.to_numeric(df_scatter[pop_col], errors="coerce")
        df_scatter[pib_col] = pd.to_numeric(df_scatter[pib_col], errors="coerce")
        df_scatter = df_scatter.dropna(subset=[pop_col, pib_col])
        
        # Adicionar categoria de porte
        df_scatter['porte'] = pd.cut(
            df_scatter[pop_col],
            bins=[0, 20000, 100000, 500000, float('inf')],
            labels=['Pequeno', 'Médio', 'Grande', 'Metrópole']
        )
        
        fig4 = px.scatter(
            df_scatter,
            x=pop_col,
            y=pib_col,
            color='estado',
            size=pib_col,
            hover_name='municipio',
            hover_data={'estado': True, pop_col: ':,', pib_col: ':,.2f', 'porte': True},
            title='População vs PIB per capita por Estado',
            labels={pop_col: 'População', pib_col: 'PIB per capita (R$)'},
            log_x=True,
            opacity=0.7
        )
        fig4.update_layout(
            height=600,
            title={
                'text': "Gráfico 4: Relação entre População e PIB per capita",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#1f77b4'}
            }
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Análise da relação entre tamanho populacional (eixo horizontal em escala logarítmica) e PIB per capita (eixo vertical). O tamanho das bolhas representa o PIB per capita, enquanto as cores diferenciam os estados, revelando padrões de desenvolvimento econômico.</i></p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico 5: PIB médio por Estado
        st.markdown("### 💵 PIB per capita Médio por Estado")
        if pib_col and "estado" in df_filtered.columns:
            df_pib_estado = df_filtered.copy()
            df_pib_estado[pib_col] = pd.to_numeric(df_pib_estado[pib_col], errors="coerce")
            df_pib_grouped = df_pib_estado.groupby('estado')[pib_col].mean().reset_index()
            df_pib_grouped = df_pib_grouped.sort_values(pib_col, ascending=True)
            
            fig5 = px.bar(
                df_pib_grouped,
                x=pib_col,
                y='estado',
                orientation='h',
                color=pib_col,
                color_continuous_scale='Greens',
                title='PIB per capita Médio por Estado',
                labels={pib_col: 'PIB per capita Médio (R$)', 'estado': 'Estado'}
            )
            fig5.update_layout(
                height=500, 
                showlegend=False,
                title={
                    'text': "Gráfico 5: PIB per capita Médio por Estado",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            st.plotly_chart(fig5, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>PIB per capita médio dos municípios por estado, ordenados do menor para o maior valor. A escala de cores verde indica a intensidade econômica, permitindo comparações diretas entre as unidades federativas.</i></p>", unsafe_allow_html=True)
    
    with col2:
        # Gráfico 6: Distribuição de PIB por porte
        st.markdown("### 📊 PIB per capita por Porte do Município")
        if pop_col and pib_col:
            df_porte = df_filtered.copy()
            df_porte[pop_col] = pd.to_numeric(df_porte[pop_col], errors="coerce")
            df_porte[pib_col] = pd.to_numeric(df_porte[pib_col], errors="coerce")
            df_porte = df_porte.dropna(subset=[pop_col, pib_col])
            
            df_porte['porte'] = pd.cut(
                df_porte[pop_col],
                bins=[0, 20000, 100000, 500000, float('inf')],
                labels=['Pequeno\n(<20k)', 'Médio\n(20-100k)', 'Grande\n(100-500k)', 'Metrópole\n(>500k)']
            )
            
            fig6 = px.box(
                df_porte,
                x='porte',
                y=pib_col,
                color='porte',
                title='Distribuição do PIB per capita por Porte Municipal',
                labels={pib_col: 'PIB per capita (R$)', 'porte': 'Porte do Município'},
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig6.update_layout(
                height=500, 
                showlegend=False,
                title={
                    'text': "Gráfico 6: PIB per capita por Porte Municipal",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            st.plotly_chart(fig6, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Boxplot mostrando a distribuição do PIB per capita segundo o porte municipal (Pequeno: <20k hab.; Médio: 20-100k; Grande: 100-500k; Metrópole: >500k). As caixas representam a mediana e quartis, enquanto os pontos externos indicam outliers.</i></p>", unsafe_allow_html=True)

# ============ TAB 3: QUALIDADE DE VIDA ============
with tab3:
    st.markdown("## 🌟 Pergunta 3: Como varia a Qualidade de Vida (IDH)?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico 7: IDH por Estado (Boxplot)
        st.markdown("### 📊 Distribuição do IDH por Estado")
        if idh_col and "estado" in df_filtered.columns:
            df_idh = df_filtered.copy()
            df_idh[idh_col] = pd.to_numeric(df_idh[idh_col], errors="coerce")
            df_idh = df_idh.dropna(subset=[idh_col])
            
            # Calcular médias para ordenar
            estado_order = df_idh.groupby('estado')[idh_col].mean().sort_values(ascending=False).index
            
            fig7 = px.box(
                df_idh,
                x='estado',
                y=idh_col,
                color='estado',
                title=f'Distribuição do IDH por Estado ({idh_col.split("_")[-1]})',
                labels={idh_col: 'IDH', 'estado': 'Estado'},
                category_orders={'estado': estado_order}
            )
            fig7.update_layout(
                height=500, 
                showlegend=False,
                title={
                    'text': f"Gráfico 7: Distribuição do IDH por Estado ({idh_col.split('_')[-1]})",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            fig7.add_hline(y=0.7, line_dash="dash", line_color="red", 
                          annotation_text="IDH Alto (0.7)")
            st.plotly_chart(fig7, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Distribuição do Índice de Desenvolvimento Humano (IDH) por estado, ordenados pela média decrescente. A linha tracejada vermelha marca o limiar de IDH Alto (0,7), conforme classificação do PNUD. As caixas mostram a variação dentro de cada estado.</i></p>", unsafe_allow_html=True)
    
    with col2:
        # Gráfico 8: IDH vs População
        st.markdown("### 👥 IDH × Tamanho Populacional")
        if idh_col and pop_col:
            df_idh_pop = df_filtered.copy()
            df_idh_pop[idh_col] = pd.to_numeric(df_idh_pop[idh_col], errors="coerce")
            df_idh_pop[pop_col] = pd.to_numeric(df_idh_pop[pop_col], errors="coerce")
            df_idh_pop = df_idh_pop.dropna(subset=[idh_col, pop_col])
            
            df_idh_pop['porte'] = pd.cut(
                df_idh_pop[pop_col],
                bins=[0, 20000, 100000, 500000, float('inf')],
                labels=['Pequeno', 'Médio', 'Grande', 'Metrópole']
            )
            
            fig8 = px.violin(
                df_idh_pop,
                x='porte',
                y=idh_col,
                color='porte',
                box=True,
                title='IDH por Porte Municipal (Violino + Box)',
                labels={idh_col: 'IDH', 'porte': 'Porte do Município'},
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig8.update_layout(
                height=500, 
                showlegend=False,
                title={
                    'text': "Gráfico 8: IDH por Porte Municipal (Violin Plot)",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#1f77b4'}
                }
            )
            st.plotly_chart(fig8, use_container_width=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Gráfico de violino combinado com boxplot, mostrando a distribuição do IDH segundo o porte populacional dos municípios. A forma do violino indica a densidade de municípios em cada faixa de IDH, revelando se municípios maiores tendem a ter melhor desenvolvimento humano.</i></p>", unsafe_allow_html=True)
    
    # Gráfico adicional: Top e Bottom IDH
    st.markdown("### 🏅 Melhores e Piores IDH")
    if idh_col and "municipio" in df_filtered.columns:
        df_idh_ranking = df_filtered.copy()
        df_idh_ranking[idh_col] = pd.to_numeric(df_idh_ranking[idh_col], errors="coerce")
        df_idh_ranking = df_idh_ranking.dropna(subset=[idh_col])
        
        top_10 = df_idh_ranking.nlargest(10, idh_col)[['municipio', 'estado', idh_col]].copy()
        top_10['categoria'] = 'Top 10 Melhores'
        
        bottom_10 = df_idh_ranking.nsmallest(10, idh_col)[['municipio', 'estado', idh_col]].copy()
        bottom_10['categoria'] = 'Top 10 Piores'
        
        df_comparison = pd.concat([top_10, bottom_10])
        df_comparison['label'] = df_comparison['municipio'] + ' - ' + df_comparison['estado']
        
        fig9 = px.bar(
            df_comparison,
            x=idh_col,
            y='label',
            color='categoria',
            orientation='h',
            title='Municípios com Melhor e Pior IDH',
            labels={idh_col: 'IDH', 'label': 'Município'},
            color_discrete_map={'Top 10 Melhores': '#2ecc71', 'Top 10 Piores': '#e74c3c'}
        )
        fig9.update_layout(
            height=600,
            title={
                'text': "Gráfico 9: Municípios com Melhor e Pior IDH",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#1f77b4'}
            }
        )
        st.plotly_chart(fig9, use_container_width=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Comparação direta entre os 10 municípios com melhor IDH (verde) e os 10 com pior IDH (vermelho) dentre os municípios filtrados. Esta visualização evidencia as desigualdades regionais no desenvolvimento humano brasileiro.</i></p>", unsafe_allow_html=True)

# ============ TAB 4: VISÃO GEOGRÁFICA ============
with tab4:
    st.markdown("## 🗺️ Visualização Geográfica")
    
    if ("latitude" in df_filtered.columns) and ("longitude" in df_filtered.columns):
        df_map = df_filtered.copy()
        df_map["latitude"] = pd.to_numeric(df_map["latitude"], errors="coerce")
        df_map["longitude"] = pd.to_numeric(df_map["longitude"], errors="coerce")
        df_map = df_map.dropna(subset=["latitude", "longitude"])
        
        if pop_col in df_map.columns:
            df_map[pop_col] = pd.to_numeric(df_map[pop_col], errors="coerce").fillna(0)
        if idh_col in df_map.columns:
            df_map[idh_col] = pd.to_numeric(df_map[idh_col], errors="coerce").fillna(0)
        
        # Mapa 2D com Plotly
        st.markdown("### 🌎 Mapa Interativo 2D")
        size_col = pop_col if pop_col in df_map.columns else None
        color_col = idh_col if idh_col in df_map.columns else None
        
        fig_map = px.scatter_mapbox(
            df_map,
            lat="latitude",
            lon="longitude",
            hover_name="municipio",
            hover_data={"estado": True, pop_col: ":,", idh_col: ":.3f"},
            size=size_col,
            color=color_col,
            color_continuous_scale="RdYlGn",
            size_max=20,
            zoom=3.5,
            height=600,
            title="Municípios Brasileiros: Tamanho = População, Cor = IDH"
        )
        fig_map.update_layout(
            mapbox_style="open-street-map",
            title={
                'text': "Mapa 1: Localização Geográfica dos Municípios",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#1f77b4'}
            }
        )
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -1rem;'><i>Visualização geoespacial interativa dos municípios brasileiros. O tamanho dos marcadores é proporcional à população, enquanto a cor representa o IDH (verde = alto, amarelo = médio, vermelho = baixo). Permite identificar concentrações populacionais e padrões de desenvolvimento regional.</i></p>", unsafe_allow_html=True)
        
        # Mapa 3D com PyDeck
        st.markdown("### 🏙️ Mapa 3D com Barras (População)")
        if pop_col in df_map.columns:
            df_map["pop_norm"] = (df_map[pop_col] / df_map[pop_col].max()) * 500000
            
            view_state = pdk.ViewState(
                latitude=df_map["latitude"].mean(),
                longitude=df_map["longitude"].mean(),
                zoom=3.5,
                pitch=50,
                bearing=-30
            )
            
            column_layer = pdk.Layer(
                "ColumnLayer",
                data=df_map,
                get_position=["longitude", "latitude"],
                get_elevation="pop_norm",
                elevation_scale=0.1,
                radius=10000,
                get_fill_color=[255, 140, 0, 180],
                pickable=True,
                auto_highlight=True,
            )
            
            tooltip = {
                "html": "<b>{municipio}</b><br/>Estado: {estado}<br/>População: {" + pop_col + ":,}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
            
            r = pdk.Deck(
                layers=[column_layer],
                initial_view_state=view_state,
                tooltip=tooltip,
            )
            st.pydeck_chart(r, use_container_width=True)
            st.caption("**Mapa 2:** Representação tridimensional dos municípios brasileiros onde a altura das colunas é proporcional à população. Esta visualização permite identificar intuitivamente os grandes centros urbanos e suas distribuições pelo território nacional.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem; background-color: #f0f2f6; border-radius: 10px;'>
    <h3 style='color: #1f77b4; margin-bottom: 1rem;'>📊 Dashboard IBGE Cidades</h3>
    <p style='color: #666; margin: 0.5rem 0;'>
        <strong>Disciplina:</strong> Processamento e Visualização de Dados<br>
        <strong>Professora:</strong> Prof. Dra. Marcela Xavier
    </p>
    <p style='color: #666; margin: 1rem 0 0.5rem 0;'>
        <strong>Desenvolvido por:</strong>
    </p>
    <p style='color: #444; margin: 0.3rem 0;'>
        👨‍💻 João Vitor Ribeiro de Oliveira - RA: 813109<br>
        👨‍💻 Levir Daymmon - RA: XXXXXX
    </p>
    <p style='color: #999; margin: 1.5rem 0 0 0; font-size: 0.9rem;'>
        Dados do Instituto Brasileiro de Geografia e Estatística (IBGE) | 9 Visualizações Interativas
    </p>
</div>
""", unsafe_allow_html=True)