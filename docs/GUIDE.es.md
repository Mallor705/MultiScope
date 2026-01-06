[English](./GUIDE.md) | [Português](./GUIDE.pt-br.md)

# Guía de Twinverse

¡Bienvenido a la guía de Twinverse! Este documento te guiará por el proceso de configuración y uso de la aplicación Twinverse para ejecutar múltiples instancias de Steam.

> [!NOTE]
> Para usar Twinverse, es necesario agregar su usuario al grupo `input` para permitir que el programa gestione los dispositivos de entrada.
>
> ```bash
> sudo usermod -aG input $USER
> ```
> en el Bazzite:
> ```bash
> ujust add-user-to-input-group
> ```
> **Reinicie el sistema para que los cambios surtan efecto.**

## 1. Número de instancias

Primero, necesitas decidir cuántas instancias de Steam deseas ejecutar. Twinverse soporta hasta 8 instancias en total.

- **Pantalla dividida (Splitscreen):** Puedes ejecutar un máximo de 4 instancias por monitor.
- **Pantalla completa (Fullscreen):** Puedes ejecutar un máximo de 1 instancia por monitor.

Usa el selector numérico "Número de instancias" para definir la cantidad deseada.

<img width="708" height="127" alt="general-layout" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/general-layout.png" />

## 2. Modo de pantalla

Puedes elegir entre dos modos de pantalla:

- **Pantalla completa (Fullscreen):** Cada instancia se ejecutará en un monitor separado.
- **Pantalla dividida (Splitscreen):** Las instancias se distribuirán en un solo monitor, ya sea horizontal o verticalmente.

<img width="708" height="204" alt="screen-settings" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/screen-settings.png" />

### Opciones de Pantalla dividida

Al seleccionar "Splitscreen", puedes elegir entre dos orientaciones:

- **Horizontal:** Las instancias se colocan una al lado de la otra.
- **Vertical:** Las instancias se colocan una encima de la otra.

Las posiciones y los formatos varían automáticamente según el número de instancias.

Nota: La organización automática de las instancias solo funciona con entornos `KDE Plasma`.

<img width="1280" height="720" alt="horizontal-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/horizontal-game.png" />
<img width="1280" height="720" alt="vertical-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/vertical-game.png" />

## 3. Configuración de la instancia

Para cada instancia, puedes configurar las siguientes opciones:

- **Control (Gamepad):** Asignar un control específico a la instancia.
- **Capturar Mouse:** Dedicar el mouse a una sola instancia. Por ahora, solo una instancia a la vez puede usar el mouse y el teclado.
- **Dispositivo de audio:** Seleccionar un dispositivo de salida de audio específico para la instancia.
- **Tasa de actualización (Refresh Rate):** Definir la tasa de actualización para la instancia. Es útil si quieres limitar los FPS o usar una tasa de actualización específica.
- **Variables de entorno (Environment Variables):** Definir variables de entorno específicas para la instancia.

<img width="595" height="409" alt="player-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/player-config.png" />

## 4. Iniciar una instancia

Después de configurar una instancia, haz clic en el botón **"Iniciar"** junto a ella para lanzar una instancia aislada de Steam sin gamescope. La primera vez, Steam se instalará automáticamente; este proceso puede tomar unos minutos.

Cada instancia puede iniciarse individualmente con su botón **"Iniciar"**. Para ejecutar varias a la vez, utiliza el botón **"Play"** ubicado en la parte inferior de la ventana.

Solo las instancias que ya tienen Steam instalado pueden iniciarse con el botón **"Play"**. Puedes verificarlo por el ícono de palomita (✓) en la instancia. Si el ícono no está presente, instala Steam haciendo clic en el botón **"Iniciar"** de esa instancia. Esto permite configurar, agregar juegos o aplicaciones de manera rápida y directa en una instancia específica.

<img width="651" height="178" alt="instance-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/instance-config.png" />

## 5. Modo Big Picture de Steam (Opcional)

Para una mejor experiencia, se recomienda activar el "Modo Big Picture" en la configuración de Steam. Esto proporcionará una interfaz amigable para controles, ideal para Twinverse.

Para hacerlo, ve a `Configuración > Interfaz` y marca la casilla para `Iniciar Steam en modo Big Picture`.

Repite este proceso para todas las instancias que desees iniciar en Modo Big Picture.

<img width="850" height="722" alt="enable-bigpicture" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/enable-bigpicture.png" />

## 6. Jugar

¡Cuando todas tus instancias estén configuradas y en ejecución, puedes comenzar a jugar! Cada instancia tendrá sus propios dispositivos de entrada y audio dedicados, permitiéndote jugar con tus amigos o familiares en la misma computadora.

¡Disfruta tu sesión de juego!

### Atajos de teclado:

  Super + F                      alternar fullscreen
  Super + N                      alternar filtro de vecinos más cercanos
  Super + U                      alternar FSR upscaling
  Super + Y                      alternar NIS upscaling
  Super + I                      aumentar la nitidez de FSR en 1
  Super + O                      disminuir la nitidez de FSR en 1
  Super + S                      tomar una captura de pantalla
  Super + G                      alternar captura de teclado

# Opcional

## Aplicaciones

Para agregar aplicaciones a tu instancia, ve a `Agregar un juego` y haz clic en `Agregar un juego que no es de Steam...`. Selecciona la aplicación que deseas agregar.

<img width="364" height="142" alt="add-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/add-game.png" />

### ¿Por qué hacer esto?

Esto te permite ejecutar aplicaciones directamente desde la instancia, haciendo posible tener una configuración única por instancia para esa aplicación. Esto sucede porque cada instancia tiene su propio directorio `HOME` único. Se pueden encontrar en `~/.local/share/twinverse/home_{n}`.

Un buen ejemplo de uso es [mangojuice](https://github.com/radiolamp/mangojuice); si quieres usarlo con configuraciones personalizadas, necesitarás ejecutarlo y configurarlo para cada instancia individualmente.

## Compatibilidad con múltiples GPU

> [!NOTE]
> Esto debe añadirse directamente a los argumentos del juego, no a las variables de entorno.

Twinverse permite ejecutar varios juegos en diferentes GPU.

Añade la siguiente línea a los argumentos de Steam de tu juego:

```bash
DRI_PRIME=1!

```

Esto hace que se use la GPU 1 en el juego. Puedes ajustar los valores según la configuración de tu sistema.
