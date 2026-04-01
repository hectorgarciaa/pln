from conf import NLP_MODEL, STOPWORDS_ES
import re
import spacy

# 3. PREPROCESAMIENTO
def cargar_spacy(modelo: str = NLP_MODEL):
    nlp = spacy.load(modelo, disable=["ner", "parser"])
    return nlp


def preprocesar_texto(texto: str, nlp) -> str:
    """Limpia, lematiza y elimina stopwords."""
    texto = texto.lower()
    texto = re.sub(r"[^\w\sáéíóúüñ]", " ", texto)
    texto = re.sub(r"\d+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    doc = nlp(texto)
    tokens = [
        token.lemma_.lower().strip() for token in doc
            if token.lemma_.lower().strip()
            and token.lemma_.lower().strip() not in STOPWORDS_ES
            and token.pos_ not in ("PUNCT", "SPACE", "X")
            and len(token.lemma_.lower().strip()) > 1
            and not token.lemma_.isdigit()
            and not token.is_stop
    ]
    return " ".join(tokens)