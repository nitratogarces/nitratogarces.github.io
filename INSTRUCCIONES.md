# Pauta de Nitrato

La tarea programada lee este archivo en cada ejecución. Para cambiar el
criterio editorial, basta con cambiar este texto.

## 1. ¿Toca bobina hoy?

- La tarea se ejecuta a diario, pero Nitrato publica **cada dos días**.
- Mira la fecha de la bobina más reciente en `bobinas_json/` (el nombre del
  archivo es su fecha). Si han pasado **menos de dos días** desde ella (fecha de
  hoy en Madrid), no hagas nada más: hoy no toca.
- La bobina nueva lleva el número siguiente al último publicado.

## 2. Sección (rotación fija)

Las secciones se alternan siempre en este orden, según el número de bobina:

| Bobina | Sección | Clave |
|---|---|---|
| 1, 5, 9… | El proceso | `proceso` |
| 2, 6, 10… | El archivo vivo | `archivo` |
| 3, 7, 11… | El error | `error` |
| 4, 8, 12… | La versión que no viste | `version` |

`python3 generate.py` indica al final qué número y qué sección tocan.

- **El proceso.** Cómo se hizo algo concreto de una película o serie: la luz,
  el sonido, el montaje, el casting, el diseño de producción, el doblaje, los
  efectos, la música. El oficio contado desde dentro, con su gente.
- **El archivo vivo.** Una obra estrenada hace exactamente 10, 25, 50, 75 o 100
  años (o en un aniversario cercano a la fecha de la bobina). Qué condiciones
  industriales, técnicas y humanas la hicieron posible, y qué cambió después.
- **El error.** Lo que salió mal: rodajes abandonados, presupuestos desbordados,
  intérpretes sustituidos, montajes rehechos, estrenos fallidos, copias
  perdidas. El fracaso como parte del funcionamiento de la industria.
- **La versión que no viste.** Montajes del director, versiones distintas según
  país o mercado, finales alternativos, escenas cortadas, cambios impuestos por
  la distribución o la censura.

Cine y series, de cualquier país y época. Mezclar a lo largo del tiempo cine
español, europeo, estadounidense y de otros lugares, y piezas clásicas con
producciones recientes. No repetir una obra ya tratada en `bobinas_json/`.

## 3. Elección del tema

Buscar un caso con **una pieza escondida**: un dato poco conocido en los medios
especializados que cambia cómo se mira la obra. El criterio no es la fama de la
película, sino que exista una historia verificable que el lector no conozca.

## 4. Investigación

- Usar fuentes fiables y abrirlas: entrevistas con el equipo, libros y
  artículos de historia del cine, archivos de filmotecas, publicaciones de
  distribuidoras, prensa especializada (por ejemplo Criterion, BFI, American
  Cinematographer, Academia de Cine, Filmoteca Española, Caimán, Fotogramas,
  Variety, The Hollywood Reporter), Wikipedia solo como punto de partida.
- **Nada inventado.** Ni anécdotas, ni diálogos, ni escenas de rodaje
  imaginadas, ni cifras aproximadas presentadas como exactas. Si un dato no se
  ha podido comprobar en al menos una fuente fiable, no entra.
- Si dos fuentes discrepan, se dice. Si una relación entre hechos es una
  coincidencia y no una causa, se dice que es una coincidencia.
- Lo que haya dicho alguien del equipo se cuenta en estilo indirecto. Como
  mucho una cita literal breve por pieza.

## 5. Escritura

- **Una pieza por bobina**, de **1.100 a 1.800 palabras**.
- **Textura narrativa.** Empezar por una imagen, un objeto, un momento o un dato
  concreto que sumerja al lector, no por una presentación. Construir la pieza
  como un relato que avanza y se revela, con cortes de escena (`***` como
  párrafo propio) donde cambie el ángulo.
- **Audaz y poco habitual.** Buscar el ángulo que los medios del sector no
  suelen tomar: la persona que no sale en los créditos importantes, la
  condición material que lo explica todo, la coincidencia que nadie ha
  señalado. Terminar con una imagen o una idea que abra, no con un resumen.
- **No es crítica.** No se valora si la obra es buena o mala, no se puntúa, no
  se recomienda verla.
- **Sin compromiso ideológico.** No se toma partido en cuestiones políticas
  actuales ni se juzga a personas por sus ideas. El contexto histórico
  (censura, guerra, régimen) se describe como hecho, sin editorializar.
- Firmado por Miguel Garcés. Prosa en español de España, cuidada, sin
  subtítulos dentro del texto, sin listas, sin emojis.
- Sin mencionar que el texto se ha preparado de forma automática.

## 6. Datos de la pieza

Guardar en `bobinas_json/AAAA-MM-DD.json` con la forma que describe la cabecera
de `generate.py`:

- **title:** titular evocador y concreto. **dek:** una o dos frases.
- **ficha:** 4 a 6 casillas sobre la obra (Obra, Año, Dirección, y las que
  sean pertinentes al tema: Fotografía, Montaje, Productora, País, Plataforma…).
- **sources:** todas las fuentes abiertas de las que salen los datos, con
  título y enlace.

## 7. Generación y publicación

1. `python3 generate.py` y comprobar que no da error.
2. Revisar que `index.html` muestra la pieza nueva.
3. Autor de los commits: `Miguel Garcés` con el correo `noreply` de GitHub de
   la cuenta nitrato-garces. Nunca un correo personal.
4. Mensaje de commit: `Bobina N — Título`. Push a `main`.
