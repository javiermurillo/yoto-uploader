# Yoto Audio Uploader

Este script automatiza la subida de archivos de audio a la plataforma "My Cards" de Yoto. Está diseñado específicamente para uso personal, para subir los audiolibros y música para las tarjetas de tu hijo.

## Funcionalidades

- **Subida por Lotes:** Sube archivos de 3 en 3 para evitar saturar la plataforma.
- **Soporte de Formatos:** Acepta `.mp3`, `.m4a`, `.wav` y `.m4b`.
- **Estabilidad:** Usa métodos directos para evitar errores de interfaz (como botones que se mueven).
- **Nombre de Playlist:** (Próximamente) Te permite nombrar la playlist y guarda los cambios automáticamente.

## Requisitos

1.  **Python 3.12+**
2.  **Playwright:** Necesario para controlar el navegador.

## Instalación

1.  Instalar las dependencias:
    ```bash
    pip install -r requirements.txt
    ```
2.  Instalar los navegadores de Playwright:
    ```bash
    playwright install chromium
    ```
3.  Configurar tus credenciales:
    - Copia el archivo de ejemplo: `cp .env.example .env`
    - Edita `.env` y pon tu email y contraseña de Yoto.

## Uso

1.  Ejecuta el script:
    ```bash
    python yoto_uploader.py
    ```
2.  Ingresa la **ruta completa** de la carpeta que contiene los archivos de audio cuando se te pida.
3.  El navegador se abrirá y verás el proceso. **No cierres la ventana** hasta que el script termine.

## Notas Importantes

- Este script es para **uso personal**.
- Si la plataforma de Yoto cambia su diseño, es posible que el script necesite actualizaciones.
