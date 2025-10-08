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
            marker=dict(color="#0DBE2D", line=dict(color='green', width=1.5)),
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
                marker=dict(color="#EE530C", line=dict(color='red', width=1.5)),
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
    def plot_histogram_hover(df_part, hover_cols, title='x'):
        custom_data = df_part[hover_cols].values if hover_cols else None
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_part['ChargeTime'],
            name='Laadtijd',
            nbinsx=30,
            opacity=0.8,
            marker=dict(color="blue", line=dict(color='white', width=1.5)),
            customdata=custom_data,
            hovertemplate='ChargeTime: %{x} uur<br>Aantal sessies: %{y}' +
                          ''.join([f'<br>{col}: %{{customdata[{i}]}}' for i, col in enumerate(hover_cols)]) +
                          '<extra></extra>' if hover_cols else '<extra></extra>'
        ))
        st.plotly_chart(fig, use_container_width=True)

    # --- Plots per jaar ---
    if jaar == "2018":
        plot_histogram(df_filtered, stacked=True, log_y=True, title='2018 – Laadtijd vs IdleTijd (stacked, logaritmisch)')

    elif jaar == "2022":
        st.info("De Focus ligt op laadtijd, fasen en bezetting.")

            # --- Bezettingsgraad van de laadpaal (KPI) ---
        st.subheader("Bezettingsgraad van de laadpaal")
        totaal_connected = df_filtered['ConnectedTime'].sum()  # in uren
        totaal_uren = (df_filtered['exit_time'].max() - df_filtered['start_time'].min()).total_seconds() / 3600
        bezettingsgraad = totaal_connected / totaal_uren * 100
        st.metric("Bezettingsgraad", f"{bezettingsgraad:.2f}%")

                # --- Voorbereidingen: zet datetime kolommen om ---
        df_2022['start_time'] = pd.to_datetime(df_2022['start_time'])
        df_2022['exit_time'] = pd.to_datetime(df_2022['exit_time'])
        df_2022['start_hour'] = df_2022['start_time'].dt.hour
        df_2022['weekday'] = df_2022['start_time'].dt.day_name()

                # --- Keuzemenu voor categorieën ---
        categorie = st.selectbox(
            "Kies KPI-categorie:",
            options=['Gebruik', 'Efficiëntie']
        )

        st.subheader("Totale output")
        totaal_energie_mwh = df_2022['TotalEnergy'].sum() / 1_000_000
        st.metric("Totaal geleverde energie", f"{totaal_energie_mwh:.2f} MWh")

        st.subheader(f"KPI's: {categorie}")

        # --- Bereken en toon KPI's per categorie ---
        if categorie == 'Gebruik':
            totaal_sessies = len(df_2022)
            gem_aangesloten = df_2022['ChargeTime'].mean()
            gem_energie = df_2022['TotalEnergy'].mean() / 1000  # kWh

            # Gebruik st.columns om KPI's naast elkaar te zetten
            col1, col2, col3 = st.columns(3)
            col1.metric("Aantal sessies", totaal_sessies)
            col2.metric("Gemiddelde tijd aangesloten aan de laadpaal", f"{gem_aangesloten:.2f} uur")
            col3.metric("Gemiddelde energie per sessie", f"{gem_energie:.2f} kWh")

        elif categorie == 'Efficiëntie':
            gem_vermogen = df_2022['GemiddeldVermogen'].mean() / 1000
            gem_max_power = df_2022['MaxPower'].mean() / 1000

            col1, col2 = st.columns(2)
            col1.metric("Gemiddeld vermogen", f"{gem_vermogen:.2f} kW")
            col2.metric("Gemiddeld maximaal vermogen", f"{gem_max_power:.2f} kW")

            # --- Extra: Gemiddeld vermogen per fase ---
            vermogen_per_fase = df_2022.groupby('N_phases')['GemiddeldVermogen'].mean() / 1000
            energie_per_fase = df_2022.groupby('N_phases')['TotalEnergy'].mean() / 1000  # kWh

            col1, col2 = st.columns(2)
            with col1:
                st.write("Gemiddeld vermogen per fase (kW):")
                st.dataframe(vermogen_per_fase.round(2))
            with col2:
                st.write("Gemiddelde energie per sessie per fase (kWh):")
                st.dataframe(energie_per_fase.round(2))
        
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

if jaar == '2018':
    pass

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
        colorscale='Plasma',  # aangepaste kleuren
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
        color_discrete_sequence=['#cce5ff', '#99ccff', '#66b2ff'],
        hole=0.3  # donut chart
    )
    fig_fase_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_fase_pie, use_container_width=True)


    #diepgaandere analyse
        # Maak dagdeel
    def get_daypart(hour):
        if 0 <= hour < 6:
            return 'Nacht'
        elif 6 <= hour < 12:
            return 'Ochtend'
        elif 12 <= hour < 18:
            return 'Middag'
        else:
            return 'Avond'

    df_2022['dagdeel'] = df_2022['start_hour'].apply(get_daypart)

    # --- Streamlit layout ---
    st.title("2022 Laadpaal Data - Relaties & KPI Analyses")

    # ------------------------------------------
    st.subheader("1️⃣ Relaties & correlaties")

    # ChargeTime vs TotalEnergy
    st.write("**ChargeTime ↔ TotalEnergy**")
    fig1 = px.scatter(df_2022, x='ChargeTime', y='TotalEnergy',
                    color='N_phases',
                    labels={'ChargeTime':'Laadtijd (uur)', 'TotalEnergy':'Geleverde energie (kWh)'},
                    hover_data=['GemiddeldVermogen'])
    st.plotly_chart(fig1)


    # Dagdeel/uur ↔ bezetting / fasegebruik
    st.write("**Dagdeel / Uur ↔ bezetting**")
    bezetting_per_uur = df_2022.groupby(['start_hour','N_phases']).size().reset_index(name='aantal_sessies')
    fig6 = px.bar(bezetting_per_uur, x='start_hour', y='aantal_sessies', color='N_phases',
                labels={'start_hour':'Uur van de dag', 'aantal_sessies':'Aantal sessies', 'N_phases':'Fase'})
    st.plotly_chart(fig6)

    # ------------------------------------------
    st.subheader("2️⃣ KPI-afgeleide analyses")

    # VermogensRatio ↔ TotalEnergy
    st.write("**VermogensRatio ↔ TotalEnergy**")
    fig10 = px.scatter(df_2022, x='VermogensRatio', y='TotalEnergy', color='N_phases',
                    labels={'VermogensRatio':'VermogensRatio','TotalEnergy':'Geleverde energie (kWh)'})
    st.plotly_chart(fig10)

    # Dagdeel / start_hour als categorie
    st.write("**Gemiddelde sessies per dagdeel**")
    sessie_per_dagdeel = df_2022.groupby('dagdeel')['ChargeTime'].mean().reset_index()
    fig11 = px.bar(sessie_per_dagdeel, x='dagdeel', y='ChargeTime',
                labels={'dagdeel':'Dagdeel','ChargeTime':'Gemiddelde laadtijd (uur)'})
    st.plotly_chart(fig11)

    st.write("**Gemiddeld vermogen per fase per dagdeel**")
    vermogen_per_dagdeel_fase = df_2022.groupby(['dagdeel','N_phases'])['GemiddeldVermogen'].mean().reset_index()
    fig12 = px.bar(vermogen_per_dagdeel_fase, x='dagdeel', y='GemiddeldVermogen', color='N_phases',
                labels={'dagdeel':'Dagdeel','GemiddeldVermogen':'Gemiddeld vermogen (kW)','N_phases':'Fase'})
    st.plotly_chart(fig12)

    # #2 nieuw
    import plotly.figure_factory as ff
    import numpy as np 
        # ------------------------------------------
    st.subheader("Correlatiematrix")

    # Kies numerieke kolommen voor correlatie
    num_cols = ['ChargeTime','TotalEnergy','GemiddeldVermogen','MaxPower','VermogensRatio','LaadEfficiëntie']

    # Bereken correlatie
    corr_matrix = df_2022[num_cols].corr()

  # Custom kleuren (genormaliseerd tussen 0 en 1)
    custom_colorscale = [
        [0.0, 'green'],    # laagste waarde
        [0.3, 'yellow'],   # midden laag
        [0.6, 'orange'],   # midden hoog
        [1.0, 'blue']      # hoogste waarde
    ]

    # Maak heatmap met Plotly
    fig_corr = ff.create_annotated_heatmap(
        z=corr_matrix.values,
        x=list(corr_matrix.columns),
        y=list(corr_matrix.columns),
        annotation_text=np.round(corr_matrix.values, 2),
        colorscale=custom_colorscale,  # correcte variabele
        showscale=True
    )

    st.plotly_chart(fig_corr, use_container_width=True)


    #Voorspelling
    import streamlit as st
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    import plotly.express as px

    # --- Titel ---
    st.title("🚗 Laadpaal Beschikbaarheid Voorspelling 2022")
    st.markdown("""
    Deze app laat zien hoe goed we kunnen voorspellen of een laadpaal beschikbaar is op een bepaald uur.
    We gebruiken historische data van 2022 en een Random Forest model om dit te doen.
    """)

    # --- Laad data ---
    @st.cache_data
    def load_data():
        df = pd.read_pickle('charging_data.pkl')  # laad 2022 data
        df['start_time'] = pd.to_datetime(df['start_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        return df

    df_2022 = load_data()

    # --- Feature engineering ---
    df_model = df_2022.copy()
    df_model['start_hour_floor'] = df_model['start_time'].dt.floor('H')
    df_model['end_hour_floor'] = df_model['exit_time'].dt.floor('H')

    # Maak uurdataframe voor beschikbaarheid
    hours_range = pd.date_range(start=df_model['start_hour_floor'].min(),
                                end=df_model['end_hour_floor'].max(), freq='H')
    availability = pd.DataFrame({'hour': hours_range})
    availability['aantal_bezet'] = 0

    # Vul bezetting
    for idx, row in df_model.iterrows():
        mask = (availability['hour'] >= row['start_hour_floor']) & (availability['hour'] < row['end_hour_floor'])
        availability.loc[mask, 'aantal_bezet'] += 1

    # Target: 1 = beschikbaar, 0 = bezet
    availability['beschikbaar'] = np.where(availability['aantal_bezet'] == 0, 1, 0)

    # Feature engineering
    availability['hour_of_day'] = availability['hour'].dt.hour
    availability['weekday'] = availability['hour'].dt.weekday  # 0=maandag
    availability['dagdeel'] = pd.cut(availability['hour_of_day'],
                                    bins=[0,6,12,18,24],
                                    labels=['Nacht','Ochtend','Middag','Avond'],
                                    right=False)

    # Rolling features: historisch aantal bezet
    availability['bezet_1u_lag'] = availability['aantal_bezet'].shift(1).fillna(0)
    availability['bezet_2u_lag'] = availability['aantal_bezet'].shift(2).fillna(0)

    # --- Features voor het model (vast) ---
    features = ['hour_of_day', 'weekday', 'bezet_1u_lag', 'bezet_2u_lag']


    X = availability[features]
    y = availability['beschikbaar']

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, shuffle=False)

    # --- Random Forest ---
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # --- Evaluatie ---
    st.subheader("📊 Model Evaluatie")
    st.markdown("""
    Hieronder zie je hoe goed het model heeft gepresteerd:

    - **Confusion Matrix**: laat zien hoeveel keer het model correct voorspelde dat de laadpaal beschikbaar of bezet was.
    - **Classification Report**: toont metrics zoals precision, recall en f1-score.
    """)

    # Bereken confusion matrix en classification report
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()  # true negatives, false positives, false negatives, true positives

    st.write("Confusion Matrix (Rijen = echte waarde, Kolommen = voorspelling):")
    st.text(cm)

    st.write("Classification Report:")
    st.text(classification_report(y_test, y_pred))

    # Dynamische uitleg
    st.subheader("📖 Uitleg Confusion Matrix")
    st.markdown(f"""
    **Dit kun je als volgt lezen:**

    |                  | Voorspeld 0 (bezet) | Voorspeld 1 (beschikbaar) |
    |------------------|--------------------|---------------------------|
    | **Werkelijk 0**  | {tn}               | {fp}                        |
    | **Werkelijk 1**  | {fn}               | {tp}                        |

    - **{tn}**: Het model voorspelde correct “bezet” voor {tn} uren. ✅  
    - **{tp}**: Het model voorspelde correct “beschikbaar” voor {tp} uren. ✅  
    - **{fp}**: Het model dacht dat het beschikbaar was terwijl het eigenlijk bezet was. ❌ (False Positives)  
    - **{fn}**: Het model dacht dat het bezet was terwijl het eigenlijk beschikbaar was. ❌ (False Negatives)  
    """)

    # --- Gemiddelde voorspelling per dagdeel ---
    st.subheader("🌅 Gemiddelde voorspelling per dagdeel")
    st.markdown("""
    Hier zie je hoe vaak het model voorspelt dat de laadpaal beschikbaar is in elk dagdeel:

    - **Nacht, Ochtend, Middag, Avond**
    - De hoogte van de balk geeft het gemiddelde percentage beschikbaarheid.
    """)

    df_viz = X_test.copy()
    df_viz['Voorspeld'] = y_pred
    df_viz['dagdeel'] = availability.loc[X_test.index, 'dagdeel']

    gem_voorspelling = df_viz.groupby('dagdeel')['Voorspeld'].mean().reset_index()

    fig_dagdeel = px.bar(
        gem_voorspelling,
        x='dagdeel',
        y='Voorspeld',
        labels={'dagdeel':'Dagdeel','Voorspeld':'Gemiddelde voorspelling'},
        color='Voorspeld',
        color_continuous_scale='Viridis',
        text=gem_voorspelling['Voorspeld'].round(2)
    )
    st.plotly_chart(fig_dagdeel)

    # --- Voorspelling voor een specifiek tijdstip ---
    st.subheader("🔮 Voorspelling voor een specifiek uur")
    st.markdown("Selecteer een dag en tijd en kijk of de laadpaal waarschijnlijk beschikbaar is.")

    # Input: datum en tijd apart
    selected_date = st.date_input(
        "Kies een datum",
        value=df_2022['start_time'].min().date()
    )

    selected_time = st.time_input(
        "Kies een tijd",
        value=pd.to_datetime(df_2022['start_time'].min()).time()
    )

    # Combineer tot datetime en rond af op het uur
    selected_datetime = pd.to_datetime(f"{selected_date} {selected_time}").floor('H')

    # Feature engineering voor het gekozen tijdstip
    hour_of_day = selected_datetime.hour
    weekday = selected_datetime.weekday()

    # Haal lag features op, gebruik 0 als er geen data is
    bezet_1u_lag = availability.loc[availability['hour'] == selected_datetime - pd.Timedelta(hours=1), 'aantal_bezet']
    bezet_1u_lag = int(bezet_1u_lag.values[0]) if not bezet_1u_lag.empty else 0

    bezet_2u_lag = availability.loc[availability['hour'] == selected_datetime - pd.Timedelta(hours=2), 'aantal_bezet']
    bezet_2u_lag = int(bezet_2u_lag.values[0]) if not bezet_2u_lag.empty else 0

    # Maak dataframe voor predictie
    input_df = pd.DataFrame([{
        'hour_of_day': hour_of_day,
        'weekday': weekday,
        'bezet_1u_lag': bezet_1u_lag,
        'bezet_2u_lag': bezet_2u_lag
    }])

    # Alleen gebruik de geselecteerde features
    input_df = input_df[features]

    # Voorspelling + zekerheid
    pred = model.predict(input_df)[0]
    pred_proba = model.predict_proba(input_df)[0][pred] * 100  # zekerheid in %

    status = "Beschikbaar ✅" if pred == 1 else "Bezet ❌"

    st.markdown(f"**Voorspelling voor {selected_datetime}:** {status}  \n**Zekerheid:** {pred_proba:.1f}%")
