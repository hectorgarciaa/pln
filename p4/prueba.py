from conf import HTML_PATH
from parseo import cargar_html, extraer_capitulos

quijote = cargar_html(HTML_PATH)
capitulos = extraer_capitulos(quijote)

for cap in capitulos:
    print(len(cap["texto"]))