[English](../README.md) | [Português](./README.pt-br.md)

# MultiScope

**MultiScope** es una herramienta de código abierto para Linux que te permite crear y gestionar múltiples instancias de `gamescope` y `steam` simultáneamente. Esto permite que varios jugadores disfruten de su biblioteca de juegos en una sola computadora, ya sea en pantalla dividida o cada uno con su propia pantalla, además de contar con salida de audio y dispositivos de entrada dedicados.

---

## ✨ Características Principales

MultiScope está diseñado como una solución flexible para jugar múltiples juegos al mismo tiempo en Linux. Aquí están algunas de sus características principales:

1.  **Gestión Sencilla de Múltiples Instancias:** Ejecuta varias instancias de Steam al mismo tiempo, permitiendo que tú y tus amigos disfruten sus bibliotecas de juegos por separado.
2.  **Asignación de Hardware por Instancia:** Asigna ratones, teclados y controles específicos a cada instancia del juego. (El ratón/teclado solo se puede asignar a una instancia a la vez)
3.  **Canales de Audio Dedicados:** Envía el audio de cada instancia del juego a un dispositivo de salida de audio separado.
4.  **Interfaz Gráfica Intuitiva (GUI):** Una interfaz amigable que simplifica la configuración y el lanzamiento de tus sesiones de juego.
5.  **Directorio Home Separado:** MultiScope te permite tener un directorio "home" nuevo y separado para cada instancia, lo que te permite personalizar configuraciones y archivos individualmente. (No interfiere con tu directorio Home principal)
6.  **Biblioteca de Juegos Compartida:** MultiScope te permite compartir el directorio de juegos de Steam entre varias instancias, ahorrando espacio en disco y facilitando las actualizaciones de juegos. (Los usuarios necesitan tener el juego en sus bibliotecas de Steam para poder ejecutarlo)
7.  **Usa Cualquier Proton:** MultiScope te permite usar cualquier versión de Proton para ejecutar tus juegos, incluyendo versiones personalizadas como [ProtonGE](https://github.com/GloriousEggroll/proton-ge-custom).
8.  **Juega lo que Quieras:** Las instancias no están limitadas a jugar el mismo juego; cada instancia puede jugar el juego que desee (siempre que el usuario tenga el juego en su biblioteca de Steam).

## 🎬 Demostración

`![Demostración de MultiScope](URL_DEL_GIF)`

## ⚙️ Cómo Funciona

MultiScope orquesta múltiples instancias independientes de Steam aprovechando las tecnologías de aislamiento y gestión de pantalla de Linux. El objetivo principal es ejecutar sesiones separadas de Steam que no entren en conflicto entre sí, permitiendo que diferentes usuarios inicien sesión y jueguen simultáneamente sin interferencia entre los clientes de Steam.

Aquí tienes un desglose técnico de los componentes principales:

-   **Aislamiento con Bubblewrap:** Esta es la base de MultiScope. Para cada instancia de Steam, MultiScope usa `bubblewrap` para crear un entorno aislado ("sandbox"). Una función crítica de este aislamiento es la creación de un directorio `home` único y separado para cada instancia. Esto asegura que cada sesión de Steam tenga su propia configuración, caché de datos, archivos de guardado y credenciales de usuario, evitando cualquier cruce de datos o conflictos entre instancias o con el usuario del sistema.

-   **Aislamiento de Dispositivos de Entrada:** `bubblewrap` crea un directorio `/dev/input` privado y vacío dentro del entorno aislado. Luego, usa `--dev-bind` para exponer selectivamente *solo* los dispositivos de entrada asignados (por ejemplo, un teclado, ratón o controlador específico) en ese directorio privado. Este es el núcleo del aislamiento de entrada: la instancia de Steam aislada es fundamentalmente incapaz de ver cualquier otro dispositivo de entrada aparte de los que le fueron asignados explícitamente.

-   **Gestión de Pantalla con Gamescope:** MultiScope lanza instancias del cliente de Steam. Para gestionar cómo se muestran estas instancias, ofrece la opción de usar `gamescope` de Valve. Cuando está activado, `gamescope` actúa como un micro-compositor, ejecutando una instancia de Steam en un servidor de pantalla anidado y aislado. Esto permite un control preciso sobre las ventanas, resolución y configuraciones de rendimiento para la sesión de ese jugador.

-   **Redirección de Audio con Pipewire:** Para la gestión de audio, MultiScope define variables de entorno (`PULSE_SINK`) que instruyen al servidor de audio `pipewire` a dirigir todo el audio de una instancia aislada específica a un dispositivo de audio dedicado. Esto permite que el audio del juego de cada jugador se envíe a sus propios audífonos o altavoces.

## 🚀 Estado del Proyecto

MultiScope está en desarrollo activo; todavía se pueden encontrar algunos errores.

En cuanto a compatibilidad, MultiScope debería funcionar bien en sistemas que ya puedan ejecutar Gamescope y Steam normalmente, ya que su funcionamiento estándar no se altera.

Si encuentras problemas, no dudes en compartir tus comentarios y reportar errores en la sección de [Issues](https://github.com/Mallor705/MultiScope/issues).

## 📦 Instalación

La forma más fácil y recomendada de usar MultiScope es a través de la versión AppImage. Este archivo único funciona en la mayoría de las distribuciones modernas de Linux sin necesidad de instalación en el sistema.

1.  **Descarga la AppImage más reciente:**
    Ve a la página de [**Releases**](https://github.com/Mallor705/MultiScope/releases) y descarga el archivo `.appimage` más reciente.

2.  **Hazlo Ejecutable:**
    Después de descargarlo, haz clic derecho en el archivo, ve a "Propiedades" y marca la casilla "Permitir ejecutar el archivo como programa". Alternativamente, puedes usar la terminal:
    ```bash
    chmod +x MultiScope-*.AppImage
    ```

3.  **Ejecuta la Aplicación:**
    Ejecuta el AppImage y disfruta. ¡Eso es todo!

#### Integración de AppImage (Opcional)

Para una mejor integración con el sistema (por ejemplo, agregar una entrada en el menú de aplicaciones), puedes usar una herramienta como **[Gear Lever](https://github.com/mijorus/gearlever)** para gestionar tu AppImage.

---

## 🛠️ Para Desarrolladores

Si deseas contribuir a MultiScope o ejecutarlo directamente desde el código fuente, sigue las instrucciones a continuación.

### Ejecutar desde el Código Fuente

El script `run.sh` proporciona una forma rápida de configurar un entorno local y ejecutar la aplicación. Creará automáticamente un entorno virtual e instalará las dependencias necesarias.

```bash
# Clona el repositorio
git clone https://github.com/Mallor705/MultiScope.git
cd MultiScope

# Ejecuta el script de lanzamiento
./run.sh
```

### Compilar desde el Código Fuente

El script `build.sh` compila la aplicación en un ejecutable independiente usando PyInstaller. El binario final se colocará en el directorio `dist/`.

```bash
./build.sh
```

### Empaquetar un AppImage

El script `package-appimage.sh` automatiza el proceso de creación de un AppImage. Primero ejecuta el script de compilación y luego usa `linuxdeploy` para empaquetar la aplicación en un archivo `.appimage` distribuible.

```bash
./package-appimage.sh
```

## 🤝 Cómo Contribuir

¡Aceptamos contribuciones de todos! Si estás interesado en ayudar a mejorar MultiScope, sigue estos pasos:

1.  **Haz un Fork del Repositorio:** Crea tu propia copia del proyecto en GitHub.
2.  **Crea una Rama:** Crea una nueva rama para tu función o corrección de errores (`git checkout -b mi-funcion-increible`).
3.  **Haz tus Cambios:** Implementa tus mejoras.
4.  **Envía un Pull Request:** Abre un "pull request" detallando tus cambios para revisión.

## 📜 Licencia

Este proyecto está bajo la **Licencia Pública General de GNU v3.0 (GPL-3.0)**. Para más detalles, consulta el archivo [LICENSE](../LICENSE).

## ⚖️ Aviso Legal

MultiScope es un proyecto independiente de código abierto y no está afiliado, respaldado o de ninguna manera conectado oficialmente con Valve Corporation o Steam.

Esta herramienta actúa como una capa de orquestación que aprovecha tecnologías de aislamiento (`bubblewrap`) para ejecutar múltiples instancias aisladas del cliente oficial de Steam. MultiScope **no modifica, parchea, realiza ingeniería inversa ni altera** ningún archivo de Steam o su funcionamiento normal. Todas las instancias de Steam lanzadas por esta herramienta son las versiones oficiales y no modificadas proporcionadas por Valve.

Los usuarios son los únicos responsables de cumplir con los términos del Acuerdo de Suscriptor de Steam.

## 🙏 Créditos

Este proyecto se inspiró en el trabajo de:

-   [NaviVani-dev](https://github.com/NaviVani-dev) y su script [dualscope.sh](https://gist.github.com/NaviVani-dev/9a8a704a31313fd5ed5fa68babf7bc3a).
-   [Tau5](https://github.com/Tau5) y su proyecto [Co-op-on-Linux](https://github.com/Tau5/Co-op-on-Linux).
-   [wunnr](https://github.com/wunnr) y su proyecto [Partydeck](https://github.com/wunnr/partydeck) (Recomiendo usarlo si buscas un enfoque más cercano a [Nucleus Co-op](https://github.com/SplitScreen-Me/splitscreenme-nucleus)).
```
