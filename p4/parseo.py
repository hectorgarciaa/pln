from conf import FRONTMATTER_IDS
from pathlib import Path
from bs4 import BeautifulSoup

# 2. PARSING DEL HTML

def cargar_html(ruta: Path) -> BeautifulSoup:
    """Lee el archivo HTML y devuelve un objeto BeautifulSoup."""
    with open(ruta, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def extraer_capitulos(soup: BeautifulSoup) -> list[dict]:
    """
    Segmenta el libro en capítulos usando las etiquetas <h3> con <a name="...">.
    Ignora front-matter y licencia de Gutenberg.
    Devuelve una lista de párrafos por capítulo (no texto concatenado).
    """
    secciones = []
    for h3 in soup.find_all("h3"):
        ancla = h3.find("a", attrs={"name": True})
        if ancla:
            secciones.append({
                "id": ancla["name"],
                "titulo": h3.get_text(strip=True),
                "elemento": h3,
            })

    capitulos = []
    for sec in secciones:
        if sec["id"] in FRONTMATTER_IDS:
            continue

        parrafos = []
        sibling = sec["elemento"].find_next_sibling()
        while sibling:
            if sibling.name == "h3" and sibling.find("a", attrs={"name": True}):
                break
            if sibling.name == "h2" and sibling.find("a", attrs={"name": True}):
                break
            texto = sibling.get_text(" ", strip=True)
            if texto:
                parrafos.append(texto)
            sibling = sibling.find_next_sibling()

        if not parrafos:
            continue

        parte = "I" if sec["id"].startswith("1_") else "II"
        capitulos.append({
            "id": sec["id"],
            "parte": parte,
            "titulo": sec["titulo"],
            "parrafos": parrafos,
        })

    return capitulos


def extraer_chunks(capitulos: list[dict], tam_ventana: int = 3, solapamiento: int = 1) -> list[dict]:
    """
    Genera chunks con ventana deslizante a partir de los párrafos de cada capítulo.

    Ejemplo con tam_ventana=3, solapamiento=1:
        párrafos: [p1, p2, p3, p4, p5]
        chunks:   [p1+p2+p3], [p2+p3+p4], [p3+p4+p5]

    Cada chunk incluye el título del capítulo al que pertenece.
    """
    paso = tam_ventana - solapamiento  # cuántos párrafos avanzamos en cada paso
    chunks = []

    for cap in capitulos:
        parrafos = cap["parrafos"]
        n = len(parrafos)

        if n == 0:
            continue

        # Si el capítulo es más corto que la ventana, lo tomamos entero como un chunk
        if n <= tam_ventana:
            chunks.append({
                "cap_id": cap["id"],
                "parte": cap["parte"],
                "titulo": cap["titulo"],
                "texto": cap["titulo"] + " " + " ".join(parrafos),
                "chunk_idx": 0,
            })
            continue

        for inicio in range(0, n - tam_ventana + 1, paso):
            ventana = parrafos[inicio: inicio + tam_ventana]
            chunks.append({
                "cap_id": cap["id"],
                "parte": cap["parte"],
                "titulo": cap["titulo"],
                "texto": cap["titulo"] + " " + " ".join(ventana),
                "chunk_idx": inicio // paso,
            })

        # Si quedaron párrafos finales que no forman una ventana completa,
        # los añadimos como el último chunk (evita perder el final del capítulo)
        ultimo_inicio = ((n - tam_ventana) // paso) * paso + paso
        if ultimo_inicio < n:
            ventana = parrafos[ultimo_inicio:]
            chunks.append({
                "cap_id": cap["id"],
                "parte": cap["parte"],
                "titulo": cap["titulo"],
                "texto": cap["titulo"] + " " + " ".join(ventana),
                "chunk_idx": -1,  # marca de "último fragmento residual"
            })

    return chunks