# Nitrato

Lo que una película fue antes de ser la película. Una pieza nueva cada dos días,
por Miguel Garcés, alternando cuatro secciones: El proceso, El archivo vivo,
El error y La versión que no viste.

Web estática en GitHub Pages: https://nitrato-garces.github.io/nitrato/

## Estructura

```
index.html            portada: la última bobina y la lista de las anteriores
archivo.html          todas las bobinas
piezas/               una página por bobina
bobinas_json/         el contenido de cada bobina (fuente de todo el sitio)
assets/style.css      diseño
assets/script.js      botón de copiar enlace
generate.py           reconstruye el sitio a partir de bobinas_json/
INSTRUCCIONES.md      pauta editorial que sigue la tarea programada
```

Para corregir una pieza publicada: editar su JSON en `bobinas_json/`, ejecutar
`python3 generate.py` y subir los cambios.
