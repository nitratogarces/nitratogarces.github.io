# Reels de Fuera de Plano

Plantilla para convertir las láminas de un carrusel de Fuera de Plano en un reel vertical (1080×1920, 24 fps, sin voz) con la misma estética: negro cálido, marco fino dorado con esquinas en escuadra, versalitas espaciadas en oro, Spectral (redonda y cursiva) en crema, palabras destacadas en cursiva dorada.

Usa las fuentes de `reels/fuentes/`. El material de las películas no se sube al repositorio.

```
python3 reels/fuera_de_plano/fdp_reel.py guion.json            # vídeo completo
python3 reels/fuera_de_plano/fdp_reel.py guion.json 3 9.5 20   # fotogramas de prueba (PNG)
```

## Dos formatos

- **`"formato": "ventana"`** (por defecto). Cada escena es una lámina: rótulo de sección, imagen en una ventana enmarcada y texto debajo. Es el formato para material de baja resolución o horizontal, porque la imagen apenas se amplía.
- **`"formato": "completo"`**. La primera escena es la portada (en ventana) y el resto lleva la imagen a pantalla completa, con el texto fundido encima sobre una sombra que sube desde abajo. Solo si el material tiene resolución suficiente (720p o más, idealmente 1080p, o material vertical).

Una escena puede forzar el otro formato con `"formato"` propio. En pantalla completa, un medio con `"alto": 1020` ocupa solo la franja superior a todo el ancho (útil si lo importante de la imagen es un texto o un plano muy ancho).

## Opciones generales

| Clave | Qué hace |
|---|---|
| `salida` | Nombre del MP4. |
| `formato` | `ventana` o `completo`. |
| `numerar` | `true` añade el contador «01 / 07» al pie. Por defecto, sin numerar. |
| `firma_pie` | En formato ventana, «Miguel Garcés» pequeño al pie de cada lámina (por defecto sí). En la portada aparece siempre. |

El reel **no termina con la pregunta** de la última lámina del carrusel ni con la firma «Miguel Garcés · Actor»: cierra con una imagen y el rótulo «Fuera de plano», y funde a negro.

## Escenas

Cada escena lleva `dur` (segundos) y:

| Clave | Qué hace |
|---|---|
| `seccion` | Rótulo en versalitas doradas con filete (p. ej. «La cita»). `filete: true` pone solo el filete. |
| `titulo` | Título grande en cursiva (portada). |
| `medios` | Lista de imágenes o vídeos; `en` indica el segundo de la escena en que entra cada uno. |
| `ventana` | `{"alto": 440}`: alto de la ventana de imagen (formato ventana). |
| `orden` | Orden de los bloques: `titulo`, `ventana`, `numero`, `textos` (o un número de píxeles de espacio). |
| `numero`, `numero_pie` | Cifra grande dorada y su leyenda en versalitas (p. ej. «10» / «Minutos hasta la primera frase»). |
| `textos` | `{estilo, texto, desde, tam, color, espacio}`. `*así*` pone el texto en cursiva dorada. |
| `reticula` | Retícula fina en la mitad derecha, como la lámina de portada. |
| `fundido`, `sombra` | (Pantalla completa) dónde empieza y cuán oscura es la sombra bajo el texto. |

Estilos: `titulo`, `cuerpo`, `suave`, `cursiva`, `dialogo`, `numero`. Colores: `crema`, `oro`, `gris`.

Medios:

- Imagen: `{"imagen": "material/x.jpg", "zoom": [1, 1.06], "foco_x": 0.5, "foco_y": 0.3}`.
- Vídeo: `{"video": "material/x.mp4", "desde": 84.2, "lento": 1.5, "zoom": [1, 1.08], "foco_x": 0.6}` o, para unir tramos, `"tramos": [[230.8, 232.5], [235.85, 237.45]]`.

`zoom`, `foco_x` y `foco_y` aceptan un valor fijo o `[inicio, fin]` para un movimiento lento.
