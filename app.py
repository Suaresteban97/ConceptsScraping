from flask import Flask, request, jsonify
import requests
import os
import pdfplumber
from dotenv import load_dotenv
import re
import json

load_dotenv()
app = Flask(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = os.getenv("DEEPSEEK_API_KEY")

TXT_DIR = "txts"
JSON_DIR = "jsons"
for d in (TXT_DIR, JSON_DIR):
    os.makedirs(d, exist_ok=True)


def extract_text_from_pdf(file_stream):
    """Extrae todo el texto plano del PDF, sin imágenes ni formato."""
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def find_relevant_text(text):
    """Filtra el texto para encontrar solo los fragmentos con los numerales relevantes."""
    relevant_sections = []

    # Sección 3.2 VISITA TÉCNICA hasta antes de 3.3 o 4.1
    visita = re.search(r"(3\.2[\s\S]*?)(?=3\.3|4\.1|$)", text)
    if visita:
        relevant_sections.append(visita.group(1))

    # Sección 4.1 ALMACENAMIENTO Y DISTRIBUCIÓN... hasta antes de 4.1.1.1 OBSERVACIONES DE LA VISITA
    pozos = re.search(
        r"(4\.1\s+ALMACENAMIENTO[\s\S]*?)(?=\n4\.\d|$)",
        text
    )
    if pozos:
        relevant_sections.append(pozos.group(1))

    # Sección 4.1.3 ANTECEDENTES hasta antes de 4.1.4
    antecedentes = re.search(r"(4\.1\.3[\s\S]*?)(?=4\.1\.4|$)", text)
    if antecedentes:
        relevant_sections.append(antecedentes.group(1))

    return "\n".join(relevant_sections)


@app.route('/process-pdf', methods=['POST'])
def process_pdf_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Archivo PDF inválido"}), 400

    filename_base = os.path.splitext(file.filename)[0]
    txt_path = os.path.join(TXT_DIR, f"{filename_base}.txt")
    json_path = os.path.join(JSON_DIR, f"{filename_base}.json")

    # Extraer o cargar fragmento relevante
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            relevant_text = f.read()
    else:
        raw_text = extract_text_from_pdf(file.stream)
        if not raw_text:
            return jsonify({"error": "No se pudo extraer texto del PDF"}), 400
        relevant_text = find_relevant_text(raw_text)
        if not relevant_text:
            return jsonify({"error": "No se encontró información relevante en el PDF"}), 400
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(relevant_text)

    # Construir prompt para DeepSeek
    prompt = f"""
    Analiza el siguiente texto completo y devuelve SOLO un JSON con esta estructura:

    {{
    "visita_tecnica_fecha": "YYYY-MM-DD[, YYYY-MM-DD]", 
    "pozos_afectados": "PZ1, PZ2, PO-1", 
    "antecedentes": "Concepto técnico 599 del 2014, 2014ER216333"
    }}

    REGLAS:
    1. En el numeral 3.2 (VISITA TÉCNICA), identifica las fechas de la visita en formato "YYYY-MM-DD". Si hay más de una, sepáralas por coma y espacio.
    2. En el numeral 4.1, bajo el subtítulo "Ubicación de los pozos que presentan producto en fase libre, iridisciencia y/o olor", extrae solo los nombres de los pozos (ejemplo: PO-1, PZ1), en un string separado por coma.
    3. En el numeral 4.1.3, extrae antecedentes relacionados con requerimientos, conceptos técnicos, autos o radicados mencionados como "se solicitó", "se requirió", "requerimiento", etc. Incluye identificador y fecha si existe.

    NO incluyas explicación ni texto adicional, solo el JSON.

    Texto relevante:
    {relevant_text}
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }

    try:
        # Enviar solicitud a la API
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        respuesta = response.json()
        contenido = respuesta["choices"][0]["message"]["content"]

        # Limpiar el bloque de código con triple backticks
        contenido_limpio = re.sub(r"^```json\s*|\s*```$", "", contenido.strip(), flags=re.MULTILINE)
        result_json = json.loads(contenido_limpio)

        # Guardar JSON
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(result_json, jf, ensure_ascii=False, indent=2)

        return jsonify(result_json)

    except Exception as e:
        return jsonify({"error": str(e), "response": response.text}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
