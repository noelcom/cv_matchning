import streamlit as st
import pandas as pd
import json
import os
import tempfile
from google import genai
from google.genai import types

# 1. Design och inställningar för webbsidan
st.set_page_config(page_title="HR-AI: CV-Matchning", page_icon="🚀", layout="wide")
st.title("🚀 HR-AI: Anonym CV-Matchning")

# 2. Hantera API-nyckel i sidopanelen (Smart "Bring Your Own Key"-lösning)
with st.sidebar:
    st.header("⚙️ Inställningar")
    api_key = st.text_input("Klistra in din Google Gemini API-nyckel", type="password")
    st.info("Nyckeln sparas inte när du stänger sidan. Det gör att appen kan delas utan att kosta dig pengar!")

# 3. Databas i minnet (Ersätter Google Drive för att funka snabbt på webben)
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
        
    if st.button("🧠 Starta AI-Analys", type="primary"):
        if not api_key:
            st.error("⚠️ Du måste lägga in din API-nyckel i sidopanelen (till vänster) först!")
        elif not uppladdade_filer:
            st.warning("⚠️ Du måste ladda upp minst ett CV!")
        elif not annons_text.strip():
            st.warning("⚠️ Du måste klistra in en arbetsannons!")
        else:
            with st.spinner("Analyserar kandidater med AI... Detta kan ta en liten stund."):
                client = genai.Client(api_key=api_key)
                
                # Din sylvassa systeminstruktion
                instruktion = """
                Du är en objektiv, extremt analytisk och fördomsfri AI-rekryterare. Ditt uppdrag är att revolutionera rekryteringsprocessen genom att helt kringgå traditionella, byråkratiska ATS-system som bara räknar nyckelord. Du letar efter *verklig* kompetens, potential och relevant erfarenhet.

                DITT TILLVÄGAGÅNGSSÄTT (COMMON SENSE OCH HELHETSSYN):
                1. Läs mellan raderna: Stirra dig inte blind på specifika buzzwords. Om en kandidat beskriver att de "byggt och driftsatt ett komplett ordersystem", ska du använda din branschkunskap för att förstå vilka tekniker och kompetenser som krävdes för det, även om kandidaten glömt skriva ut exakta nyckelord.
                2. Format-agnostisk (Objektivitet): Du ska helt ignorera CV:ts design, grammatik och layout. Ett rörigt, oformaterat textdokument med fantastisk erfarenhet ska få EXAKT samma bedömning som ett hyperoptimerat design-CV med samma innehåll. Döm endast den faktiska datan.
                3. Översättbara färdigheter (Transferable skills): Värdera praktisk problemlösning, verkliga resultat och förmågan att lära sig över stela jobbtitlar.

                STRIKT GDPR OCH ANONYMITET (KRITISKT KRAV):
                För att garantera en 100% fördomsfri och laglig process får du under INGA omständigheter extrahera, nämna eller hinta om följande i ditt svar:
                - Namn, e-post, telefonnummer, adresser eller postorter.
                - Ålder, födelsedatum, kön, könsidentitet eller pronomen (använd neutrala omskrivningar om du måste).
                - Nationalitet, etniskt ursprung, modersmål eller civilstånd.
                - Bilder, länkar till LinkedIn, GitHub eller hemsidor som kan identifiera personen.
                Kandidaten existerar för dig enbart som en renodlad kompetensprofil.

                BEDÖMNING OCH SCORING (0-100):
                Jämför kandidatens bevisade erfarenheter mot den bifogade arbetsannonsens krav. Sätt en rättvis poäng. Ge inte automatiskt höga poäng bara för att kandidaten "nämner" ett ord från annonsen, utan kräv kontext att de faktiskt har *använt* kompetensen. En poäng över 80 ska innebära att kandidaten bevisligen kan klara av arbetsuppgifterna från dag ett.
                """
                
                for nummer, fil in enumerate(uppladdade_filer, 1):
                    # 1. Döljer namnet i gränssnittet
                    anonymt_id = f"Kandidat #{nummer}"
                    
                    # 2. Skapar ett säkert filnamn (ändrat till engelskt variabelnamn)
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
                                        "motivation": {"type": "STRING"},
                                        "nyckelkompetenser": {"type": "STRING"},
                                        "profil": {"type": "STRING"},
                                        "utbildning": {"type": "STRING"},
                                        "erfarenhetsniva": {"type": "STRING"}
                                    },
                                    "required": ["score", "motivation", "nyckelkompetenser", "profil", "utbildning", "erfarenhetsniva"]
                                }
                            )
                        )
                        
                        resultat = json.loads(svar.text)
                        
                        st.session_state.kandidat_db[anonymt_id] = resultat
                        st.session_state.leaderboard.append({"Kandidat": anonymt_id, "Poäng": resultat["score"], "Nyckelkompetenser": resultat["nyckelkompetenser"]})
                        
                    except Exception as e:
                        st.error(f"Ett fel uppstod med {fil.name}. Felmeddelande: {e}")
                
                if st.session_state.leaderboard:
                    st.success("✅ Analys klar! Byt till fliken 'Detaljer & Resultat' ovan för att se vinnarna.")
                    df = pd.DataFrame(st.session_state.leaderboard)
                    df = df.sort_values(by="Poäng", ascending=False).reset_index(drop=True)
                    df.index += 1
                    st.dataframe(df, use_container_width=True)

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
                
                st.markdown("#### 🔑 Nyckelkompetenser")
                st.write(data['nyckelkompetenser'])
                
                st.markdown("#### 💼 Erfarenhet & Utbildning")
                st.write(f"**Nivå:** {data['erfarenhetsniva']}")
                st.write(f"**Utbildning:** {data['utbildning']}")
                
                st.markdown("#### 📝 Sammanfattning av Profil")
                st.write(data['profil'])
                
                st.markdown("#### 💡 AI:ns Motivering")
                st.info(data['motivation'])
