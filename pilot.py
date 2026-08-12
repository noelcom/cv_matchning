import streamlit as st
import pandas as pd
import json
import os
import tempfile
import shutil
import time
from google import genai
from google.genai import types

# 1. Design och inställningar för webbsidan
st.set_page_config(page_title="CV-Matchning", page_icon="🚀", layout="wide")
st.title("🚀 Anonym CV-Matchning")

# 2. Hantera API-nyckel i sidopanelen
with st.sidebar:
    st.header("⚙️ Inställningar")
    api_key = st.text_input("Klistra in din Google Gemini API-nyckel", type="password")
    st.info("Nyckeln sparas inte när du stänger sidan. Det gör att appen kan delas utan att kosta dig pengar!")

# 3. Databas i minnet
if 'kandidat_db' not in st.session_state:
    st.session_state.kandidat_db = {}
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = []

tab1, tab2 = st.tabs(["1. Ny Analys", "2. Detaljer & Resultat"])

# --- FLIK 1: KÖR ANALYSEN ---
with tab1:
    st.markdown("### Klistra in arbetsannons och ladda upp CV:n")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        annons_text = st.text_area("Arbetsannons", height=250, placeholder="Klistra in texten från platsannonsen här...")
    with col2:
        uppladdade_filer = st.file_uploader("Ladda upp CV:n (.pdf)", type=["pdf"], accept_multiple_files=True)
        st.caption("🔒 **Datasäkerhet & GDPR:** Detta är en MVP. Inga CV-filer sparas permanent på någon server – allt bearbetas enbart i stunden i tillfälligt minne. Datan skickas krypterat via API för analys. Använd gärna anonymiserade test-CV:n.")
        
    if st.button("🧠 Starta AI-Analys", type="primary"):
        if not api_key:
            st.error("⚠️ Du måste lägga in din API-nyckel i sidopanelen (till vänster) först!")
        elif not uppladdade_filer:
            st.warning("⚠️ Du måste ladda upp minst ett CV!")
        elif not annons_text.strip():
            st.warning("⚠️ Du måste klistra in en arbetsannons!")
        else:
            client = genai.Client(api_key=api_key)
            
            # Den stenhårda och universella systeminstruktionen
            instruktion = """
            Du är en objektiv, extremt analytisk och fördomsfri AI-rekryterare. Ditt uppdrag är att revolutionera rekryteringsprocessen genom att leta efter *verklig* kompetens och relevant erfarenhet. Du är dock STENHÅRD och realistisk i din bedömning av ansvarsnivå och senioritet.

            DITT TILLVÄGAGÅNGSSÄTT:
            1. Analysera ansvarsnivå: Stirra dig inte blind på att en bransch matchar. Om annonsen söker en ledare, chef eller specialist, och kandidaten enbart har praktik, assistentroller eller instegsjobb, ska poängen dras ner kraftigt.
            2. Format-agnostisk: Ignorera CV:ts design och döm endast den faktiska datan.
            3. Översättbara färdigheter: Värdera praktisk problemlösning, men respektera de hårda kraven.

            STRIKT GDPR OCH ANONYMITET:
            För att garantera en 100% fördomsfri process får du under INGA omständigheter extrahera eller hinta om:
            - Namn, e-post, telefonnummer, adresser, ålder, kön, nationalitet eller länkar.
            Kandidaten existerar för dig enbart som en renodlad kompetensprofil.

            BEDÖMNING OCH SCORING (0-100) - STRIKTA REGLER:
            Du är en extremt kritisk bedömare. Du MÅSTE följa denna skala:
            - 0-30: Långt ifrån kraven. Saknar avgörande erfarenhet (t.ex. en junior/praktikant som söker en ledarroll).
            - 31-50: Uppfyller vissa grundkrav, men saknar rätt ansvarsnivå eller spetskompetens.
            - 51-75: En stark kandidat som uppfyller de flesta krav och kan axla rollen med viss upplärning.
            - 76-90: En extremt kvalificerad kandidat som överträffar kraven, har bevisad erfarenhet av exakt rätt ansvarsnivå och kan prestera från dag ett.
            - 91-100: En perfekt, exceptionell matchning (väldigt ovanligt).
            """
            
            temp_dir = tempfile.mkdtemp()
            st.session_state.leaderboard = [] 
            st.session_state.kandidat_db = {}
            
            # Visuell feedback: Progress bar
            totalt_antal = len(uppladdade_filer)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for nummer, fil in enumerate(uppladdade_filer, 1):
                # Uppdatera texten för användaren
                status_text.markdown(f"**⏳ Analyserar kandidat {nummer} av {totalt_antal}...**")
                
                # 1. Döljer filnamnet i gränssnittet
                anonymt_id = f"Kandidat #{nummer}"
                
                # 2. Ger filen ett säkert namn i bakgrunden för att undvika kraschar (åäö)
                safe_filename = f"cv_dokument_{nummer}.pdf"
                temp_path = os.path.join(temp_dir, safe_filename)
                
                with open(temp_path, "wb") as f:
                    f.write(fil.getbuffer())
                
                try:
                    uppladdad_pdf = client.files.upload(file=temp_path)
                    svar = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[instruktion, f"ARBETSANNONS:\n{annons_text}\n\nKANDIDATENS CV BIFOGAS.", uppladdad_pdf],
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type="application/json",
                            response_schema={
                                "type": "OBJECT",
                                "properties": {
                                    "score": {"type": "INTEGER"},
                                    "ar_erfarenhet": {"type": "INTEGER", "description": "Antal års relevant erfarenhet för rollen"},
                                    "utbildningsmatch": {"type": "STRING", "description": "Matchar utbildningen annonsens krav?"},
                                    "konkreta_resultat": {"type": "STRING", "description": "Vilka konkreta resultat eller projekt har kandidaten levererat?"},
                                    "nyckelkompetenser": {"type": "STRING", "description": "Hårda färdigheter, mjukvaror och språk"},
                                    "saknade_krav": {"type": "STRING", "description": "Vad saknar kandidaten baserat på annonsen? Var ärlig."},
                                    "motivation": {"type": "STRING", "description": "Kort och rak motivering till poängen"}
                                },
                                "required": ["score", "ar_erfarenhet", "utbildningsmatch", "konkreta_resultat", "nyckelkompetenser", "saknade_krav", "motivation"]
                            }
                        )
                    )
                    
                    resultat = json.loads(svar.text)
                    
                    # Sparar originalfilen för senare nedladdning
                    resultat["original_namn"] = fil.name
                    resultat["fil_data"] = fil.getvalue() 
                    
                    st.session_state.kandidat_db[anonymt_id] = resultat
                    st.session_state.leaderboard.append({"Kandidat": anonymt_id, "Poäng": resultat["score"], "Nyckelkompetenser": resultat["nyckelkompetenser"]})
                    
                except Exception as e:
                    st.error(f"Ett fel uppstod med Kandidat #{nummer}. Felmeddelande: {e}")
                
                finally:
                    # Radera filen från Googles servrar direkt efter analys
                    try:
                        if 'uppladdad_pdf' in locals():
                            client.files.delete(name=uppladdad_pdf.name)
                    except:
                        pass
                
                # När kandidaten är klar, uppdatera mätaren
                progress_bar.progress(nummer / totalt_antal)
                
                # Liten paus för att undvika rate limit-kraschar från Google
                time.sleep(2)
            
            # Radera den lokala mappen på Streamlit-servern
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            status_text.markdown("**✅ Alla kandidater färdiganalyserade!**")
            
            if st.session_state.leaderboard:
                st.success("Analys klar! Byt till fliken 'Detaljer & Resultat' ovan för att se vinnarna.")
                df = pd.DataFrame(st.session_state.leaderboard)
                df = df.sort_values(by="Poäng", ascending=False).reset_index(drop=True)
                df.index += 1
                st.dataframe(df[["Kandidat", "Poäng"]], use_container_width=True)

# --- FLIK 2: LEADERBOARD OCH DETALJER ---
with tab2:
    st.markdown("### 🏆 Leaderboard & Detaljerad AI-Analys")
    
    if not st.session_state.leaderboard:
        st.info("Ingen data laddad än. Kör en analys i Flik 1 först!")
    else:
        df = pd.DataFrame(st.session_state.leaderboard)
        df = df.sort_values(by="Poäng", ascending=False).reset_index(drop=True)
        df.index += 1
        
        col_list, col_details = st.columns([1, 2])
        
        with col_list:
            st.dataframe(df[["Kandidat", "Poäng"]], use_container_width=True)
            vald_kandidat = st.selectbox("🔍 Välj kandidat att granska djupare:", df["Kandidat"].tolist())
            
        with col_details:
            if vald_kandidat:
                data = st.session_state.kandidat_db[vald_kandidat]
                
                st.subheader(f"Analys för {vald_kandidat}")
                st.metric(label="AI Matchningspoäng", value=f"{data['score']} / 100")
                
                st.markdown("#### 📊 Erfarenhet & Utbildning")
                st.write(f"**Relevanta år i branschen:** {data['ar_erfarenhet']} år")
                st.write(f"**Utbildning:** {data['utbildningsmatch']}")
                
                st.markdown("#### 🚀 Konkreta resultat & Projekt")
                st.write(data['konkreta_resultat'])
                
                st.markdown("#### 🔑 Nyckelkompetenser & Språk")
                st.write(data['nyckelkompetenser'])
                
                st.markdown("#### ⚠️ Saknade krav (Gaps)")
                st.warning(data['saknade_krav'])
                
                st.markdown("#### 💡 AI:ns Motivering")
                st.info(data['motivation'])
                
                # Knapp för att bryta anonymiteten
                st.divider()
                st.markdown("#### 🔓 Avslöja & Kontakta")
                st.write("När du är redo att gå vidare med kandidaten kan du ladda ner originaldokumentet här.")
                st.download_button(
                    label=f"📥 Ladda ner original-CV",
                    data=data['fil_data'],
                    file_name=data['original_namn'],
                    mime="application/pdf",
                    type="primary"
                )
