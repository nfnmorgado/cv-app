import streamlit as st
from docx import Document
import pdfplumber
import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("CV Auto Formatter")

# Uploads

cv_file = st.file_uploader("Upload CV (PDF ou DOCX)")
template_file = st.file_uploader("Upload Template DOCX")

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
        return text
    else:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])

if st.button("Gerar CV"):
    if cv_file and template_file:
        with st.spinner("A processar..."):
            # 1. Extrair texto
            cv_text = extract_text(cv_file)
            # 2. IA parsing
            prompt = f"""
            Extrai:
            - initials
            - experience
            - availability
            - english_level
            - country
            - skills (separados por ;)
            - summary
            - work_experience (company, position, start, end, description)

            CV:
            {cv_text}

            Responde em JSON.
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.choices[0].message.content

import re
match = re.search(r'{.*}', raw, re.DOTALL)

if match:
    json_str = match.group(0)
    data = json.loads(json_str)
else:
    st.error("Erro ao interpretar resposta da AI")
    st.write(raw)
return

            # 3. Preencher template
            doc = Document(template_file)

            replacements = {
                "[Candidates First and Last Initials]": data.get("initials", ""),
                "[Experience]": data.get("experience", ""),
                "[Availability]": data.get("availability", ""),
                "[English]": data.get("english_level", ""),
                "[Country]": data.get("country", ""),
                "[Skills]": data.get("skills", ""),
                "[Summary]": data.get("summary", "")
            }

        for p in doc.paragraphs:
            for k, v in replacements.items():
                if k in p.text:
                    p.text = p.text.replace(k, str(v))

        # Work experience (primeiro)
        if data.get("work_experience"):
            exp = data["work_experience"][0]
            for p in doc.paragraphs:
                if "[Company Name]" in p.text:
                    p.text = f"{exp['company']} - {exp['position']}"
                if "[start date" in p.text:
                    p.text = f"{exp['start']} to {exp['end']}"
                if "[Description]" in p.text:
                    p.text = exp['description']

        output = "output.docx"
        doc.save(output)

        with open(output, "rb") as f:
            st.download_button("Download CV", f, file_name="CV_final.docx")

else:
    st.error("Faz upload dos dois ficheiros")
