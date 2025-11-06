import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.title("Steam game gebruik:")


kaarten = pd.read_csv("1verbetercsv.csv")

# Filter totaalrij eruit
kaarten_filtered = kaarten[~kaarten['country'].isin(['Totaal', 'All countries', 'Total'])].copy()

pop_2021 = pd.read_csv("A2021_population.csv")
pop_2021 = pop_2021[['country', '2021_last_updated']].copy()
pop_2021['2021_last_updated'] = pop_2021['2021_last_updated'].str.replace(",", "").astype(int)

url_2024 = 'https://storage.googleapis.com/kagglesdsdata/datasets/5331522/8856555/World%20Population%20by%20country%202024.csv?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=gcp-kaggle-com%40kaggle-161607.iam.gserviceaccount.com%2F20251106%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20251106T150358Z&X-Goog-Expires=259200&X-Goog-SignedHeaders=host&X-Goog-Signature=35c43c7451727fd509358759005686e4cd59fbbec3a516b8106abe51f059dbe7085b2524d2e9f276b1f0bf18496e8d385eccacf32098a1ba8cc3c853e372a40b552aa0a9c195cab38f828ca1c016ef999c336b635e28cbce3fb45b8775821f1ca785ada3cc4fda1e9144a97986e880544b7c5a3470a4e57af9acd95fe6855e8f97ee5559401dd77eaac0c3004381f1b84dd219b766d615eecb2ea14913a93f558054d7ee2120d5b405a11af16ae9e5ab8e0c44ad290d50ab721eb58105541cc1d8d1851fe68e02bd7b032d5da5e42600541979bfb4d5fa4133019eff99d7dfc8c04912ac538b44de8ab36c75e777e7d4e17a0e00d104554c47fb4babd6361794'
r = requests.get(url_2024)
data_2024 = StringIO(r.text)
pop_2024 = pd.read_csv(data_2024)
pop_2024 = pop_2024[['Country', 'Population 2024']].copy()
pop_2024['Population 2024'] = pop_2024['Population 2024'].astype(str).str.replace(",", "").astype(int)


st.sidebar.header("Kies optie")
optie = st.sidebar.selectbox(
    "Wat wil je bekijken?", 
    ["Kaart en gebruikers per land", "Lineaire voorspelling"]
)

if optie == "Kaart en gebruikers per land":

    st.title("Aantal Steam-gebruikers per land (2021 vs 2024)")
    
    # Keuze top 10 basisjaar onder de titel
    st.subheader("Selecteer basisjaar voor Top 10")
    basisjaar = st.radio("Kies jaar:", ["2024", "2021"])


    # Top 10 landen op basis van gekozen jaar
    jaar_col = f"SteamUsers_{basisjaar}"
    top10 = kaarten_filtered.sort_values(by=jaar_col, ascending=False).head(10).copy()

    # Verschil berekenen
    top10['Verschil_2024_2021'] = top10['SteamUsers_2024'] - top10['SteamUsers_2021']

    # Totaal van top 10 berekenen
    totaal_row = pd.DataFrame({
        'country': ['Totaal'],
        'SteamUsers_2021': [top10['SteamUsers_2021'].sum()],
        'SteamUsers_2024': [top10['SteamUsers_2024'].sum()],
        'Verschil_2024_2021': [top10['Verschil_2024_2021'].sum()]
    })

    # Combineer totaal en top 10
    df_display = pd.concat([totaal_row, top10], ignore_index=True)

    # Formatteren getallen
    for col in ['SteamUsers_2021', 'SteamUsers_2024']:
        df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}".replace(",", "."))
    df_display['Verschil_2024_2021'] = df_display['Verschil_2024_2021'].apply(
        lambda x: f"+{x:,.0f}".replace(",", ".") if x > 0 else f"{x:,.0f}".replace(",", ".")
    )

    # Index vanaf 1 zetten
    df_display.index = range(1, len(df_display) + 1)

    # --------------------------
    # KPI's gebaseerd op totaal_row uit Top 10 tabel
    # --------------------------

    # totaal_row moet al bestaan zoals in je code:
    # totaal_row = pd.DataFrame({
    #     'country': ['Totaal'],
    #     'SteamUsers_2021': [top10['SteamUsers_2021'].sum()],
    #     'SteamUsers_2024': [top10['SteamUsers_2024'].sum()],
    #     'Verschil_2024_2021': [top10['Verschil_2024_2021'].sum()]
    # })

    totaal_2021 = int(totaal_row['SteamUsers_2021'].values[0])
    totaal_2024 = int(totaal_row['SteamUsers_2024'].values[0])
    totaal_verschil = int(totaal_row['Verschil_2024_2021'].values[0])

    # --------------------------
    # KPI-weergave in Streamlit
    # --------------------------
    st.subheader("Totaal Steam-gebruikers Top 10 + totaal")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Totaal gebruikers (2021)",
        value=f"{totaal_2021:,.0f}".replace(",", "."),
    )

    col2.metric(
        label="Totaal gebruikers (2024)",
        value=f"{totaal_2024:,.0f}".replace(",", "."),
    )

    col3.metric(
        label="Totaal verschil",
        value=f"{totaal_verschil:+,.0f}".replace(",", "."),
    )

    # DataFrame tonen zonder totaalrij en met reset index
    st.subheader("Top 10 landen Steam-gebruikers")

    # Filter totaalrij weg
    top10_only = df_display[df_display['country'] != 'Totaal'].copy()

    # Index resetten vanaf 1
    top10_only.index = range(1, len(top10_only) + 1)

    # Toon in Streamlit
    st.dataframe(
        top10_only[['country', 'SteamUsers_2021', 'SteamUsers_2024', 'Verschil_2024_2021']],
        height=250
    )

    kaarten_long = top10.melt(
        id_vars=["country"],
        value_vars=["SteamUsers_2021", "SteamUsers_2024"],
        var_name="Year",
        value_name="SteamUsers"
    )
    kaarten_long["Year"] = kaarten_long["Year"].str.replace("SteamUsers_", "")
    kaarten_long['SteamUsers_fmt'] = kaarten_long['SteamUsers'].apply(lambda x: f"{x:,.0f}".replace(",", "."))

    fig = px.bar(
        kaarten_long,
        x="Year",
        y="SteamUsers",
        color="country",
        barmode="group",
        text="SteamUsers_fmt",
        title="Top 10 landen met meeste Steam-gebruikers (2021 vs 2024)"
    )

    fig.update_traces(
        textposition='inside',
        hovertemplate='<b></b><br>Jaar: %{x}<br>Gebruikers: %{text}'
    )

    fig.update_layout(
        yaxis_title="Aantal gebruikers",
        xaxis_title="Jaar",
        bargap=0.15
    )

    st.plotly_chart(fig, use_container_width=True)

    # Merge Steam-data met 2021 bevolking
    steam_pop = pd.merge(
        kaarten_filtered,
        pop_2021,
        on='country',
        how='left'
    )
    steam_pop['Pct_2021'] = steam_pop['SteamUsers_2021'] / steam_pop['2021_last_updated'] * 100

    # Merge met 2024 bevolking
    steam_pop = pd.merge(
        steam_pop,
        pop_2024,
        left_on='country',
        right_on='Country',
        how='left'
    )
    steam_pop['Pct_2024'] = steam_pop['SteamUsers_2024'] / steam_pop['Population 2024'] * 100

    # Verschil berekenen
    steam_pop['Verschil_pct'] = steam_pop['Pct_2024'] - steam_pop['Pct_2021']

    # Top 10 landen op basis van SteamUsers_2024
    top10_pct = steam_pop.sort_values(by='SteamUsers_2024', ascending=False).head(10).copy()

    # Formatteren percentages
    top10_pct['Pct_2021_fmt'] = top10_pct['Pct_2021'].map(lambda x: f"{x:.2f}%")
    top10_pct['Pct_2024_fmt'] = top10_pct['Pct_2024'].map(lambda x: f"{x:.2f}%")
    top10_pct['Verschil_pct_fmt'] = top10_pct['Verschil_pct'].apply(
        lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%"
    )

    # Index vanaf 1
    top10_pct.index = range(1, len(top10_pct) + 1)

    # --- Outlier-instellingen bovenaan KPI-sectie ---
    st.subheader("Outlier-instellingen")
    show_outliers = st.checkbox("Outliers tonen", value=True)
    drempel = st.slider(
        "Outlier-drempel (% van bevolking)",
        min_value=0.0,
        max_value=100.0,
        value=69.0,
        step=0.5
    )

    # --- Pas outliers toe op steam_pop ---
    steam_pop_mod = steam_pop.copy()
    if not show_outliers:
        for jaar in ["Pct_2021", "Pct_2024"]:
            steam_pop_mod.loc[steam_pop_mod[jaar] > drempel, jaar] = drempel

    # --- Gebruik steam_pop_mod voor KPI-berekeningen ---
    steam_pct_combined = steam_pop_mod[['country', 'Pct_2021', 'Pct_2024']].dropna().copy()
    steam_pct_combined['Verschil_pct'] = steam_pct_combined['Pct_2024'] - steam_pct_combined['Pct_2021']
    steam_pct_combined['Groei_pctpunt'] = steam_pct_combined['Verschil_pct']

    # Berekeningen
    gem_groei_pctpunt = steam_pct_combined['Groei_pctpunt'].mean()
    gem_pct_2021 = steam_pct_combined['Pct_2021'].mean()
    gem_pct_2024 = steam_pct_combined['Pct_2024'].mean()
    delta_gem_pct = gem_pct_2024 - gem_pct_2021
    max_pct_land = steam_pct_combined.loc[steam_pct_combined['Pct_2024'].idxmax(), 'country']
    max_pct_value = steam_pct_combined['Pct_2024'].max()

    # --- KPI-weergave ---
    st.subheader("KPI’s: Percentage bevolking dat Steam gebruikt per land")
    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Gem. groei in % (2021 → 2024)",
        value=f"{gem_groei_pctpunt:+.2f} %",
    )  

    col2.metric(
        label="Gem. % dat Steam speelt in 2024",
        value=f"{gem_pct_2024:.2f}%",
        delta=f"{delta_gem_pct:+.2f}% t.o.v. 2021",
    )

    col3.metric(
        label="Land met hoogste % bevolking (2024)",
        value=f"{max_pct_land}",
        delta=f"{max_pct_value:.2f}%",
    )

    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import requests
    from io import StringIO

    st.title("Percentage bevolking dat Steam speelt per land")

    # --- Steam-data ---
    kaarten = pd.read_csv("1verbetercsv.csv")
    kaarten_filtered = kaarten[~kaarten['country'].isin(['Totaal', 'All countries', 'Total'])].copy()

    # --- Population 2021 ---
    pop_2021 = pd.read_csv("A2021_population.csv")
    pop_2021 = pop_2021[['country', '2021_last_updated']].copy()
    pop_2021['2021_last_updated'] = pop_2021['2021_last_updated'].str.replace(",", "").astype(int)

    # --- Population 2024 via API/URL ---
    url_2024 = 'https://storage.googleapis.com/kagglesdsdata/datasets/5331522/8856555/World%20Population%20by%20country%202024.csv?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=gcp-kaggle-com%40kaggle-161607.iam.gserviceaccount.com%2F20251106%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20251106T120252Z&X-Goog-Expires=259200&X-Goog-SignedHeaders=host&X-Goog-Signature=8a483e42b215d2c05231d368528ccd10834b2d67e3e8ee5d0b7f6da933044b07bd938e1f867b7b4837b36cd6fd5ef36d60ded8237987083261dc1136d79fa3a01ab92650e7e011bf550986a012cf9195183c4e4628ab8da7fcfa38674626699665125997b67baf664a3ec232c2c9e47f0f49551b596f6e1a39469028f5fab0eb9a624d903c61c70db2af09d0f17ab1114fe916c77ee155fda612df5d140bdb247c881f2f57932e5e9c3ce10ae5c136c86dc73f7365afca3fdef068758f2cfdc346aaa38ad94f752b1355863b2cfdc7cc17f9f689299b475266ff8de79f0c9f8b124d8d2e01a1106dfb9d124e52c785550371a92e2f7c071227bf6ec39784f9ac'
    r = requests.get(url_2024)
    data_2024 = StringIO(r.text)
    pop_2024 = pd.read_csv(data_2024)
    pop_2024 = pop_2024[['Country', 'Population 2024']].copy()
    pop_2024['Population 2024'] = pop_2024['Population 2024'].astype(str).str.replace(",", "").astype(int)

    # --- Merge Steam-data met populaties ---
    steam_pop = pd.merge(kaarten_filtered, pop_2021, left_on='country', right_on='country', how='left')
    steam_pop = pd.merge(steam_pop, pop_2024, left_on='country', right_on='Country', how='left')

    # --- Bereken % bevolking dat Steam speelt ---
    steam_pop['Pct_2021'] = steam_pop['SteamUsers_2021'] / steam_pop['2021_last_updated'] * 100
    steam_pop['Pct_2024'] = steam_pop['SteamUsers_2024'] / steam_pop['Population 2024'] * 100

    # --- Jaar selectie boven de kaart ---
    jaar = st.radio(
        "Kies jaar:",
        ["2024", "2021"],
        key="jaar_pct"
    )

    # --- Kolommen voor gekozen jaar ---
    kolom_pct = f"Pct_{jaar}"
    kolom_abs = f"SteamUsers_{jaar}"

    # --- Plotly choropleth met vaste kleurenschaal 0% → 100% ---
    fig = px.choropleth(
        steam_pop_mod,
        locations="country",
        locationmode="country names",
        color=kolom_pct,
        hover_name="country",
        hover_data={
            kolom_abs: True,        # absoluut aantal gebruikers
            kolom_pct: ':.2f'       # % van bevolking
        },
        color_continuous_scale="Viridis",
        range_color=(0, 100),
        title=f"% van de bevolking dat Steam speelt ({jaar})"

    )

    fig.update_coloraxes(colorbar_title="% van bevolking")
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

    st.plotly_chart(fig, use_container_width=True)

elif optie == "Lineaire voorspelling":
    #------------
    import streamlit as st
    import pandas as pd
    import numpy as np
    import plotly.express as px

    st.title("Lineaire voorspelling")

    # Checkbox: tonen of niet
    show_pyramid = st.checkbox("Leeftijdsverdeling laten zien")

    if show_pyramid:
        # CSV inlezen
        df = pd.read_csv("AWORLD-2020.csv")

        # Leeftijdsgroepen
        age_groups = df['Age'].tolist()

        # Mannen en vrouwen aantallen
        male_values = df['M'].values
        female_values = df['F'].values

        # Percentage van totaal per geslacht
        male_percent = 100 * male_values / male_values.sum()
        female_percent = 100 * female_values / female_values.sum()

        # DataFrame voor piramide
        pyramid_df = pd.DataFrame({
            "Leeftijdsgroep": age_groups*2,
            "Percentage": np.concatenate([-male_percent, female_percent]),  # mannen negatief
            "Geslacht": ["Mannen"]*len(age_groups) + ["Vrouwen"]*len(age_groups)
        })

        # Maximale waarde voor symmetrische x-as
        max_val = max(male_percent.max(), female_percent.max()) * 1.1

        # Plotly piramide
        fig = px.bar(
            pyramid_df,
            x="Percentage",
            y="Leeftijdsgroep",
            color="Geslacht",
            orientation="h",
            text=np.abs(pyramid_df["Percentage"]).round(1),
            hover_data={
                "Geslacht": True,
                "Leeftijdsgroep": True,
                "Percentage": ':.1f'
            },
            barmode="overlay",
            title="Bevolkingspiramide van de wereld (2020)",
            color_discrete_map={"Mannen": "blue", "Vrouwen": "pink"}  # kleuren instellen
        )

        # Layout aanpassingen
        fig.update_layout(
            yaxis={
                'title': "Leeftijdsgroep",
                'categoryorder':'array',
                'categoryarray': age_groups[::-1]  # jong onderaan, oud bovenaan
            },
            xaxis=dict(
                title="Percentage",
                tickvals=[-max_val, -max_val/2, 0, max_val/2, max_val],
                ticktext=[f"{int(max_val)}%", f"{int(max_val/2)}%", "0%", f"{int(max_val/2)}%", f"{int(max_val)}%"],
                range=[-max_val, max_val]
            ),
            bargap=0.1
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vink het vakje aan om de leeftijdsverdeling te bekijken.")

    # DataFrame maken met jouw verdeling
    data = {
        "Leeftijdsgroep": ["16–24", "25–34", "35–44", "45–54", "55–64", "65+"],
        "Percentage_gamers": [25, 28, 17, 13, 9, 8]
    }
    game_leeftijd_df = pd.DataFrame(data)

    # Checkbox om tabel te tonen of verbergen
    show_table = st.checkbox("Toon verdeling van gamers per leeftijdsgroep", value=True)

    if show_table:
        # Percentages als string met % weergeven
        df_display = game_leeftijd_df.copy()
        df_display['Percentage_gamers'] = df_display['Percentage_gamers'].astype(str) + '%'
        
        st.subheader("Verdeling van gamers per leeftijdsgroep")
        st.dataframe(df_display)             
    
    import streamlit as st
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression

    # --- Data importeren ---
    steam_df = pd.read_csv("1verbetercsv.csv")
    steam_df.columns = steam_df.columns.str.strip()

    # Populatie 2021
    pop_2021 = pd.read_csv("A2021_population.csv")
    pop_2021.columns = pop_2021.columns.str.strip()
    pop_2021["2020_population"] = pop_2021["2020_population"].str.replace(",", "").astype(int)
    pop_2021 = pop_2021.rename(columns={"country": "country", "2020_population": "Population_2021"})

    import pandas as pd
    import requests
    from io import StringIO

    # URL van de Kaggle dataset (zonder speciale tekens / headers)
    url = "https://storage.googleapis.com/kagglesdsdata/datasets/5331522/8856555/World%20Population%20by%20country%202024.csv?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=gcp-kaggle-com%40kaggle-161607.iam.gserviceaccount.com%2F20251106%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20251106T120252Z&X-Goog-Expires=259200&X-Goog-SignedHeaders=host&X-Goog-Signature=8a483e42b215d2c05231d368528ccd10834b2d67e3e8ee5d0b7f6da933044b07bd938e1f867b7b4837b36cd6fd5ef36d60ded8237987083261dc1136d79fa3a01ab92650e7e011bf550986a012cf9195183c4e4628ab8da7fcfa38674626699665125997b67baf664a3ec232c2c9e47f0f49551b596f6e1a39469028f5fab0eb9a624d903c61c70db2af09d0f17ab1114fe916c77ee155fda612df5d140bdb247c881f2f57932e5e9c3ce10ae5c136c86dc73f7365afca3fdef068758f2cfdc346aaa38ad94f752b1355863b2cfdc7cc17f9f689299b475266ff8de79f0c9f8b124d8d2e01a1106dfb9d124e52c785550371a92e2f7c071227bf6ec39784f9ac"

    # Ophalen van de CSV via requests
    response = requests.get(url)
    if response.status_code == 200:
        csv_data = StringIO(response.text)
        pop_2024 = pd.read_csv(csv_data)
        pop_2024.columns = pop_2024.columns.str.strip()
        pop_2024 = pop_2024.rename(columns={"Country": "country", "Population 2024": "Population_2024"})
        pop_2024["Population_2024"] = pop_2024["Population_2024"].astype(int)
    else:
        st.error(f"Kon pop_2024 niet ophalen van de API, status code: {response.status_code}")
        pop_2024 = pd.DataFrame(columns=["country","Population_2024"])


    # --- Bereken Pct_2021 ---
    df = steam_df.merge(pop_2021[["country","Population_2021"]], on="country", how="left")
    df["Pct_2021"] = df["SteamUsers_2021"] / df["Population_2021"] * 100
    df = df.merge(pop_2024[["country","Population_2024"]], on="country", how="left")
    df["Pct_2024"] = df["SteamUsers_2024"] / df["Population_2024"] * 100

    # --- Leeftijdsverdeling gamers ---
    game_leeftijd_df = pd.DataFrame({
        "Leeftijdsgroep": ["16–24", "25–34", "35–44", "45–54", "55–64", "65+"],
        "Percentage_gamers": [25,28,17,13,9,8]
    })
    pct_jongeren = game_leeftijd_df.loc[game_leeftijd_df["Leeftijdsgroep"]=="16–24", "Percentage_gamers"].values[0]
    pct_ouderen = game_leeftijd_df.loc[game_leeftijd_df["Leeftijdsgroep"].isin(["35–44","45–54","55–64","65+"]), "Percentage_gamers"].sum()

    # --- Lineair regressie met log-transformatie ---
    df_model = df.dropna(subset=["Pct_2021", "Population_2024", "SteamUsers_2024"])
    X = df_model[["Pct_2021"]].copy()
    X["Pct_Jongeren"] = pct_jongeren
    X["Pct_Ouderen"] = pct_ouderen
    y_log = np.log(df_model["Pct_2024"] + 1)
    model = LinearRegression()
    model.fit(X, y_log)

    # --- Helper functie voor eenvoudige landmatching ---
    def match_land(land_input, landen_lijst):
        land_input = land_input.lower()
        for land in landen_lijst:
            if land_input in land.lower() or land.lower() in land_input:
                return land
        return land_input  # geen match

    # --- Streamlit interface ---
    st.title("Voorspelling Steam-gebruik 2024 per land (log-transformatie)")

    landen_lijst = sorted(list(df["country"].unique()))
    landen_lijst.insert(0, "Ander")
    land = st.selectbox("Selecteer een land:", landen_lijst)

    if land == "Ander":
        land_input = st.text_input("Typ het land:")
        if land_input:
            land = match_land(land_input, df["country"].tolist())

    if land:
        pct_2021_land = None
        pop_2024_land = None
        werkelijk_pct = None

        # --- Automatische lookup ---
        if land in df["country"].values:
            pct_2021_land = float(df.loc[df["country"]==land, "Pct_2021"])
            pop_2024_land = int(df.loc[df["country"]==land, "Population_2024"])
            werkelijk_pct = df.loc[df["country"]==land, "Pct_2024"].values[0]  # kan NaN zijn
        else:
            # Handmatige input indien onbekend land
            pct_2021_land = st.number_input("Pct_2021 (% Steam-users)", min_value=0.0, max_value=100.0, value=1.0)
            pop_2024_land = st.number_input("Populatie 2024", min_value=1, value=1000000)

        # --- Model input & voorspelling ---
        X_pred = pd.DataFrame({
            "Pct_2021": [pct_2021_land],
            "Pct_Jongeren": [pct_jongeren],
            "Pct_Ouderen": [pct_ouderen]
        })

        pct_2024_pred_log = model.predict(X_pred)[0]
        pct_2024_pred = np.exp(pct_2024_pred_log) - 1
        steam_pred_abs = int(pct_2024_pred/100 * pop_2024_land)

        # Veilig omgaan met NaN in werkelijk_pct
        steam_werkelijk_abs = int(werkelijk_pct/100 * pop_2024_land) if pd.notna(werkelijk_pct) else None
         
# --- Resultaten tonen in Streamlit met kolommen ---
    st.subheader(f"Resultaten voor {land}:")

    # Eerste rij van 3 kolommen: belangrijkste percentages en absolute voorspelling
    col1, col2, col3 = st.columns(3)
    col1.metric("Voorspeld % Steam-users 2024", f"{pct_2024_pred:.2f}%")
    col2.metric(
        "Werkelijk % Steam-users 2024", 
        f"{werkelijk_pct:.2f}%" if pd.notna(werkelijk_pct) else "n.v.t."
    )
    col3.metric("Absolute voorspelde Steam-users", f"{steam_pred_abs:,}")

    # Tweede rij van 3 kolommen: absolute werkelijke, verschil en % groei t.o.v. 2021
    col4, col5, col6 = st.columns(3)
    col4.metric(
        "Absolute werkelijke Steam-users", 
        f"{steam_werkelijk_abs:,}" if steam_werkelijk_abs is not None else "n.v.t."
    )
    col5.metric(
        "Verschil voorspelling t.o.v. werkelijkheid", 
        f"{(steam_pred_abs - steam_werkelijk_abs):,}" if steam_werkelijk_abs is not None else "n.v.t."
    )
    col6.metric("% toename t.o.v. 2021", f"{pct_2024_pred - pct_2021_land:+.2f}%")

    # Extra details optioneel in een expander
    with st.expander("Meer details"):
        st.write(f"- Pct_2021 land: {pct_2021_land:.2f}%")
        st.write(f"- Populatie 2024: {pop_2024_land:,}")
