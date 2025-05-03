# --- Imports ---
import streamlit as st
import pandas as pd
import pymongo
import pycountry
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(
    page_title="Veille Agriculture 4.0",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

colors = ['#2e8b57', '#3cb371', '#66cdaa', '#98fb98', '#90ee90', '#7cfc00', '#00fa9a']

# --- MongoDB Data Loading ---
@st.cache_data
def load_mongo_data():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["veille_agriculture"]
    collections = [
        'google_alerts_Agriculture4.0',
        'ieee_agriculture_4_0_newest', 'ieee_agriculture_4_0_relevant',
        'scholar_agriculture_4_0_newest', 'scholar_agriculture_4_0_relevant',
        'springer_agriculture_4_0_newest', 'springer_agriculture_4_0_relevant',
        'wiley_agriculture_4_0_newest', 'wiley_agriculture_4_0_relevant',
        'talkwalker_alerts_Agricuture_4.0'
    ]

    all_data = []
    for name in collections:
        try:
            records = list(db[name].find({}))
            if records:
                df = pd.json_normalize(records)
                df["source"] = name.replace('_', ' ').replace('.', ' ').title()

                if "titre" in df.columns:
                    df.rename(columns={'titre': 'title', 'lien': 'url', 'pays': 'country'}, inplace=True)

                if "date" in df.columns:
                    df["insertion_date"] = pd.to_datetime(df["date"], errors="coerce")
                elif "published" in df.columns:
                    df["published_date"] = pd.to_datetime(df["published"], errors="coerce")
                elif "publication_date" in df.columns:
                    df["published_date"] = pd.to_datetime(df["publication_date"], errors="coerce")
                elif "year" in df.columns:
                    df["published_date"] = pd.to_datetime(df["year"], errors="coerce")

                all_data.append(df)
        except Exception as e:
            st.warning(f"Erreur dans {name} : {e}")
    all_data = [df for df in all_data if not df.empty]  # 🛠️ exclure les DF vides
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        if "published_date" in full_df.columns:
            full_df = full_df.dropna(subset=["published_date"])
            full_df["published_date"] = full_df["published_date"].dt.tz_localize(None)
        if "insertion_date" in full_df.columns:
            full_df["insertion_date"] = full_df["insertion_date"].dt.tz_localize(None)
        return full_df
    return pd.DataFrame()

# --- Utility Functions ---
def extract_domain(url, source):
    if pd.isna(url): return None
    try:
        if 'google.com/url' in url and 'Google Alerts' in source:
            parsed = urlparse(url)
            true_url = parse_qs(parsed.query).get('url', [None])[0]
            return urlparse(true_url).netloc if true_url else None
        return urlparse(url).netloc
    except:
        return None

def get_collection_label(name):
    if "Google Alerts" in name: return "Google Alerts"
    if "Ieee" in name: return "IEEE Xplore"
    if "Scholar" in name: return "Google Scholar"
    if "Springer" in name: return "Springer"
    if "Wiley" in name: return "Wiley Online Library"
    return name

def get_iso_alpha3(country_name):
    try:
        return pycountry.countries.search_fuzzy(country_name)[0].alpha_3
    except:
        return None

# --- Data Loading ---
df = load_mongo_data()
if df.empty:
    st.error("Aucune donnée chargée.")
    st.stop()

df['domain'] = df.apply(lambda row: extract_domain(row['url'], row['source']), axis=1)
df['source_label'] = df['source'].apply(get_collection_label)

# --- Filters Preparation ---
target_collections = [
    'Google Alerts Agriculture4 0', 'Ieee Agriculture 4 0 Newest',
    'Scholar Agriculture 4 0 Newest', 'Springer Agriculture 4 0 Newest',
    'Wiley Agriculture 4 0 Newest'
]
filtered_df = df[df['source'].isin(target_collections)]
max_insertion_date = filtered_df['insertion_date'].max()

relevant_collections = [
    'Ieee Agriculture 4 0 Relevant', 'Scholar Agriculture 4 0 Relevant',
    'Springer Agriculture 4 0 Relevant', 'Wiley Agriculture 4 0 Relevant'
]
relevant_df = df[df['source'].isin(relevant_collections)]
relevant_max_date = relevant_df['insertion_date'].max()
#sidebar
with st.sidebar:
    st.title("📊 Dashboard Agriculture 4.0")
    st.markdown("---")
    
    st.markdown("""
    Bienvenue dans le tableau de bord interactif dédié à l'analyse des contenus web sur *l'Agriculture 4.0*.

    Ce tableau de bord regroupe des *publications issues de plusieurs sources* : 
    - Articles scientifiques
    - Blogs 
    - Communiqués de presse
    - Revues techniques
    -....

    *🎯 Objectifs :*
    - Visualiser les tendances mondiales
    - Identifier les pays et plateformes les plus actifs
    - Suivre l'évolution des thématiques

    """)
    
    st.markdown("---")
    st.info("Mis à jour automatiquement à partir des données collectées (IEEE, Springer, Google Scholar, etc.)")
# --- Line 1: Stats | Map | Top Domains ---
st.title("🌾 Tableau de bord de la veille sur l'Agriculture 4.0")
st.markdown("---") 
st.header("📊 Vue Générale")
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader("📈 Statistiques")
    st.metric("Nombre total de publications collectées", len(df))
    st.metric("Nombre de sources uniques", df['domain'].nunique())
    last_date = df['insertion_date'].max()
    st.metric("Dernière mise à jour", last_date.strftime("%Y-%m-%d") if pd.notna(last_date) else "Non dispo")

with col2:
    st.subheader("🌍 Répartition géographique des publications")
    talkwalker_df = df[df['source'] == 'Talkwalker Alerts Agricuture 4 0']
    if 'country' in talkwalker_df.columns:
        country_counts = talkwalker_df['country'].value_counts().reset_index()
        country_counts.columns = ['country', 'count']
        country_counts['iso_alpha'] = country_counts['country'].apply(get_iso_alpha3)
        country_counts = country_counts.dropna(subset=['iso_alpha'])
        fig_map = px.choropleth(
            country_counts,
            locations="iso_alpha",
            color="count",
            hover_name="country",
            hover_data=["count"],
            color_continuous_scale=colors,
            title=""
        )
        fig_map.update_layout(geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'))
        st.plotly_chart(fig_map, use_container_width=True)

with col3:
    st.subheader("🔝 Top 10 des sources les plus actives")
    top_domains = df['domain'].value_counts().head(10).reset_index()
    top_domains.columns = ['Domaine', "Nombre de publications collectées"]
    st.dataframe(top_domains, use_container_width=True)

import streamlit.components.v1 as components
st.markdown("---")  # 👈 line separator
# --- Line 2: Latest & Relevant with true fixed boxes ---
st.header("📰 Contenus Récents et Pertinents collectés")
col4, col5 = st.columns(2)  # adjust widths as before

with col4:
    st.subheader("🆕 Derniers contenus détectés")
    sources = sorted(filtered_df['source_label'].dropna().unique().tolist())
    sources.insert(0, "Toutes les sources")
    sel = st.selectbox("Filtrer par source :", sources, key="fixed_recent_html")

    # Build one HTML blob
    html_recent = """
    <div style="
        height:300px;
        overflow-y:auto;
        padding:8px;
        border:1px solid #ddd;
        border-radius:4px;
        background:#fafafa;
    ">
    """
    if sel == "Toutes les sources":
        items = filtered_df[filtered_df['insertion_date'] == max_insertion_date]
    else:
        items = filtered_df[
            (filtered_df['insertion_date'] == max_insertion_date) &
            (filtered_df['source_label'] == sel)
        ]
    for _, row in items.iterrows():
        ds = row['insertion_date'].strftime('%Y-%m-%d')
        html_recent += f"""
        <div style="margin-bottom:10px;">
          <a href="{row['url']}" target="_blank" style="font-weight:bold; color:#2e8b57; text-decoration:none;">
            {row['title']}
          </a><br>
          <small style="color:#555;">{row['source_label']} — {ds}</small>
        </div>
        """
    html_recent += "</div>"

    # Render that single blob
    components.html(html_recent, height=320)  # height little bigger than 300px to fit scroll bar

with col5:
    st.subheader(f"⭐ Publications les plus pertinentes")
    rel_sources = sorted(relevant_df['source_label'].unique().tolist())
    rel_sources.insert(0, "Toutes les sources")
    sel2 = st.selectbox("Filtrer par source :", rel_sources, key="fixed_relevant_html")

    html_relevant = """
    <div style="
        height:300px;
        overflow-y:auto;
        padding:8px;
        border:1px solid #ddd;
        border-radius:4px;
        background:#fffdf8;
    ">
    """
    if sel2 == "Toutes les sources":
        rels = relevant_df[relevant_df['insertion_date'] == relevant_max_date]
    else:
        rels = relevant_df[
            (relevant_df['insertion_date'] == relevant_max_date) &
            (relevant_df['source_label'] == sel2)
        ]
    if rels.empty:
        html_relevant += "<p style='color:#777;'>Aucun article trouvé.</p>"
    else:
        for _, row in rels.iterrows():
            ds = row['insertion_date'].strftime('%Y-%m-%d')
            html_relevant += f"""
            <div style="margin-bottom:10px;">
              <a href="{row['url']}" target="_blank" style="font-weight:bold; color:#c47f00; text-decoration:none;">
                {row['title']}
              </a><br>
              <small style="color:#777;">{row['source_label']} — {ds}</small>
            </div>
            """
    html_relevant += "</div>"

    components.html(html_relevant, height=320)
st.markdown("---")  # 👈 line separator
st.markdown("<br>", unsafe_allow_html=True)
# --- Line 3: Wordcloud | Articles per Day ---
col6, col7 = st.columns(2)

with col6:
    st.subheader("☁️ Nuage de mots")
    all_titles = ' '.join(df['title'].dropna().astype(str).values)
    wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='Greens', max_words=200).generate(all_titles)
    fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
    ax_wc.imshow(wordcloud, interpolation='bilinear')
    ax_wc.axis('off')
    st.pyplot(fig_wc)

with col7:
    st.subheader("🗓️ publications par jour")
    df['insertion_day'] = df['insertion_date'].dt.date
    articles_per_day = df.groupby('insertion_day').size().reset_index(name='count')
    fig_articles = px.line(
        articles_per_day, x='insertion_day', y='count', markers=True,
        labels={'insertion_day': 'Date', 'count': "Nombre d'articles"},
        title=""
    )
    fig_articles.update_layout(xaxis_title="Date", yaxis_title="Nombre des publications", height=400)
    st.plotly_chart(fig_articles, use_container_width=True)
