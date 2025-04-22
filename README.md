# 🧠 ConceptsScraping

Este proyecto es una API en Flask que recibe archivos PDF, extrae texto relevante según numerales específicos, y utiliza la API de **DeepSeek** para convertir ese texto en un resumen estructurado en JSON.

---

## 🚀 ¿Qué hace?

1. Recibe un archivo `.pdf` mediante una petición `POST`.
2. Extrae el texto plano del PDF.
3. Filtra solo secciones específicas del documento:
   - **3.2 VISITA TÉCNICA**
   - **4.1 ALMACENAMIENTO Y DISTRIBUCIÓN**
   - **4.1.3 ANTECEDENTES**
4. Envía ese texto a DeepSeek con instrucciones específicas.
5. Devuelve un JSON con:
   - Fechas de visita técnica.
   - Pozos afectados.
   - Antecedentes.

---

## 🧱 Estructura del JSON de respuesta

```json
{
  "visita_tecnica_fecha": "YYYY-MM-DD[, YYYY-MM-DD]",
  "pozos_afectados": "PZ1, PZ2, PO-1",
  "antecedentes": "Concepto técnico 599 del 2014, 2014ER216333"
}
