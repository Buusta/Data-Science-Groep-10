import pandas as pd
import streamlit as st
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px

sns.set_style("whitegrid")

# --- Sidebar navigatie ---
st.sidebar.header("Navigatie")
pagina = st.sidebar.radio("Kies een pagina:", ["Pagina 1", "Pagina 2", "Pagina 3"])

if pagina == "Pagina 1":
    st.title("Laadpaal Data Dashboard")
    st.markdown('**********zullen we deze tabel/filter weghalen?')

    # --- Jaar selecteren ---
    jaar = st.sidebar.selectbox("Kies dataset:", ["2018", "2022", "Beide"])

    # --- 2018 CSV laden ---
    df_2018 = pd.read_csv('laadpaaldata.csv')
    df_2018['Started'] = df_2018['Started'].replace('2018-02-29 07:37:53', '2018-02-28 07:37:53')
    df_2018['Ended'] = df_2018['Ended'].replace({
        '2018-02-29 07:46:07': '2018-02-28 07:46:07',
        '2018-02-29 16:46:45': '2018-02-28 16:46:45'
    })
    df_2018['Started'] = pd.to_datetime(df_2018['Started'], errors='coerce')
    df_2018['Ended'] = pd.to_datetime(df_2018['Ended'], errors='coerce')
    for col in ['TotalEnergy', 'ChargeTime', 'ConnectedTime', 'MaxPower']:
        df_2018[col] = pd.to_numeric(df_2018[col], errors='coerce')

    # --- 2022 PKL laden ---
    df_2022 = pd.read_pickle('charging_data.pkl')

    # --- Zet charging_duration om naar uren float ---
    def duration_to_hours(duration):
        if pd.isna(duration):
            return 0
        if isinstance(duration, pd.Timedelta):
            return duration.total_seconds() / 3600
        try:
            parts = str(duration).split(':')
            if len(parts) == 3:
                h, m, s = map(int, parts)
            elif len(parts) == 2:
                h, m = map(int, parts)
                s = 0
            else:
                h, m, s = 0, 0, 0
            return h + m / 60 + s / 3600
        except:
            return 0

    df_2022['ChargeTime'] = df_2022['charging_duration'].apply(duration_to_hours)
    df_2022['ConnectedTime'] = df_2022['ChargeTime']
    df_2022['TotalEnergy'] = pd.to_numeric(df_2022['energy_delivered [kWh]'], errors='coerce') * 1000
    df_2022['MaxPower'] = pd.to_numeric(df_2022['max_charging_power [kW]'], errors='coerce') * 1000
    df_2022['N_phases'] = pd.to_numeric(df_2022['N_phases'], errors='coerce')
    df_2022['start_time'] = pd.to_datetime(df_2022['start_time'], errors='coerce')
    df_2022['exit_time'] = pd.to_datetime(df_2022['exit_time'], errors='coerce')

    # --- Feature engineering ---
    def add_features(df):
        df['ChargeTime'] = df['ChargeTime'].clip(lower=0)
        df['ConnectedTime'] = df['ConnectedTime'].clip(lower=0)
        df['GemiddeldVermogen'] = df.apply(
            lambda row: row['TotalEnergy'] / row['ChargeTime'] if row['ChargeTime'] > 0 else 0, axis=1
        )
        df['Efficiëntie'] = df.apply(
            lambda row: row['ChargeTime'] / row['ConnectedTime'] if row['ConnectedTime'] > 0 else 0, axis=1
        )
        df['IdleTijd'] = (df['ConnectedTime'] - df['ChargeTime']).clip(lower=0)
        df['VermogensRatio'] = df.apply(
            lambda row: row['GemiddeldVermogen'] / row['MaxPower'] if row['MaxPower'] > 0 else 0, axis=1
        )
        df['LaadEfficiëntie'] = df.apply(
            lambda row: row['TotalEnergy'] / row['ConnectedTime'] if row['ConnectedTime'] > 0 else 0, axis=1
        )
        df['IdleRatio'] = df.apply(
            lambda row: row['IdleTijd'] / row['ConnectedTime'] if row['ConnectedTime'] > 0 else 0, axis=1
        )

        def categoriseer_sessie(uren):
            if uren < 1:
                return 'Kort'
            elif uren <= 3:
                return 'Gemiddeld'
            else:
                return 'Lang'

        df['Sessielengte'] = df['ChargeTime'].apply(categoriseer_sessie)
        return df

    df_2018 = add_features(df_2018)
    df_2022 = add_features(df_2022)

    # --- Dataset selectie ---
    if jaar == "2018":
        df_plot = df_2018.copy()
    elif jaar == "2022":
        df_plot = df_2022.copy()
    else:
        df_2018['Jaar'] = 2018
        df_2022['Jaar'] = 2022
        df_plot = pd.concat([df_2018, df_2022], ignore_index=True)

    df_plot.replace([float('inf'), float('-inf')], pd.NA, inplace=True)

    # --- Checkbox uitleg ---
    toon_uitleg = st.checkbox("Laat uitleg van de data zien", value=True)
    if toon_uitleg:
        with st.expander("Overzicht van toegevoegde features", expanded=True):
            feature_info = {
                "Kolom": ["GemiddeldVermogen", "Efficiëntie", "IdleTijd", "VermogensRatio",
                          "LaadEfficiëntie", "IdleRatio", "Sessielengte"],
                "Betekenis": ["Gemiddeld vermogen tijdens laden",
                              "Aandeel van verbonden tijd dat echt geladen is",
                              "Tijd verbonden, maar niet ladend",
                              "Gemiddeld vermogen / Max vermogen",
                              "Energie per verbonden uur",
                              "IdleTijd / ConnectedTime",
                              "Kort / Gemiddeld / Lang"],
                "Nuttig voor": ["Vergelijking laadpaal prestaties",
                                "Inzicht in benutting van de laadpaal",
                                "Blokkeringstijd voor andere EV’s",
                                "Maximale benutting laadpaal",
                                "Effectieve energieafgifte",
                                "Efficiëntieanalyse van sessies",
                                "Snel groeperen en analyseren van sessies"]
            }
            st.table(pd.DataFrame(feature_info))

    # --- Checkbox voor outliers filteren ---
    filter_outliers = st.checkbox("Filter onrealistische outliers", value=True)
    if filter_outliers:
        df_filtered = df_plot[
            (df_plot['ChargeTime'] <= 24) &
            (df_plot['ConnectedTime'] <= 24) &
            (df_plot['VermogensRatio'] <= 1) &
            (df_plot['IdleRatio'] <= 1)
        ].copy()
    else:
        df_filtered = df_plot.copy()

    # --- DataFrame bekijken ---
    with st.expander("Laadpaal DataFrame bekijken", expanded=False):
        st.dataframe(df_filtered)

    # --- Overzicht statistieken ---
    st.subheader("Overzicht statistieken van alle kolommen")
    with st.expander("Bekijk overzicht statistiek", expanded=False):
        num_cols = ['ChargeTime', 'ConnectedTime', 'TotalEnergy', 'MaxPower',
                    'GemiddeldVermogen', 'Efficiëntie', 'IdleTijd',
                    'VermogensRatio', 'LaadEfficiëntie', 'IdleRatio']
        df_stats = df_filtered[num_cols].describe().T
        st.dataframe(df_stats)

    st.markdown('****dit overzicht is misschien en beetje te uitgebreid om te presenteren voor het publiek. zullen we het houden op de (overview) tabel hieronder? en  zal ik dit dan zo laten of als een filter weergeven?')
    # --- Functie voor histogram ---
    def plot_histogram(df_part, stacked=False, log_y=False, title=''):
        df_part['IdleTijd'] = df_part['IdleTijd'].clip(lower=0)
        custom_data = df_part[['GemiddeldVermogen', 'Efficiëntie', 'IdleRatio']].values
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_part['ChargeTime'],
            name='Laadtijd',
            nbinsx=30,
            opacity=0.8,
            marker=dict(color='#4CAF50', line=dict(color='darkgreen', width=1.5)),
            customdata=custom_data,
            hovertemplate=(
                'ChargeTime: %{x} uur<br>'
                'Aantal sessies: %{y}<br>'
                'Gemiddeld Vermogen: %{customdata[0]:.0f} W<br>'
                'Efficiëntie: %{customdata[1]:.2f}<br>'
                'IdleRatio: %{customdata[2]:.2f}<extra></extra>'
            )
        ))
        if stacked:
            fig.add_trace(go.Histogram(
                x=df_part['IdleTijd'],
                name='IdleTijd',
                nbinsx=30,
                opacity=0.8,
                marker=dict(color='#FFC107', line=dict(color='orange', width=1.5)),
                customdata=custom_data,
                hovertemplate=(
                    'IdleTijd: %{x} uur<br>'
                    'Aantal sessies: %{y}<br>'
                    'Gemiddeld Vermogen: %{customdata[0]:.0f} W<br>'
                    'Efficiëntie: %{customdata[1]:.2f}<br>'
                    'IdleRatio: %{customdata[2]:.2f}<extra></extra>'
                )
            ))
        fig.update_layout(
            barmode='stack' if stacked else 'overlay',
            xaxis_title='Tijd (uren)',
            yaxis_title='Aantal sessies',
            yaxis_type='log' if log_y else 'linear',
            title=title,
            template='plotly_white',
            legend=dict(x=0.8, y=0.95)
        )
        st.plotly_chart(fig, use_container_width=True)



    # --- Interactieve hover plot voor 2022 ---
    def plot_histogram_hover(df_part, hover_cols, title=''):
        custom_data = df_part[hover_cols].values if hover_cols else None
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_part['ChargeTime'],
            name='Laadtijd',
            nbinsx=30,
            opacity=0.8,
            marker=dict(color='#4CAF50', line=dict(color='darkgreen', width=1.5)),
            customdata=custom_data,
            hovertemplate='ChargeTime: %{x} uur<br>Aantal sessies: %{y}' +
                          ''.join([f'<br>{col}: %{{customdata[{i}]}}' for i, col in enumerate(hover_cols)]) +
                          '<extra></extra>' if hover_cols else '<extra></extra>'
        ))
        st.plotly_chart(fig, use_container_width=True)

        st.info("De Focus ligt op laadtijd, fasen en bezetting.")
        
        # --- Hover-opties ---
        hover_options = st.multiselect(
            "Kies welke gegevens je wilt zien in de hover-informatie:",
            options=['TotalEnergy', 'Efficiëntie', 'N_phases', 'GemiddeldVermogen', 'IdleRatio'],
            default=['TotalEnergy', 'Efficiëntie', 'N_phases']
        )
        plot_histogram_hover(df_filtered, hover_options, title='2022 – Laadtijd (custom hover-info)')

        # --- Boxplot per fase ---
        fasen_keuze = st.multiselect("Selecteer fasen voor de boxplot:", options=sorted(df_filtered['N_phases'].dropna().unique()), default=sorted(df_filtered['N_phases'].dropna().unique()))
        df_box = df_filtered[df_filtered['N_phases'].isin(fasen_keuze)]
        st.subheader("Laadtijd per fase")
        fig_box = px.box(
            df_box,
            x='N_phases',
            y='ChargeTime',
            color='N_phases',
            points='all',
            labels={'N_phases':'Aantal fasen','ChargeTime':'Laadtijd (uren)'},
            title='Laadtijd per fase (1, 2 of 3)'
        )
        st.plotly_chart(fig_box, use_container_width=True)

        # --- Heatmap ---
        dagen_keuze = st.multiselect(
            "Selecteer dagen voor de heatmap:",
            options=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
            default=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        )
        st.subheader("Bezettingsgraad per dag van de week en uur")
        df_filtered['Dag'] = df_filtered['start_time'].dt.day_name()
        df_filtered['Uur'] = df_filtered['start_time'].dt.hour
        df_heat = df_filtered[df_filtered['Dag'].isin(dagen_keuze)]
        heatmap_data = df_heat.pivot_table(
            index='Dag',
            columns='Uur',
            values='ChargeTime',
            aggfunc='count',
            fill_value=0
        )
        fig_heat = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Blues',
            colorbar_title='Aantal sessies',
            hovertemplate='Dag: %{y}<br>Uur: %{x}<br>Aantal sessies: %{z}<extra></extra>'
        ))
        fig_heat.update_layout(
            title='Bezettingsgraad per dag en uur',
            xaxis_title='Uur van de dag',
            yaxis_title='Dag van de week',
            template='plotly_white'
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # --- Scatter plot gefixt ---
        st.subheader("ChargeTime vs Gemiddeld Vermogen per fase")
        df_scatter = df_filtered.dropna(subset=['ChargeTime', 'GemiddeldVermogen', 'N_phases'])
        df_scatter = df_scatter[df_scatter['ChargeTime'] > 0]
        fig_scatter = px.scatter(
            df_scatter,
            x='ChargeTime',
            y='GemiddeldVermogen',
            color='N_phases',
            labels={'ChargeTime':'Laadtijd (uren)','GemiddeldVermogen':'Gemiddeld vermogen (W)'},
            title='ChargeTime vs Gemiddeld Vermogen (hover-info per sessie)',
            hover_data=['TotalEnergy','Efficiëntie','N_phases']
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

elif pagina == "Pagina 2":
    st.title("Auto-specificaties")
    st.write("Hier komen gegevens over voertuigtrend, groei EV’s en prijsontwikkeling.")

elif pagina == "Pagina 3":
    st.title("Overzichtskaart")
    st.write("Hier komt de interactieve kaart van laadpalen.")







# 2018 plots new
if jaar == '2018':
    
    # KPI tabel
    st.subheader("Resultaten data 2018")
    
    # Creëer een styled dataframe
    metrics_data = {
        'Laadpaal Metrics': [
            '🔢 Totaal aantal sessies',
            '⚡ Laadefficiëntie', 
            '⏰ Idle tijd percentage',
            '🕒 Gemiddelde laadtijd',
            '🔌 Gemiddelde aansluitingstijd',
            '📈 Lange sessies (>3u)',
            '📉 Korte sessies (<1u)',
            '🚨 Hoog idle probleem',
            '🔋 Totale energie',
            '💪 Gemiddeld vermogen'
        ],
        'Resultaten': [
            f"**{len(df_filtered):,}**",
            f"**{df_filtered['Efficiëntie'].mean():.1%}**",
            f"**{df_filtered['IdleRatio'].mean():.1%}**", 
            f"**{df_filtered['ChargeTime'].mean():.1f} uur**",
            f"**{df_filtered['ConnectedTime'].mean():.1f} uur**",
            f"**{len(df_filtered[df_filtered['Sessielengte'] == 'Lang']):,}**",
            f"**{len(df_filtered[df_filtered['Sessielengte'] == 'Kort']):,}**",
            f"**{len(df_filtered[df_filtered['IdleRatio'] > 0.5]):,}**",
            f"**{(df_filtered['TotalEnergy'].sum() / 1000):.0f} kWh**",
            f"**{df_filtered['GemiddeldVermogen'].mean():.0f} W**"
        ]
    }
    
    df_dashboard = pd.DataFrame(metrics_data)
    
    # Toon met styling
    st.markdown("""
    <style>
    .metrics-table {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.dataframe(
        df_dashboard,
        hide_index=True,
        use_container_width=True
    )
    
# Korte samenvatting
    st.info("""
    **💡 Hoofdboodschap:** 
    - **{:.1%} efficiëntie** betekent **{:.1%} van de tijd wordt verspild**
    - **{} probleemsessies** hebben meer dan 50% idle tijd
    - **{} lange sessies** hebben grote impact op beschikbaarheid
    """.format(
        df_filtered['Efficiëntie'].mean(),
        df_filtered['IdleRatio'].mean(), 
        len(df_filtered[df_filtered['IdleRatio'] > 0.5]),
        len(df_filtered[df_filtered['Sessielengte'] == 'Lang'])
    ))

    st.markdown("---")
    # plot 1 (not sure als ik deze oook wil doen)
    st.markdown('**********deze grafiek moet nog gemaakt worden tot de kleuern van de andere grafieken, of misschien haal ik deze weg')
    plot_histogram(df_filtered, stacked=True, log_y=True, title='2018 – Laadtijd vs IdleTijd (stacked, logaritmisch)')

    # 📍 SCHEIDING lijn
    st.markdown("---")

    st.subheader("Verdeling van laadtijd per sessielengte")
  
    # plot 2 (boxplot)
    fig_sessie = px.box(
        df_filtered,
        x='Sessielengte',
        y='ChargeTime',
        color='Sessielengte',
        points='all',
        labels={'ChargeTime': 'Laadtijd (uren)', 'Sessielengte': 'Categorie'},
        title='Laadtijd per sessielengte',
        log_y = True
    )

    st.plotly_chart(fig_sessie, use_container_width=True)

    # Uitleg onder de boxplot
    st.markdown("➱ **Sessielengte analyse** | **Log-schaal voor betere spreiding**")
    st.success("""Gemiddelde efficiëntie per idle-interval
    **opmerkingen:**
    - **Kort:** Grootste variatie - van minuten tot bijna 1 uur
    - **Gemiddeld:** Compacte box = voorspelbare laadtijden  
    - **Lang:** Lange staarten = occasionele zeer lange sessies
    """)

    # 📍 SCHEIDING lijn
    st.markdown("---")

        # Voeg deze code toe boven je grafieken
    visualisatie_keuze = st.radio(
        "Kies visualisatie:",
        ["Scatterplot: Relatie per laadsessie", "Balkdiagram: Gemiddelde per interval"],
        horizontal=True
    )

    # plot 3 & 4 (scatter en bar plot)
    if visualisatie_keuze == "Scatterplot: Relatie per laadsessie":
        st.subheader("Efficiëntie vs Idle-tijd")
        df_scatter = df_filtered[df_filtered['IdleTijd'] <= 24]
        fig_eff_idle = px.scatter(
            df_scatter,  # 🔹 Gebruik df_scatter hier, niet df_filtered
            x='IdleTijd',
            y='Efficiëntie',
            color='Sessielengte',
            labels={'IdleTijd': 'Idle-tijd (uren)', 'Efficiëntie': 'Efficiëntie (ratio)'},
            title='Relatie tussen Idle-tijd en efficiëntie',
            hover_data=['ChargeTime', 'ConnectedTime', 'VermogensRatio']
        )
        st.plotly_chart(fig_eff_idle, use_container_width=True)

        # Extra uitleg onder scatterplot
        st.markdown('➱ **Efficientie = Idle Tijd/Connected Time**')
        st.markdown("➱ **Elk punt = één laadsessie** | **Kleur = sessielengte**")
        st.info("""
        **Opmerking:** Hogere idle-tijd leidt tot lagere efficiëntie - auto's blijven langer aangesloten zonder te laden.
        **Oplossing:** Focus op het verminderen van idle-periodes voor betere efficiëntie.
        """)


    # Barplot geeft de gemiddelde efficiëntie per idle-interval weer.
    # Hiermee zie je duidelijk hoe efficiëntie afneemt bij langere idle-periodes en per sessielengte.
    elif visualisatie_keuze == "Balkdiagram: Gemiddelde per interval":
        st.subheader("Gemiddelde efficiëntie per idle-interval")

        # 1️⃣ Filter outliers (IdleTijd ≤ 48 uur)
        df_bar = df_filtered[df_filtered['IdleTijd'] <= 24].copy()

        # 2️⃣ Maak idle-interval bins
        df_bar['IdleBin'] = pd.cut(
            df_bar['IdleTijd'],
            bins=[0, 0.5, 1, 2, 4, 8, 24],
            include_lowest=True
        )

        # 3️⃣ Bereken gemiddelde efficiëntie per interval én sessielengte
        df_group = (
            df_bar.groupby(['IdleBin', 'Sessielengte'])['Efficiëntie']
            .mean()
            .reset_index()
        )

        # 4️⃣ Zet de bin-namen om naar strings
        df_group['IdleBin'] = df_group['IdleBin'].astype(str)

        # 5️⃣ Barplot met legenda
        fig_idle_bar = px.bar(
            df_group,
            x='IdleBin',
            y='Efficiëntie',
            color='Sessielengte',  # 💡 legenda hier!
            barmode='group',       # of 'stack' als je wilt stapelen
            title='Gemiddelde efficiëntie per idle-interval (per sessielengte)',
            labels={
                'IdleBin': 'Idle-interval (uren)',
                'Efficiëntie': 'Gemiddelde efficiëntie',
                'Sessielengte': 'Sessielengte'
            }
        )

        # 6️⃣ Layout iets mooier maken
        fig_idle_bar.update_layout(
            template='plotly_white',
            legend_title='Sessielengte',
            xaxis_title='Idle-interval (uren)',
            yaxis_title='Gemiddelde efficiëntie'
        )

        # 7️⃣ Toon grafiek
        st.plotly_chart(fig_idle_bar, use_container_width=True)

        # Extra uitleg onder balkdiagram
        st.info("""
        **Opmerking:** Efficiëntie daalt significant bij idle-tijden > 4 uur.
        **Oplossing:** Streef naar idle-tijden onder 2 uur voor optimale efficiëntie.
        """)

     # 📍 SCHEIDING lijn
    st.markdown("---")

    # plot 5 (Heatmap)
    st.subheader("IdleRatio Patronen: Dag en Uur")

    df_filtered['Dag'] = df_filtered['Started'].dt.day_name()
    df_filtered['Uur'] = df_filtered['Started'].dt.hour

    # Pivot table
    heat_data = df_filtered.pivot_table(
        index='Dag',
        columns='Uur', 
        values='IdleRatio',
        aggfunc='mean'
    ).reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])

    # Interpolatie
    heat_data = heat_data.apply(lambda row: row.interpolate(method='linear', limit_direction='both'), axis=1)

    # Custom kleurschaal
    custom_scale = [
        [0.0, 'darkblue'],
        [0.5, 'lightblue'],  
        [1.0, 'red']
    ]

    fig5 = px.imshow(
        heat_data.values,
        x=heat_data.columns,
        y=heat_data.index,
        color_continuous_scale=custom_scale,
        range_color=[0, 1],
        labels=dict(x="Uur", y="Dag", color="IdleRatio"),
        height=350
    )

    fig5.update_layout(
        title='IdleRatio Patronen per Dag en Uur van de Week',
        xaxis_title='Uur van de Dag',
        yaxis_title='Dag van de Week'
    )

    st.plotly_chart(fig5, use_container_width=True)

    # Efficiënte uitleg - 2 regels
    st.markdown("➱ **🔵 Blauw = Laag (Efficiënt)** | **🔴 Rood = Hoog (Inefficiënt)**")
    st.info("""
            **Opmerking**: tussen 0–2 u zijn enkele IdleRatio-waarden geïnterpoleerd.
            """)
    
    # 📍 SCHEIDING lijn
    st.markdown("---")

    # ployt 6 (Correlatie matrix)
    st.subheader("Correlatie Analyse")

    corr_cols = ['ChargeTime','ConnectedTime','TotalEnergy','MaxPower',
                'GemiddeldVermogen','Efficiëntie','IdleTijd','VermogensRatio','LaadEfficiëntie','IdleRatio']
    corr = df_filtered[corr_cols].corr()
    fig6 = px.imshow(
        corr,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        title='Correlatie Matrix tussen Laadpaal Variabelen',
        aspect='auto',
        height=500
    )
    st.plotly_chart(fig6, use_container_width=True)

    # Compacte highlights - direct onder matrix
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="IdleRatio ↔ Efficiëntie", 
            value="-1.00",
            delta="-1.00"
        )
        st.caption("Perfect negatief")

    with col2:
        st.metric(
            label="ConnectedTime ↔ IdleTijd", 
            value="+0.95",
            delta="+0.95"
        )
        st.caption("Zeer sterk positief")

    with col3:
        st.metric(
            label="ConnectedTime ↔ Efficiëntie", 
            value="-0.77", 
            delta="-0.77"
        )
        st.caption("Sterk negatief")

    # CSS om de kleuren aan te passen
    st.markdown("""
    <style>
    /* Rood voor negatieve delta's */
    [data-testid="stMetricDelta"] svg[data-icon="arrow-down"] {
        color: #ff4b4b !important;
    }
    [data-testid="stMetricDelta"] div[style*="color"]:has(svg[data-icon="arrow-down"]) {
        color: #ff4b4b !important;
    }

    /* Groen voor positieve delta's */
    [data-testid="stMetricDelta"] svg[data-icon="arrow-up"] {
        color: #00cc00 !important;
    }
    [data-testid="stMetricDelta"] div[style*="color"]:has(svg[data-icon="arrow-up"]) {
        color: #00cc00 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Samenvatting - compacter
    st.info("""
    **Opmerking:** Efficiëntieverlies wordt veroorzaakt door idle-tijd, niet door laadtijd.
    Focus optimalisatie op het verminderen van idle-periodes.
    """)
   











elif jaar == '2022':
    fig_energy_phase = px.box(
        df_filtered,
        x='N_phases',
        y='TotalEnergy',
        color='N_phases',
        points='all',
        labels={'N_phases':'Aantal fasen','TotalEnergy':'TotalEnergy (Wh)'},
        title='TotalEnergy per fase'
    )
    st.plotly_chart(fig_energy_phase, use_container_width=True)

    fig_power_phase = px.box(
        df_filtered,
        x='N_phases',
        y='GemiddeldVermogen',
        color='N_phases',
        points='all',
        labels={'N_phases':'Aantal fasen','GemiddeldVermogen':'Gemiddeld vermogen (W)'},
        title='GemiddeldVermogen per fase'
    )
    st.plotly_chart(fig_power_phase, use_container_width=True)

    #Heatmap dagdeel vs fase → kleuren aanpassen
    st.subheader("Heatmap dagdeel vs fase (bezetting per fase)")

    df_filtered['Uur'] = df_filtered['start_time'].dt.hour
    heatmap_phase_data = df_filtered.pivot_table(
        index='Uur',
        columns='N_phases',
        values='ChargeTime',
        aggfunc='count',
        fill_value=0
    )

    fig_phase_heat = go.Figure(data=go.Heatmap(
        z=heatmap_phase_data.values,
        x=heatmap_phase_data.columns,
        y=heatmap_phase_data.index,
        colorscale='Cividis',  # aangepaste kleuren
        colorbar_title='Aantal sessies',
        hovertemplate='Uur: %{y}<br>Fase: %{x}<br>Aantal sessies: %{z}<extra></extra>'
    ))
    fig_phase_heat.update_layout(
        title='Dagdeel vs fase (bezetting per fase)',
        xaxis_title='Aantal fasen',
        yaxis_title='Uur van de dag',
        template='plotly_white'
    )
    st.plotly_chart(fig_phase_heat, use_container_width=True)

    #Extra dimensie: welke fase wordt gebruikt per dag (3D-barchart concept)
    st.subheader("Verdeling fasen per dag")

    df_day_phase = df_filtered.groupby(['Dag','N_phases']).size().reset_index(name='Aantal')
    # Dagen goed sorteren
    dagen_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    df_day_phase['Dag'] = pd.Categorical(df_day_phase['Dag'], categories=dagen_order, ordered=True)

    fig_day_phase = px.bar(
        df_day_phase,
        x='Dag',
        y='Aantal',
        color='N_phases',
        labels={'Aantal':'Aantal sessies','Dag':'Dag van de week','N_phases':'Aantal fasen'},
        title='Verdeling fasen per dag',
        barmode='stack'
    )
    st.plotly_chart(fig_day_phase, use_container_width=True)

    # Verdelen van fasen laders - Barplot
    st.subheader("Verdeling van fasen laders (barplot)")

    fase_counts = df_filtered['N_phases'].value_counts().sort_index()

    fig_fase_bar = px.bar(
        x=fase_counts.index,
        y=fase_counts.values,
        labels={'x':'Aantal fasen','y':'Aantal sessies'},
        title='Aantal sessies per fase',
        color=fase_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_fase_bar, use_container_width=True)

    # Verdelen van fasen laders - Taartdiagram
    st.subheader("Verdeling van fasen laders (taartdiagram)")

    fig_fase_pie = px.pie(
        names=fase_counts.index,
        values=fase_counts.values,
        title='Percentage van sessies per fase',
        color=fase_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hole=0.3  # donut chart
    )
    fig_fase_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_fase_pie, use_container_width=True)

    # --- Bezettingsgraad van de laadpaal (KPI) ---
    st.subheader("Bezettingsgraad van de laadpaal")
    totaal_connected = df_filtered['ConnectedTime'].sum()  # in uren
    totaal_uren = (df_filtered['exit_time'].max() - df_filtered['start_time'].min()).total_seconds() / 3600
    bezettingsgraad = totaal_connected / totaal_uren * 100
    st.metric("Bezettingsgraad", f"{bezettingsgraad:.2f}%")

    # --- Heatmap: totaal aantal sessies per dag en uur ---
    st.subheader("Bezettingsgraad per dag en uur")
    df_filtered['Dag'] = df_filtered['start_time'].dt.day_name()
    df_filtered['Uur'] = df_filtered['start_time'].dt.hour

    heatmap_data = df_filtered.pivot_table(
        index='Dag',
        columns='Uur',
        values='ChargeTime',
        aggfunc='count',
        fill_value=0
    )
    weekdagen = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    heatmap_data = heatmap_data.reindex(weekdagen)

    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='Cividis',
        colorbar_title='Aantal sessies',
        hovertemplate='Dag: %{y}<br>Uur: %{x}<br>Aantal sessies: %{z}<extra></extra>'
    ))
    fig_heat.update_layout(
        title='Bezettingsgraad per dag en uur',
        xaxis_title='Uur van de dag',
        yaxis_title='Dag van de week',
        template='plotly_white'
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # mijn gedeelte voor plots toevoegen voor 2018
