# Reels de Nitrato

Plantilla para convertir una bobina de Nitrato en un reel vertical (1080×1920, 24 fps) con la estética de la web: película de nitrato con bordes perforados, grano, parpadeo, rayas y polvo, tipografías Big Shoulders y Spectral, y acento ámbar.

Esta carpeta no forma parte de la web ni la toca `generate.py`. Los reels se hacen a petición, nunca de forma automática.

## Cómo se hace un reel

1. Leer la bobina en `bobinas_json/AAAA-MM-DD.json` y elegir 6–8 momentos: gancho, ficha, 3–5 ideas y la frase de cierre del artículo.
2. Pedir a Miguel el material: fotos, carteles y fragmentos de vídeo de 3 a 10 s para cada escena. El material de las películas **no se sube a este repositorio**. Si no hay material, se hace la versión de solo texto.
3. Escribir un guion JSON (ver `ejemplos/`) en una carpeta de trabajo, con el material en `material/` junto a él.
4. Probar fotogramas sueltos y después generar el vídeo:

```
python3 reels/nitrato_reel.py guion.json 3 9.5 20   # PNG de prueba en esos segundos
python3 reels/nitrato_reel.py guion.json            # vídeo completo
```

El vídeo sale sin música (lleva una pista muda): la música se elige en Instagram al publicar.

## El guion JSON

```json
{
  "salida": "Nitrato - Bobina N - reel.mp4",
  "escenas": [ { ... }, { "tipo": "cierre" } ]
}
```

Cada escena lleva `dur` (segundos) y, según el caso:

| Clave | Qué hace |
|---|---|
| `fondo` | Material de fondo. Sin `fondo`, la escena es solo texto sobre la película. |
| `textos` | Lista de textos `{estilo, texto, desde, tam, color}`. Las palabras entre `*asteriscos*` van en ámbar. |
| `antetitulo` | Línea pequeña en ámbar encima del texto (p. ej. `NITRATO · BOBINA 15`). |
| `pos` | Altura del texto: `arriba`, `centro`, `abajo` o un número de píxeles. |
| `alto_sombra`, `sombra` | Tamaño e intensidad de la banda oscura que hace legible el texto sobre la imagen. |
| `desenfoque` | `[inicio, duración]`: la imagen y el primer texto se desenfocan (pérdida de visión). Los textos siguientes van nítidos en `pos2`. |
| `tipo: "ficha"` | Ficha técnica: `titulo` y `filas` `[["Dirección", "…"], …]`. |
| `tipo: "cierre"` | Cartela final de Nitrato con la web y «Enlace en la bio». |

Estilos de texto: `titular` (mayúsculas, gruesa), `grande`, `cuerpo`, `cursiva`, `destacado` (cursiva ámbar), `cita` (cursiva con filete ámbar), `pie`. Colores: `tinta`, `ambar`, `gris`.

`fondo` admite:

- Imagen: `{"imagen": "material/x.jpg", "modo": "vertical" | "enmarcado", "zoom": [1, 1.06], "centro_x": [0.25, 0.5], "centro_y": 0.3, "ancho": 900, "y": 850}`. `vertical` llena la pantalla; `enmarcado` encaja la imagen a un ancho sobre un fondo desenfocado (para carteles y fotos pequeñas).
- Vídeo: `{"video": "material/x.mp4", "desde": 12.5, "modo": "vertical" | "enmarcado", "lento": 1.6, "centro_x": 0.5, "recorte": "crop=364:646:178:330"}`. `lento` ralentiza (2 = mitad de velocidad); `recorte` quita bandas negras antes de encuadrar. Para material horizontal de baja resolución funciona mejor `enmarcado`.

## Criterios

- Gancho en los primeros 3–5 segundos; 40–55 s en total.
- Texto en pantalla corto: se ve sin sonido.
- No cubrir los ojos de los rostros con el texto; usar `pos` para moverlo.
- Las frases atribuidas se marcan como tales, igual que en el artículo.
- Música: sugerir 2–3 piezas reales acordes al tono, avisando de que hay que comprobar si están en la biblioteca de Instagram.
