import streamlit as st
import pandas as pd
import json
import time
import io
import PyPDF2
import anthropic

# 1. Design och inställningar för webbsidan (Måste vara överst)
st.set_page_config(page_title="CV-Matchning Pilot", page_icon="🚀", layout="wide")

# --- LÖSENORDSSKYDD START ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "pilot2026": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Ange lösenord för Early Access:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Ange lösenord för Early Access:", type="password", on_change=password_entered, key="password")
        st.error("Fel lösenord. Försök igen.")
        return False
    return True
# --- LÖSENORDSSKYDD SLUT ---

# Kontrollera lösenord innan resten av sidan visas
if check_password():
    st.title("🚀 Anonym CV-Matchning Pilot")

    # 2. Inbakad API-nyckel (hämtas dolt från Streamlit Secrets)
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except KeyError:
        api_key = None 

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
            st.caption("🔒 **Säker datahantering:** Inga CV:n sparas på våra servrar. Vår AI-leverantör raderar all data automatiskt efter 30 dagar och vi garanterar att kandidaternas uppgifter **aldrig** används för att träna några AI-modeller.")
            
        if st.button("🧠 Starta AI-Analys", type="primary"):
            if not api_key:
                st.error("⚠️ Ingen giltig Anthropic API-nyckel hittades i secrets!")
            elif not uppladdade_filer:
                st.warning("⚠️ Du måste ladda upp minst ett CV!")
            elif not annons_text.strip():
                st.warning("⚠️ Du måste klistra in en arbetsannons!")
            else:
                client = anthropic.Anthropic(api_key=api_key)
                
                # Den stenhårda och universella systeminstruktionen
                system_instruktion = """
                Du är en objektiv, extremt analytisk och fördomsfri AI-rekryterare. Ditt uppdrag är att revolutionera rekryteringsprocessen genom att leta efter *verklig* kompetens och relevant erfarenhet. Du är STENHÅRD och realistisk i din bedömning av ansvarsnivå och senioritet.

                DITT TILLVÄGAGÅNGSSÄTT:
                1. Analysera ansvarsnivå: Stirra dig inte blind på att en bransch matchar. Om annonsen söker en ledare, chef eller specialist, och kandidaten enbart har praktik eller instegsjobb, ska poängen dras ner kraftigt.
                2. Format-agnostisk: Ignorera CV:ts design.
                3. Översättbara färdigheter: Värdera praktisk problemlösning, men respektera hårda krav.

                STRIKT GDPR OCH ANONYMITET:
                Extrahera aldrig namn, kontaktuppgifter, ålder, kön eller länkar.

                BEDÖMNING OCH SCORING (0-100) - STRIKTA REGLER:
                - 0-30: Långt ifrån kraven.
                - 31-50: Uppfyller vissa grundkrav, men saknar rätt ansvarsnivå.
                - 51-75: En stark kandidat som uppfyller de flesta krav.
                - 76-90: En extremt kvalificerad kandidat som överträffar kraven.
                - 91-100: En perfekt, exceptionell matchning.
                """
                
                st.session_state.leaderboard = [] 
                st.session_state.kandidat_db = {}
                
                # Visuell feedback: Progress bar
                totalt_antal = len(uppladdade_filer)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for nummer, fil in enumerate(uppladdade_filer, 1):
                    anonymt_id = f"Kandidat #{nummer}"
                    
                    try:
                        # Extrahera text från PDF direkt i minnet (Zero Data Retention)
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(fil.getvalue()))
                        cv_text = ""
                        for page in pdf_reader.pages:
                            cv_text += page.extract_text() + "\n"
                        
                        # --- SÄKERHETSSPÄRR 1: Kontrollera tom text (t.ex. inskannad bild) ---
                        if not cv_text.strip():
                            raise ValueError("Kunde inte läsa någon text från filen. Är CV:t en inskannad bild?")
                            
                        # --- STEG 1: TVÄTTMASKINEN (ANONYMISERING) ---
                        status_text.markdown(f"**⏳ Tvättar och anonymiserar Kandidat {nummer} av {totalt_antal}...**")
                        
                        tvatt_prompt = f"""
                        Du är en strikt dataskydds-assistent. Din ENDA uppgift är att ta nedanstående CV-text och ta bort ALL personligt identifierbar information för att garantera en fördomsfri bedömning.
                        Byt ut alla namn, e-postadresser, telefonnummer, fysiska adresser, personnummer, ålder, LinkedIn-länkar och pronomen (han/hon) mot "[BORTTAGET]".
                        Ändra ingenting i den professionella eller operativa erfarenheten. Returnera enbart den tvättade texten.
                        
                        CV-TEXT:
                        {cv_text}
                        """
                        
                        tvatt_svar = client.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=2500,
                            messages=[
                                {"role": "user", "content": tvatt_prompt}
                            ]
                        )
                        
                        tvattad_cv_text = tvatt_svar.content[0].text
                        
                        # --- STEG 2: BEDÖMNINGEN (RANKING) ---
                        status_text.markdown(f"**⏳ Bedömer kompetens för Kandidat {nummer} av {totalt_antal}...**")
                        
                        bedomning_prompt = f"""
                        ARBETSANNONS:
                        {annons_text}
                        
                        KANDIDATENS TVÄTTADE CV:
                        {tvattad_cv_text}
                        
                        Din uppgift är att bedöma kandidaten. Du MÅSTE svara enbart med ett rent JSON-objekt exakt enligt denna struktur. Inkludera ingen annan text före eller efter JSON-koden.
                        {{
                            "score": [Heltal 0-100],
                            "ar_erfarenhet": [Heltal],
                            "utbildningsmatch": "[Kort text]",
                            "konkreta_resultat": "[Kort text]",
                            "nyckelkompetenser": "[Kort text]",
                            "saknade_krav": "[Kort text om gapet]",
                            "motivation": "[Din stenhårda motivering]"
                        }}
                        """

                        # Skicka till Claude
                        svar = client.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=1000,
                            system=system_instruktion,
                            messages=[
                                {"role": "user", "content": bedomning_prompt}
                            ]
                        )
                        
                        # Rensa och parsa JSON-svaret
                        raw_json = svar.content[0].text
                        if "```json" in raw_json:
                            raw_json = raw_json.split("```json")[1].split("```")[0]
                        elif "```" in raw_json:
                            raw_json = raw_json.split("```")[1].split("```")[0]
                            
                        resultat = json.loads(raw_json.strip())
                        
                        # Sparar originalfilen för senare nedladdning och koppling
                        resultat["original_namn"] = fil.name
                        resultat["fil_data"] = fil.getvalue() 
                        
                        st.session_state.kandidat_db[anonymt_id] = resultat
                        
                        # --- SÄKERHETSSPÄRR 2: Robust hämtning med .get() och strikt typsäkring ---
                        try:
                            # Tvingar värdet till ett äkta heltal (int) för att garantera rätt sortering
                            saker_score = int(resultat.get("score", 0))
                        except (ValueError, TypeError):
                            # Fångar upp om AI:n svarar med text (t.ex. "Åttiofem") eller None
                            saker_score = 0
                            
                        saker_kompetens = resultat.get("nyckelkompetenser", "Information saknas")
                        
                        st.session_state.leaderboard.append({
                            "Kandidat": anonymt_id, 
                            "Poäng": saker_score, 
                            "Nyckelkompetenser": saker_kompetens
                        })
                        
                    except Exception as e:
                        # --- SÄKERHETSSPÄRR 3: Tydlig felhantering utan krasch ---
                        st.error(f"⚠️ Systemet hoppade över Kandidat #{nummer} ({fil.name}) på grund av ett fel: {e}")
                    
                    progress_bar.progress(nummer / totalt_antal)
                    
                    # Farthållare för API:et (Vilar 5 sekunder för att undvika Rate Limits)
                    time.sleep(5)
                
                status_text.markdown("**✅ Alla kandidater färdiganalyserade och poängsatta helt anonymt!**")
                
                if st.session_state.leaderboard:
                    st.success("Analys klar! Byt till fliken 'Detaljer & Resultat' ovan för att se vinnarna.")

    # --- FLIK 2: LEADERBOARD OCH DETALJER ---
    with tab2:
        st.markdown("### 🏆 Leaderboard & Detaljerad AI-Analys")
        
        if not st.session_state.leaderboard:
            st.info("Ingen data laddad än. Kör en analys i Flik 1 först!")
        else:
            # --- EXPORT TILL EXCEL ---
            st.info("💡 **Tips:** Ladda ner hela analysen innan du stänger sidan för att spara din data lokalt.")
            
            excel_data = []
            for kand_id, data in st.session_state.kandidat_db.items():
                excel_data.append({
                    "Kandidat": kand_id,
                    "Poäng": data.get("score", 0),
                    "Års erfarenhet": data.get("ar_erfarenhet", "Saknas"),
                    "Utbildningsmatch": data.get("utbildningsmatch", "Saknas"),
                    "Nyckelkompetenser": data.get("nyckelkompetenser", "Saknas"),
                    "Konkreta resultat": data.get("konkreta_resultat", "Saknas"),
                    "Saknade krav": data.get("saknade_krav", "Saknas"),
                    "AI Motivering": data.get("motivation", "Saknas"),
                    "Källfil (Originaldokument)": data.get("original_namn", "")
                })
            
            df_export = pd.DataFrame(excel_data)
            df_export = df_export.sort_values(by="Poäng", ascending=False)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Resultat')
            excel_bytes = output.getvalue()
            
            st.download_button(
                label="📥 Ladda ner hela analysen (Excel)",
                data=excel_bytes,
                file_name="CV_Analys_Resultat.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.divider()

            # --- VISUELL PRESENTATION ---
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
                    # Säkerställer att vi visar ett värde även om något blev fel vid extrahering
                    st.metric(label="AI Matchningspoäng", value=f"{data.get('score', 0)} / 100")
                    
                    st.markdown("#### 📊 Erfarenhet & Utbildning")
                    st.write(f"**Relevanta år i branschen:** {data.get('ar_erfarenhet', 'Saknas')} år")
                    st.write(f"**Utbildning:** {data.get('utbildningsmatch', 'Saknas')}")
                    
                    st.markdown("#### 🚀 Konkreta resultat & Projekt")
                    st.write(data.get('konkreta_resultat', 'Saknas'))
                    
                    st.markdown("#### 🔑 Nyckelkompetenser & Språk")
                    st.write(data.get('nyckelkompetenser', 'Saknas'))
                    
                    st.markdown("#### ⚠️ Saknade krav (Gaps)")
                    st.warning(data.get('saknade_krav', 'Saknas'))
                    
                    st.markdown("#### 💡 AI:ns Motivering")
                    st.info(data.get('motivation', 'Saknas'))
                    
                    st.divider()
                    st.markdown("#### 🔓 Avslöja & Kontakta")
                    st.write("När du är redo att gå vidare med kandidaten kan du ladda ner originaldokumentet här.")
                    st.download_button(
                        label=f"📥 Ladda ner original-CV",
                        data=data['fil_data'],
                        file_name=data['original_namn'],
                        mime="application/pdf",
                        type="secondary"
                    )import streamlit as st
import pandas as pd
import json
import time
import io
import PyPDF2
import anthropic

# 1. Design och inställningar för webbsidan (Måste vara överst)
st.set_page_config(page_title="CV-Matchning Pilot", page_icon="🚀", layout="wide")

# --- LÖSENORDSSKYDD START ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "pilot2026": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Ange lösenord för Early Access:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Ange lösenord för Early Access:", type="password", on_change=password_entered, key="password")
        st.error("Fel lösenord. Försök igen.")
        return False
    return True
# --- LÖSENORDSSKYDD SLUT ---

# Kontrollera lösenord innan resten av sidan visas
if check_password():
    st.title("🚀 Anonym CV-Matchning Pilot")

    # 2. Inbakad API-nyckel (hämtas dolt från Streamlit Secrets)
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except KeyError:
        api_key = None 

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
            st.caption("🔒 **Säker datahantering:** Inga CV:n sparas på våra servrar. Vår AI-leverantör raderar all data automatiskt efter 30 dagar och vi garanterar att kandidaternas uppgifter **aldrig** används för att träna några AI-modeller.")
            
        if st.button("🧠 Starta AI-Analys", type="primary"):
            if not api_key:
                st.error("⚠️ Ingen giltig Anthropic API-nyckel hittades i secrets!")
            elif not uppladdade_filer:
                st.warning("⚠️ Du måste ladda upp minst ett CV!")
            elif not annons_text.strip():
                st.warning("⚠️ Du måste klistra in en arbetsannons!")
            else:
                client = anthropic.Anthropic(api_key=api_key)
                
                # Den stenhårda och universella systeminstruktionen
                system_instruktion = """
                Du är en objektiv, extremt analytisk och fördomsfri AI-rekryterare. Ditt uppdrag är att revolutionera rekryteringsprocessen genom att leta efter *verklig* kompetens och relevant erfarenhet. Du är STENHÅRD och realistisk i din bedömning av ansvarsnivå och senioritet.

                DITT TILLVÄGAGÅNGSSÄTT:
                1. Analysera ansvarsnivå: Stirra dig inte blind på att en bransch matchar. Om annonsen söker en ledare, chef eller specialist, och kandidaten enbart har praktik eller instegsjobb, ska poängen dras ner kraftigt.
                2. Format-agnostisk: Ignorera CV:ts design.
                3. Översättbara färdigheter: Värdera praktisk problemlösning, men respektera hårda krav.

                STRIKT GDPR OCH ANONYMITET:
                Extrahera aldrig namn, kontaktuppgifter, ålder, kön eller länkar.

                BEDÖMNING OCH SCORING (0-100) - STRIKTA REGLER:
                - 0-30: Långt ifrån kraven.
                - 31-50: Uppfyller vissa grundkrav, men saknar rätt ansvarsnivå.
                - 51-75: En stark kandidat som uppfyller de flesta krav.
                - 76-90: En extremt kvalificerad kandidat som överträffar kraven.
                - 91-100: En perfekt, exceptionell matchning.
                """
                
                st.session_state.leaderboard = [] 
                st.session_state.kandidat_db = {}
                
                # Visuell feedback: Progress bar
                totalt_antal = len(uppladdade_filer)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for nummer, fil in enumerate(uppladdade_filer, 1):
                    status_text.markdown(f"**⏳ Analyserar kandidat {nummer} av {totalt_antal}...**")
                    anonymt_id = f"Kandidat #{nummer}"
                    
                    try:
                        # Extrahera text från PDF direkt i minnet (Zero Data Retention)
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(fil.getvalue()))
                        cv_text = ""
                        for page in pdf_reader.pages:
                            cv_text += page.extract_text() + "\n"
                            
                        prompt = f"""
                        ARBETSANNONS:
                        {annons_text}
                        
                        KANDIDATENS CV:
                        {cv_text}
                        
                        Din uppgift är att bedöma kandidaten. Du MÅSTE svara enbart med ett rent JSON-objekt exakt enligt denna struktur. Inkludera ingen annan text före eller efter JSON-koden.
                        {{
                            "score": [Heltal 0-100],
                            "ar_erfarenhet": [Heltal],
                            "utbildningsmatch": "[Kort text]",
                            "konkreta_resultat": "[Kort text]",
                            "nyckelkompetenser": "[Kort text]",
                            "saknade_krav": "[Kort text om gapet]",
                            "motivation": "[Din stenhårda motivering]"
                        }}
                        """

                        # Skicka till Claude Sonnet 5
                        svar = client.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=1000,
                            system=system_instruktion,
                            messages=[
                                {"role": "user", "content": prompt}
                            ]
                        )
                        
                        # Rensa och parsa JSON-svaret
                        raw_json = svar.content[0].text
                        if "```json" in raw_json:
                            raw_json = raw_json.split("```json")[1].split("```")[0]
                        elif "```" in raw_json:
                            raw_json = raw_json.split("```")[1].split("```")[0]
                            
                        resultat = json.loads(raw_json.strip())
                        
                        # Sparar originalfilen för senare nedladdning och koppling
                        resultat["original_namn"] = fil.name
                        resultat["fil_data"] = fil.getvalue() 
                        
                        st.session_state.kandidat_db[anonymt_id] = resultat
                        st.session_state.leaderboard.append({"Kandidat": anonymt_id, "Poäng": resultat["score"], "Nyckelkompetenser": resultat["nyckelkompetenser"]})
                        
                    except Exception as e:
                        st.error(f"Ett fel uppstod med Kandidat #{nummer}. Felmeddelande: {e}")
                    
                    progress_bar.progress(nummer / totalt_antal)
                    
                    # Farthållare för API:et (Vilar 5 sekunder för att aldrig slå i Tier 1 Rate Limits)
                    time.sleep(5)
                
                status_text.markdown("**✅ Alla kandidater färdiganalyserade!**")
                
                if st.session_state.leaderboard:
                    st.success("Analys klar! Byt till fliken 'Detaljer & Resultat' ovan för att se vinnarna.")

    # --- FLIK 2: LEADERBOARD OCH DETALJER ---
    with tab2:
        st.markdown("### 🏆 Leaderboard & Detaljerad AI-Analys")
        
        if not st.session_state.leaderboard:
            st.info("Ingen data laddad än. Kör en analys i Flik 1 först!")
        else:
            # --- EXPORT TILL EXCEL ---
            st.info("💡 **Tips:** Ladda ner hela analysen innan du stänger sidan för att spara din data lokalt.")
            
            excel_data = []
            for kand_id, data in st.session_state.kandidat_db.items():
                excel_data.append({
                    "Kandidat": kand_id,
                    "Poäng": data.get("score", ""),
                    "Års erfarenhet": data.get("ar_erfarenhet", ""),
                    "Utbildningsmatch": data.get("utbildningsmatch", ""),
                    "Nyckelkompetenser": data.get("nyckelkompetenser", ""),
                    "Konkreta resultat": data.get("konkreta_resultat", ""),
                    "Saknade krav": data.get("saknade_krav", ""),
                    "AI Motivering": data.get("motivation", ""),
                    "Källfil (Originaldokument)": data.get("original_namn", "")
                })
            
            df_export = pd.DataFrame(excel_data)
            df_export = df_export.sort_values(by="Poäng", ascending=False)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Resultat')
            excel_bytes = output.getvalue()
            
            st.download_button(
                label="📥 Ladda ner hela analysen (Excel)",
                data=excel_bytes,
                file_name="CV_Analys_Resultat.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.divider()

            # --- VISUELL PRESENTATION ---
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
                    
                    st.divider()
                    st.markdown("#### 🔓 Avslöja & Kontakta")
                    st.write("När du är redo att gå vidare med kandidaten kan du ladda ner originaldokumentet här.")
                    st.download_button(
                        label=f"📥 Ladda ner original-CV",
                        data=data['fil_data'],
                        file_name=data['original_namn'],
                        mime="application/pdf",
                        type="secondary"
                    )
