# Programación Lineal - Método de la Gran M

## Proyecto Final de Optimización

### Samuel Puerta, Juan Pablo Valencia, Guillermo Mejía.

App web con interfaz gráfica. El método (Gran M tabular, fracciones exactas) es propio; scipy solo se usa en `tests/` para verificar.

## Requisitos e instalación

(Python 3.10+ + Streamlit)

```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```
streamlit run app.py
```

## Pruebas

```
python -m pytest -q tests
```

## Estructura

| Archivo           | Función                                               |
| ----------------- | ----------------------------------------------------- |
| `app.py`          | Interfaz (solo renderiza)                             |
| `modelo.py`       | Problema, validación de entrada, JSON                 |
| `simplex.py`      | Gran M; devuelve la lista de pasos (sin imprimir)     |
| `sensibilidad.py` | Precios sombra, costos reducidos, rangos de c y de LD |
| `grafico.py`      | Método gráfico (n = 2)                                |
| `reporte.py`      | Texto y PDF del paso a paso                           |
| `ejemplos.py`     | Los 7 problemas del enunciado                         |

## Dónde modificar

- Regla de entrada/salida de variables: bucle `while` en `simplex.resolver`.
- Textos de justificación: campo `texto` de cada paso.
- Nuevo método (p. ej. simplex revisado): crear función que devuelva el mismo dict y llamarla desde `app.py`.

Bonificaciones incluidas: fracciones exactas, exportar PDF, cargar/guardar JSON.
