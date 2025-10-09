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
    jaar = st.sidebar.selectbox("Kies dataset of voorspelling:", ["2018", "2022", "Voorspelling"])

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
    toon_uitleg = st.checkbox("Laat uitleg van de feature engineering zien", value=True)
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
            marker=dict(color="#00FF2F", line=dict(color='white', width=1.5)),
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
                marker=dict(color="#FF0000", line=dict(color='white', width=1.5)),
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
        st.info("De Focus ligt op laadtijd, fasen en bezetting van de laadpaal. De data gaat over 1 laadpaal met dus 2 aansluitingen. Er is verder geen idle time beschikbaar waardoor er wel missende data is. ")

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

        # Dagdeel/uur ↔ bezetting / fasegebruik
        st.write("**Bezetting: dagdeel / uur**")

        # Toggle toevoegen
        weergave_optie = st.radio(
            "Kies weergave:",
            options=['Per fase', 'Totaal'],
            horizontal=True
        )

        # Data voorbereiden
        bezetting_per_uur = df_2022.groupby(['start_hour','N_phases']).size().reset_index(name='aantal_sessies')
        bezetting_per_uur['N_phases'] = bezetting_per_uur['N_phases'].astype(int).astype(str)

        # Conditie op basis van keuze
        if weergave_optie == 'Per fase':
            fig6 = px.bar(
                bezetting_per_uur,
                x='start_hour',
                y='aantal_sessies',
                color='N_phases',
                color_discrete_map={'1': 'blue', '2': 'green', '3': 'red'},
                labels={'start_hour': 'Uur van de dag', 'aantal_sessies': 'Aantal sessies', 'N_phases': 'Fase'},
                title='Aantal sessies per uur (per fase)'
            )
            st.markdown("""
                Deze grafiek hieronder toont het **totaal aantal laadsessies per uur van de dag**.
                De pieken laten zien op welke momenten de laadpalen het meest gebruikt worden,
                per fasen laders, zo is het verschil in 1, 2 of 3 fasen laders te zien.
                """)
        else:
            # Groeperen zonder onderscheid in fasen
            totaal_per_uur = bezetting_per_uur.groupby('start_hour')['aantal_sessies'].sum().reset_index()
            fig6 = px.bar(
                totaal_per_uur,
                x='start_hour',
                y='aantal_sessies',
                labels={'start_hour': 'Uur van de dag', 'aantal_sessies': 'Totaal aantal sessies'},
                title='Totaal aantal sessies per uur',
                color_discrete_sequence=['#4C72B0']  # één kleur (blauw)
            )
            st.markdown("""
                Deze grafiek hieronder toont het **totaal aantal laadsessies per uur van de dag**.
                De pieken laten zien op welke momenten de laadpalen het meest gebruikt worden,
                onafhankelijk van het aantal fasen van de laders.
                """)

        # Layout en tonen
        fig6.update_layout(
            xaxis=dict(dtick=1),
            template='plotly_white'
        )
        st.plotly_chart(fig6, use_container_width=True)

        # --- Boxplot per fase ---
        fasen_keuze = st.multiselect(
            "Selecteer fasen voor de boxplot:", 
            options=sorted(df_filtered['N_phases'].dropna().unique()), 
            default=sorted(df_filtered['N_phases'].dropna().unique())
        )

        # Filter op geselecteerde fasen
        df_box = df_filtered[df_filtered['N_phases'].isin(fasen_keuze)]

        st.subheader("Laadtijd per fase")
        st.markdown("""
            Deze grafiek laat zien hoe lang auto’s gemiddeld aangesloten zijn op de laadpalen, afhankelijk van het aantal fasen (1, 2 of 3).  

            - Zo kun je snel zien dat fase 1 inderdaad minder snel laad dan fase 3, of langer nodig heeft om een auto volledig op te laden.  
            - De spreiding van de data laat zien dat sommige sessies korter of langer duren dan gemiddeld.  

            Deze visualisatie helpt bij het **begrijpen van gebruikspatronen**.
            """)

        # Zorg dat N_phases als string wordt behandeld
        df_box['N_phases'] = df_box['N_phases'].astype(int).astype(str)

        # Boxplot met vaste kleuren
        fig_box = px.box(
            df_box,
            x='N_phases',
            y='ChargeTime',
            color='N_phases',
            points='all',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
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
        st.markdown("""
            Deze heatmap laat zien hoe druk de laadpalen zijn, verdeeld over **dagen van de week** en **uren van de dag**.  

            - Donkere kleuren geven **hogere bezetting** aan, lichte kleuren **lagere bezetting**.  
            - Zo kun je snel zien **op welke dagen en tijden de laadpalen het drukst zijn**.  

            Deze visualisatie geeft een overzicht van het gebruikspatroon van de laadpaal, zodat er eenvoudig trends en piekmomenten kunnen worden herkent.
            """)
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
        st.markdown("""
            Deze grafiek toont het verband tussen de **laadtijd** en het **gemiddeld vermogen** van elke sessie, per aantal fasen (1, 2 of 3).  

            - Hoer os te zien   **hoe het aantal fasen invloed heeft op de laadtijd en het vermogen**.  
            - Patronen of clusters in de grafiek geven inzicht in **efficiënt gebruik van de laders**.  

            Deze visualisatie helpt bij het **begrijpen van het opladen per fase** en het identificeren van sessies die sneller of langzamer laden dan gemiddeld.
            """)

        df_scatter = df_filtered.dropna(subset=['ChargeTime', 'GemiddeldVermogen', 'N_phases'])
        df_scatter = df_scatter[df_scatter['ChargeTime'] > 0]

        # Zorg dat N_phases als categorie wordt behandeld
        df_scatter['N_phases'] = df_scatter['N_phases'].astype(int).astype(str)  # '1', '2', '3'

        # Scatter plot met vaste kleuren
        fig_scatter = px.scatter(
            df_scatter,
            x='ChargeTime',
            y='GemiddeldVermogen',
            color='N_phases',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
            labels={'ChargeTime':'Laadtijd (uren)','GemiddeldVermogen':'Gemiddeld vermogen (W)'},
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
    # Zorg dat N_phases als categorie wordt behandeld
    df_filtered['N_phases'] = df_filtered['N_phases'].astype(int).astype(str)  # '1', '2', '3'

    # --- Kolommen aanmaken voor de twee boxplots ---
    col1, col2 = st.columns(2)

    # --- Eerste kolom: TotalEnergy per fase ---
    with col1:
        st.markdown("""
        ### Geleverde energie per fase
        Deze boxplot toont de **verspreiding van de geleverde energie** per sessie, afhankelijk van het **aantal fasen** (1, 2 of 3).  

        Deze visualisatie helpt bij het **vergelijkend inzicht in het energiegebruik per type lader** en het herkennen van eventuele uitzonderingen.
        """)
        fig_energy_phase = px.box(
            df_filtered,
            x='N_phases',
            y='TotalEnergy',
            color='N_phases',
            points='all',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
            labels={'N_phases':'Aantal fasen','TotalEnergy':'TotalEnergy (Wh)'},
        )
        st.plotly_chart(fig_energy_phase, use_container_width=True)

    # --- Tweede kolom: GemiddeldVermogen per fase ---
    with col2:
        st.markdown("""
        ### Gemiddeld vermogen per fase
        Deze boxplot toont het **gemiddeld vermogen per sessie** afhankelijk van het **aantal fasen** (1, 2 of 3).  

        - Hier is te zien **dat fasen 3 doorgaans meer vermogen levert**.  

        Deze visualisatie helpt bij het **vergelijkend inzicht in prestaties van verschillende fasen** en het identificeren van uitzonderingen.
        """)
        fig_power_phase = px.box(
            df_filtered,
            x='N_phases',
            y='GemiddeldVermogen',
            color='N_phases',
            points='all',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
            labels={'N_phases':'Aantal fasen','GemiddeldVermogen':'Gemiddeld vermogen (W)'},
        )
        st.plotly_chart(fig_power_phase, use_container_width=True)

    #Heatmap dagdeel vs fase → kleuren aanpassen
    st.markdown("""
        ### Bezetting per uur van de dag en fase
        Deze heatmap laat zien hoe druk de laadpalen zijn, verdeeld over **de uren** **en aantal fasen (1, 2 of 3)**.  

        Deze visualisatie geeft inzicht in het **gebruikspatroon** van de laders per fase gedurende de dag en zo is hier te zien dat het vooral rond **de ochtend** en **halverwege de middag** erg druk is.
        """)

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

    # --- Markdown uitleg voor de sectie ---
    st.markdown("""
    ### Aantal sessies per fase
    Hieronder zie je zowel **het aantal sessies per fase** als **het percentage van sessies per fase**.  
    - De barplot toont absolute aantallen.  
    - De taartdiagram toont het relatieve aandeel van elke fase.  
    - **Te zien is dat fase 3 het meest gebruikt wordt, gevolgd door fase 1 en dan sterk in de minderheid fase 2**.
    """)

    # 1️⃣ eerst value counts maken
    fase_counts = df_filtered['N_phases'].value_counts().sort_index()
    fase_counts.index = fase_counts.index.astype(int).astype(str)  # strings voor categorische x-as

    # 2️⃣ Kolommen aanmaken
    col1, col2 = st.columns(2)

    # --- Barplot in de eerste kolom ---
    with col1:
        fig_fase_bar = px.bar(
            x=fase_counts.index,  # categorisch via strings
            y=fase_counts.values,
            labels={'x':'Aantal fasen','y':'Aantal sessies'},
            title='Aantal sessies per fase',
            color=fase_counts.index,
            color_discrete_map={'1':'blue','2':'green','3':'red'}
        )
        fig_fase_bar.update_xaxes(type='category')  # forceert categorische x-as
        st.plotly_chart(fig_fase_bar, use_container_width=True)

    # --- Pie chart in de tweede kolom ---
    with col2:
        fig_fase_pie = px.pie(
            names=fase_counts.index,
            values=fase_counts.values,
            title='Percentage van sessies per fase',
            color=fase_counts.index,
            color_discrete_map={'1':'blue','2':'green','3':'red'},
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

    # --- Kolommen aanmaken voor de twee plots ---
    col1, col2 = st.columns(2)

    # --- Eerste kolom: Laadtijd vs Geleverde Energie ---
    with col1:
        st.markdown("""
        ### Laadtijd vs Geleverde Energie (dot plot)
        Deze dot plot toont de relatie tussen **laadtijd per sessie** en **geleverde energie**.  

        - De x-as toont de **laadtijd (uren)**, de y-as het **totaal geleverde energie (kWh)**.  
        - Hier is te zien hoe **laadtijd en geleverde energie samenhangen** en hoe verschillende fasen invloed op hebben op de energie die zij kunnen leveren. 

        Dit helpt bij het **analyseren van efficiëntie en gebruikspatronen**.
        """)
        df_2022['N_phases'] = df_2022['N_phases'].astype(int).astype(str)
        fig1 = px.scatter(
            df_2022,
            x='ChargeTime',
            y='TotalEnergy',
            color='N_phases',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
            labels={'ChargeTime':'Laadtijd (uur)', 'TotalEnergy':'Geleverde energie (kWh)'},
            hover_data=['GemiddeldVermogen']
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Tweede kolom: VermogensRatio vs Geleverde Energie ---
    with col2:
        st.markdown("""
        ### VermogensRatio vs Geleverde Energie
        Deze scatter plot toont de relatie tussen de **VermogensRatio** en de **geleverde energie per sessie**.  

        - De x-as toont de **VermogensRatio**, een maat voor efficiëntie.  
        - De y-as toont de **geleverde energie (kWh)**.  
        - Hier is te zien hoe **efficiëntie samenhangt met energieafgifte**.  

        Dit helpt bij het **begrijpen** van het **effect van vermogensefficiëntie** op de **energieoutput**.
        """)
        df_2022['N_phases'] = df_2022['N_phases'].astype(int).astype(str)
        fig10 = px.scatter(
            df_2022,
            x='VermogensRatio',
            y='TotalEnergy',
            color='N_phases',
            color_discrete_map={'1':'blue','2':'green','3':'red'},
            labels={'VermogensRatio':'VermogensRatio','TotalEnergy':'Geleverde energie (kWh)'}
        )
        st.plotly_chart(fig10, use_container_width=True)

    # #2 nieuw
    import plotly.figure_factory as ff
    import numpy as np 
        # ------------------------------------------
    st.markdown("""
        ### Correlatiematrix
        Deze heatmap toont de **correlatie tussen alle numerieke variabelen** in de dataset, **evenals** bij **de dataset uit 2018**.  

        - Waarden dicht bij **+1** duiden op een sterke positieve correlatie (stijgt de ene variabele, dan stijgt de andere).  
        - Waarden rond **0** geven weinig tot geen lineaire relatie aan.  
        - Een correlatie van **-0.2** duidt op een **zwakke negatieve relatie**: als de ene variabele iets toeneemt, neemt de andere iets af, maar het effect is klein.


        Deze visualisatie helpt bij het **identificeren van sterke relaties tussen variabelen**, wat nuttig is voor **analyse en het voorspellingsmodel**.
        """)

    # Kies numerieke kolommen voor correlatie
    num_cols = ['ChargeTime','TotalEnergy','GemiddeldVermogen','MaxPower','VermogensRatio','LaadEfficiëntie']

    # Bereken correlatie
    corr_matrix = df_2022[num_cols].corr()

  # Custom kleuren (genormaliseerd tussen 0 en 1)
    custom_colorscale = [
        [0.0, 'red'],    # laagste waarde
        [0.3, 'orange'],   # midden laag
        [0.6, 'yellow'],   # midden hoog
        [1.0, 'green']      # hoogste waarde
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

elif jaar == "Voorspelling":
   st.header("🔮 Voorspelling laadpalen")

if jaar == "Voorspelling":
    # --- Uitleg toggle ---
    toon_uitleg = st.toggle("Toon uitleg over het model")
    if toon_uitleg:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### 🌲 Wat is een Random Forest?
            Een **Random Forest** is een machine learning model dat bestaat uit **meerdere beslisbomen** (*decision trees*).  
            Elke boom leert een iets ander patroon uit de data, bijvoorbeeld het verband tussen:
            - het dagdeel (ochtend, middag, avond)
            - het aantal fasen
            - de totale laadtijd
            - en de bezettingsgraad van de laadpalen.

            Dit zorgt ervoor dat het model robuuster wordt — één enkele boom kan fouten maken,  
            maar het gemiddelde van veel bomen levert een stabieler resultaat op.
            """)

        with col2:
            st.markdown("""
            ### ⚙️ Hoe werkt het model?
            1. De trainingsdata wordt **meerdere keren willekeurig opgesplitst**.
            2. Voor elk deel wordt een **beslisboom** getraind, die zijn eigen voorspelling leert maken.
            3. Bij het voorspellen combineren we alle bomen:
            - Voor **regressie** (bijv. laadtijd): het gemiddelde van alle bomen.
            - Voor **classificatie** (bijv. drukte): de meest voorkomende uitkomst.

            ### 💡 Waarom Random Forest?
            - Werkt goed bij **niet-lineaire patronen**.
            - Vereist **weinig afstemming**.
            - Blijft **uitlegbaar** – we kunnen zien welke variabelen de grootste invloed hebben.

            Zo kan het model voorspellen **hoe druk** het wordt en **hoe lang** laadmomenten duren,  
            op basis van historische data en kenmerken zoals tijdstip en aantal fasen.
            """)
   
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
    model = RandomForestClassifier(n_estimators=100, random_state=48)
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

# 2018 plots new
if jaar == '2018':
    
    # KPI tabel
    st.subheader("Resultaten data 2018")
    
    metrics_data = {
        'Laadpaal Metrics': [
            'Totaal aantal sessies',
            'Laadefficiëntie', 
            'Idle tijd percentage',
            'Gemiddelde laadtijd',
            'Gemiddelde aansluitingstijd',
            'Lange sessies (>3u)',
            'Korte sessies (<1u)',
            'Hoog idle probleem',
            'Totale energie',
            'Gemiddeld vermogen'
        ],
        'Resultaten': [
            f"{len(df_filtered):,}",
            f"{df_filtered['Efficiëntie'].mean():.1%}",
            f"{df_filtered['IdleRatio'].mean():.1%}", 
            f"{df_filtered['ChargeTime'].mean():.1f} uur",
            f"{df_filtered['ConnectedTime'].mean():.1f} uur",
            f"{len(df_filtered[df_filtered['Sessielengte'] == 'Lang']):,}",
            f"{len(df_filtered[df_filtered['Sessielengte'] == 'Kort']):,}",
            f"{len(df_filtered[df_filtered['IdleRatio'] > 0.5]):,}",
            f"{(df_filtered['TotalEnergy'].sum() / 1000):.0f} kWh",
            f"{df_filtered['GemiddeldVermogen'].mean():.0f} W"
        ]
    }
    
    df_dashboard = pd.DataFrame(metrics_data)

    # Styling
    st.markdown("""
    <style>
    .metrics-table {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.dataframe(df_dashboard, hide_index=True, use_container_width=True)
    
    # Samenvatting
    st.info("""
    **Conclussie:** 
    - **In 2018 was er {:.1%} efficiëntie**, dat betekent **{:.1%} van de contected time wordt niet nuttig gebruikt**
    - **{} van de 10.187** hebben meer dan **50% idle time**
    - **Dit heeft grote imact op de beschikbaarheid**
    """.format(
        df_filtered['Efficiëntie'].mean(),
        df_filtered['IdleRatio'].mean(), 
        len(df_filtered[df_filtered['IdleRatio'] > 0.5]),
        len(df_filtered[df_filtered['Sessielengte'] == 'Lang'])
    ))

    st.markdown("---")

    def plot_histogram(df, stacked=False, log_y=False, title=None, key=None):
        fig = px.histogram(
            df,
            x="Laadtijd",
            y="IdleTijd",
            barmode='stack' if stacked else 'group',
            log_y=log_y,
            title=title
    )


    st.subheader("Verdeling van laadtijd per sessielengte")

    # Plot 2
    fig_sessie = px.box(
        df_filtered,
        x='Sessielengte',
        y='ChargeTime',
        color='Sessielengte',
        points='all',
        labels={'ChargeTime': 'Laadtijd (uren)', 'Sessielengte': 'Categorie'},
        log_y=True
    )

    st.plotly_chart(fig_sessie, use_container_width=True, key='boxplot_sessie_2018')

    st.markdown("Laadtijd in uren is op logaritimsche schaal")

    st.markdown("---")

    # Keuzemenu
    visualisatie_keuze = st.radio(
        "Kies visualisatie:",
        ["Scatterplot: Relatie per laadsessie", "Histogram: Gemiddelde per interval"],
        horizontal=True
    )

    # Plot 3 – Scatterplot
    if visualisatie_keuze == "Scatterplot: Relatie per laadsessie":
        st.subheader("Efficiëntie vs Idle-tijd")
        df_scatter = df_filtered[df_filtered['IdleTijd'] <= 24]
        fig_eff_idle = px.scatter(
            df_scatter,
            x='IdleTijd',
            y='Efficiëntie',
            color='Sessielengte',
            labels={'IdleTijd': 'Idle-tijd (uren)', 'Efficiëntie': 'Efficiëntie (ratio)'},
            title='Relatie tussen Idle-tijd en efficiëntie',
            hover_data=['ChargeTime', 'ConnectedTime', 'VermogensRatio']
        )
        st.plotly_chart(fig_eff_idle, use_container_width=True, key='scatter_eff_idle_2018')

        st.info("""
        Een hogere idle-tijd leidt tot lagere efficiëntie - auto's blijven langer aangesloten zonder te laden. Dit verlies in efficiëntie is goed te zien in de scatterplot.
        """)

    # Plot 4 – Barplot
    elif visualisatie_keuze == "Balkdiagram: Gemiddelde per interval":
        st.subheader("Gemiddelde efficiëntie per idle-interval")
        df_bar = df_filtered[df_filtered['IdleTijd'] <= 24].copy()
        df_bar['IdleBin'] = pd.cut(df_bar['IdleTijd'], bins=[0, 0.5, 1, 2, 4, 8, 24], include_lowest=True)
        df_group = df_bar.groupby(['IdleBin', 'Sessielengte'])['Efficiëntie'].mean().reset_index()
        df_group['IdleBin'] = df_group['IdleBin'].astype(str)

        fig_idle_bar = px.bar(
            df_group,
            x='IdleBin',
            y='Efficiëntie',
            color='Sessielengte',
            barmode='group',
            title='Gemiddelde efficiëntie per idle-interval (per sessielengte)',
            labels={
                'IdleBin': 'Idle-interval (uren)',
                'Efficiëntie': 'Gemiddelde efficiëntie',
                'Sessielengte': 'Sessielengte'
            }
        )

        fig_idle_bar.update_layout(
            template='plotly_white',
            legend_title='Sessielengte',
            xaxis_title='Idle-interval (uren)',
            yaxis_title='Gemiddelde efficiëntie'
        )

        st.plotly_chart(fig_idle_bar, use_container_width=True, key='bar_idle_eff_2018')

        st.info("""
        **Opmerking:** Efficiëntie daalt significant bij idle-tijden > 4 uur.
        **Oplossing:** Streef naar idle-tijden onder 2 uur voor optimale efficiëntie.
        """)

    st.markdown("---")

    # Plot 5 – Heatmap
    st.subheader("IdleRatio Patronen: Dag en Uur")
    df_filtered['Dag'] = df_filtered['Started'].dt.day_name()
    df_filtered['Uur'] = df_filtered['Started'].dt.hour

    heat_data = df_filtered.pivot_table(
        index='Dag',
        columns='Uur', 
        values='IdleRatio',
        aggfunc='mean'
    ).reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])

    heat_data = heat_data.apply(lambda row: row.interpolate(method='linear', limit_direction='both'), axis=1)

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

    st.plotly_chart(fig5, use_container_width=True, key='heatmap_idle_ratio_2018')

    st.markdown("---")

    # Plot 6 – Correlatiematrix
    st.subheader("Correlatie Analyse")

    corr_cols = [
        'ChargeTime','ConnectedTime','TotalEnergy','MaxPower',
        'GemiddeldVermogen','Efficiëntie','IdleTijd','VermogensRatio','LaadEfficiëntie','IdleRatio'
    ]
    corr = df_filtered[corr_cols].corr()

    fig6 = px.imshow(
        corr,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        title='Correlatie Matrix tussen Laadpaal Variabelen',
        aspect='auto',
        height=500
    )
    st.plotly_chart(fig6, use_container_width=True, key='corr_matrix_2018')

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="IdleRatio ↔ Efficiëntie", value="-1.00", delta="-1.00")
        st.caption("Perfect negatief")
    with col2:
        st.metric(label="ConnectedTime ↔ IdleTijd", value="+0.95", delta="+0.95")
        st.caption("Zeer sterk positief")
    with col3:
        st.metric(label="ConnectedTime ↔ Efficiëntie", value="-0.77", delta="-0.77")
        st.caption("Sterk negatief")

    # Metric kleur styling
    st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg[data-icon="arrow-down"] { color: #ff4b4b !important; }
    [data-testid="stMetricDelta"] div[style*="color"]:has(svg[data-icon="arrow-down"]) { color: #ff4b4b !important; }
    [data-testid="stMetricDelta"] svg[data-icon="arrow-up"] { color: #00cc00 !important; }
    [data-testid="stMetricDelta"] div[style*="color"]:has(svg[data-icon="arrow-up"]) { color: #00cc00 !important; }
    </style>
    """, unsafe_allow_html=True)

    st.info("""
    **Opmerking:** Efficiëntieverlies wordt veroorzaakt door idle-tijd, niet door laadtijd.
    """)
