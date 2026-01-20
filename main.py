import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import re

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="YouTube AI & Metadata Explorer", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS UTILES ---
def get_video_id(url):
    """Extrait l'ID d'une URL YouTube (standard, short, ou embed)."""
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([^"&?/\s]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_youtube_client(api_key):
    return build("youtube", "v3", developerKey=api_key)

# --- INTERFACE LATERALE (SIDEBAR) ---
st.sidebar.title("🛠️ Paramètres")
api_key = st.sidebar.text_input("Clé API YouTube Data v3", type="password", help="Obtenez-en une sur Google Cloud Console")

search_mode = st.sidebar.radio("Mode de recherche", ["Par Mot-clé", "Par URL unique"])

# Gestion des langues
lang_options = {"Français": "fr", "Anglais": "en", "Espagnol": "es", "Allemand": "de"}
selected_lang = st.sidebar.selectbox("Langue de recherche (Origine)", list(lang_options.keys()))

max_results = st.sidebar.slider("Nombre de vidéos (pour mot-clé)", 5, 50, 15)

# --- CONTENU PRINCIPAL ---
st.title("🔍 Détecteur de Marqueurs IA sur YouTube")

with st.expander("ℹ️ Comment ça fonctionne ? (Explications)"):
    st.write("""
    Cette application interroge l'**API officielle de Google (YouTube Data v3)**. 
    Elle cherche un marqueur spécifique introduit en 2024 : `containsSyntheticMedia`.
    
    * **✅ OUI :** Le créateur a coché la case indiquant que le contenu est généré ou modifié par une IA (visages réalistes, lieux réels modifiés, voix synthétique).
    * **❌ NON :** Aucune déclaration d'IA n'est présente dans les métadonnées techniques.
    
    
    """)

# --- LOGIQUE DE RECHERCHE ---
if search_mode == "Par Mot-clé":
    query = st.text_input("Entrez votre recherche", "changement climatique")
    btn_label = "Lancer l'analyse groupée"
else:
    query = st.text_input("Collez l'URL de la vidéo", "https://www.youtube.com/watch?v=...")
    btn_label = "Analyser cette vidéo"

if st.button(btn_label):
    if not api_key:
        st.error("Veuillez saisir votre clé API dans la barre latérale.")
    else:
        try:
            yt = get_youtube_client(api_key)
            ids_to_check = []

            # ÉTAPE 1 : RÉCUPÉRER LES ID
            if search_mode == "Par Mot-clé":
                search_res = yt.search().list(
                    q=query,
                    part="id",
                    maxResults=max_results,
                    type="video",
                    relevanceLanguage=lang_options[selected_lang]
                ).execute()
                ids_to_check = [item['id']['videoId'] for item in search_res.get('items', [])]
            else:
                vid_id = get_video_id(query)
                if vid_id: ids_to_check = [vid_id]
                else: st.error("URL YouTube invalide.")

            # ÉTAPE 2 : RÉCUPÉRER LES MÉTADONNÉES IA
            if ids_to_check:
                video_res = yt.videos().list(
                    part="snippet,status,statistics",
                    id=",".join(ids_to_check)
                ).execute()

                data = []
                for item in video_res.get('items', []):
                    status = item.get('status', {})
                    # C'est ici que se trouve le marqueur IA
                    is_ai = status.get('containsSyntheticMedia', False)
                    
                    data.append({
                        "Identifiant": item['id'],
                        "Titre": item['snippet']['title'],
                        "Chaîne": item['snippet']['channelTitle'],
                        "Marqueur IA": "OUI" if is_ai else "NON",
                        "Vues": item['statistics'].get('viewCount', '0'),
                        "Date": item['snippet']['publishedAt'][:10],
                        "Lien": f"https://www.youtube.com/watch?v={item['id']}"
                    })

                # --- AFFICHAGE ---
                df = pd.DataFrame(data)
                
                # Style pour le tableau
                def color_label(val):
                    color = 'background-color: #ff4b4b; color: white' if val == "OUI" else ''
                    return color

                st.subheader(f"Résultats de l'analyse ({len(data)} vidéos)")
                st.table(df.style.applymap(color_label, subset=['Marqueur IA']))

                # --- EXPORT CSV ---
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger le rapport (CSV)",
                    data=csv,
                    file_name=f"rapport_youtube_ia_{query.replace(' ', '_')}.csv",
                    mime='text/csv',
                )

        except Exception as e:
            st.error(f"Erreur API : {e}")

# --- PIED DE PAGE ---
st.divider()
st.caption("Note : Ce marqueur dépend de l'auto-déclaration des créateurs ou de la détection automatique par YouTube.")
