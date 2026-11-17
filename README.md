# 🍎 Calori — Cuenta calorías con una foto

> **Haz una foto a tu comida y la IA calcula calorías y macros. Funciona en el móvil, sin instalar nada y sin que el usuario configure claves.**
>
> *English: a mobile-first web app that estimates calories and macros from a photo of your meal using Gemini vision, with a secure backend that keeps API keys server-side.*

### 👉 [Probar la demo en vivo](https://calori-obec.onrender.com)

> ⏱️ La demo está en un plan gratuito: si nadie la ha usado en un rato, la primera carga puede tardar ~50 s en despertar.

<!-- Añade aquí capturas de pantalla de la app en el móvil:
<p align="center">
  <img src="docs/captura-plan.png" width="230">
  <img src="docs/captura-dia.png" width="230">
  <img src="docs/captura-analisis.png" width="230">
</p>
-->

---

## ✨ Qué hace

- 📸 **Análisis por foto:** detecta los platos, estima gramos, calorías, carbohidratos, proteínas y grasas.
- 🎯 **Plan personalizado:** un asistente de 8 preguntas calcula tu límite diario (metabolismo basal con Mifflin-St Jeor y gasto según tu actividad).
- 🛡️ **Ritmo seguro:** nunca propone bajar de un mínimo de kcal ni perder más del 1 % del peso por semana; avisa si el plazo elegido es demasiado rápido.
- 🤖 **IA como asesor:** recomienda un plazo realista y sugiere comidas del día ajustadas a tus calorías, preferencias y alergias.
- 📊 **Seguimiento diario:** anillo de progreso, reparto por comidas (desayuno, aperitivo, comida, merienda, cena), macros frente a objetivo y racha de días.
- 📱 **Mobile-first:** una sola página que se puede añadir a la pantalla de inicio como si fuera una app.

## 🏗️ Arquitectura

```
┌──────────────┐   foto + prompt    ┌──────────────────┐    clave API     ┌──────────────┐
│  Móvil       │ ─────────────────▶ │  Servidor Python │ ───────────────▶ │ Google Gemini│
│  (HTML + JS) │ ◀───────────────── │  (Render)        │ ◀─────────────── │  (visión)    │
└──────────────┘     JSON           └──────────────────┘     JSON         └──────────────┘
  datos del usuario                  claves en variables
  guardados en su móvil              de entorno (nunca en el cliente)
```

### Decisiones técnicas que me interesaba resolver

| Problema | Solución |
|---|---|
| **No exponer las claves de la IA** en un front público | Un backend propio hace de proxy: el móvil nunca ve ninguna clave; viven como variables de entorno del hosting. |
| **Disponibilidad y cuotas** de la API | Hasta 3 claves/modelos con **failover automático**: si una falla o se queda sin cuota, prueba la siguiente. |
| **Abuso del servicio** | **Rate limiting** por usuario (por hora) y tope diario global, configurables por variables de entorno. |
| **Privacidad y simplicidad** | Sin cuentas ni base de datos: cada usuario guarda sus datos en su propio dispositivo (`localStorage`) y el servidor no almacena fotos. |
| **Respuestas de IA fiables** | Prompt que fuerza salida JSON estricta, y limpieza/validación de la respuesta antes de mostrarla. |
| **Peso de las fotos** | Las imágenes se redimensionan y comprimen en el navegador antes de enviarlas. |

## 🧰 Stack

- **Frontend:** HTML, CSS y JavaScript vanilla en un único archivo (sin frameworks ni dependencias).
- **Backend:** Python 3 con el servidor HTTP de la librería estándar + `requests`.
- **IA:** Google Gemini (visión) con soporte opcional para Anthropic Claude y OpenAI como respaldo.
- **Despliegue:** Render (HTTPS incluido), con despliegue automático desde GitHub.

## 🚀 Ejecutarlo en local

```bash
git clone https://github.com/OLIVER26GOLDEN/CALORI.git
cd CALORI
pip install -r requirements.txt

# Crea un archivo .env con tu(s) clave(s) de Gemini
echo "GEMINI_API_KEY_1=tu_clave" > .env

python servidor_movil.py
# Abre http://localhost:8000
```

## ☁️ Desplegarlo

1. Sube el repositorio a GitHub (el `.env` **no** se sube: está en `.gitignore`).
2. En Render: *New → Web Service*, runtime **Python 3**.
3. Build: `pip install -r requirements.txt` · Start: `python servidor_movil.py`
4. En *Environment* añade `GEMINI_API_KEY_1` (y `_2`, `_3` opcionales).
5. Variables opcionales: `LIMITE_HORA` (por defecto 30) y `LIMITE_DIA_TOTAL` (por defecto 1500).

Comprobación rápida: `https://tu-app.onrender.com/api/estado` → `{"ok": true, "apis": N}`.

## 📁 Estructura

```
├── servidor_movil.py     # Backend: sirve la web y hace de proxy seguro hacia la IA
├── calori_movil.html     # App completa (UI, lógica del plan, seguimiento)
├── requirements.txt
├── Procfile
└── .gitignore
```

## 🧭 Próximos pasos

- [ ] Cuentas de usuario y base de datos para sincronizar el historial entre dispositivos.
- [ ] Tests automáticos de la lógica del plan y del servidor.
- [ ] Modo offline (service worker) e instalación como PWA completa.
- [ ] Gráficas de evolución del peso y de las calorías semanales.

## ⚠️ Aviso

Las calorías y macros son **estimaciones de una IA** y no sustituyen el consejo de un profesional sanitario.

## 👤 Autor

**Oliver Lugo Jiménez** — [@OLIVER26GOLDEN](https://github.com/OLIVER26GOLDEN)

Proyecto nacido como una app de escritorio en Python y llevado a la web móvil, con backend propio y despliegue en producción. 
