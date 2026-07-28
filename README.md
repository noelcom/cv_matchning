# 🚀 Anonymous CV Matching

**(Note: The current iteration of the application UI is in Swedish)**

A smart and unbiased recruitment tool built with Python and Google Gemini AI. The system analyzes candidates' resumes against a specific job description, completely ignoring names, gender, age, or background.

🔴 **[Try the app live here!](https://cvmatchning.streamlit.app/)**

## ✨ Features
* **100% Anonymity:** Automatically hides names and filenames in the user interface to guarantee an objective assessment.
* **In-Depth Analysis:** Goes beyond simple keyword matching to evaluate actual levels of responsibility, concrete achievements, and identify missing requirements (gaps).
* **"Bring Your Own Key":** For maximum data privacy, the user provides their own Gemini API key to run the analysis.
* **Reveal Candidate:** Once the right competency profile is identified, the recruiter can download the original PDF to reach out and make contact.

## 🔒 Privacy by Design & Data Security
Because this tool handles personal data, it is built with a strict security architecture:
* **Zero Permanent Storage:** Resumes are processed exclusively in the server's temporary RAM (`st.session_state`).
* **Programmatic Cleanup:** The local temporary folder is automatically wiped via `shutil.rmtree` the moment the execution finishes.
* **Forced API Deletion:** An explicit API call (`client.files.delete()`) is dispatched to Google, ensuring the document is deleted from their servers the millisecond the AI concludes its analysis.

## 🛠️ Tech Stack
* **Language:** Python
* **Frontend/Backend:** Streamlit
* **AI Engine:** Google Gemini 2.5 Flash (via the latest `google-genai` SDK)
* **Data Handling:** Pandas, JSON (utilizing strict response schemas)

## 💡 About the Project
This project is an experimental Proof of Concept (PoC) created to investigate the problems surrounding resume screening and bias within current HR processes. The objective is to explore how data-driven analysis can contribute to a fairer, competency-based selection process by completely ignoring the visual format of a resume and focusing strictly on raw data and actual results.
