[English](../README.md) | [Português](./README.pt-br.md)

# MultiScope

<p align="center">
  <img src="https://raw.githubusercontent.com/Mallor705/MultiScope/master/share/icons/hicolor/scalable/apps/io.github.mallor.MultiScope.svg" alt="MultiScope Logo" width="128" height="128">
</p>

<p align="center">
  <a href="https://github.com/Mallor705/Multiscope/releases"><img src="https://img.shields.io/badge/Version-0.9.0-blue.svg" alt="Version"/></a>
  <a href="https://github.com/Mallor705/MultiScope/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-green.svg" alt="License"/></a>
  <a href="https://www.gtk.org/"><img src="https://img.shields.io/badge/GTK-4.0+-orange.svg" alt="GTK Version"/></a>
  <a href="https://gnome.pages.gitlab.gnome.org/libadwaita/"><img src="https://img.shields.io/badge/libadwaita-1.0+-purple.svg" alt="libadwaita Version"/></a>
</p>

<p align="center">
  <a href="https://www.python.org" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://www.gnu.org/software/bash/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnu-bash&logoColor=white" alt="Shell"/></a>
  <a href="https://www.javascript.com/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/></a>
  <a href="https://www.w3.org/Style/CSS/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/CSS3-66309A?style=for-the-badge&logo=css3&logoColor=white" alt="CSS"/></a>
</p>

**MultiScope** es una herramienta para Linux/SteamOS que te permite crear y gestionar múltiples instancias de `gamescope` y `steam` simultáneamente. Esto permite que varios jugadores disfruten de su biblioteca de juegos en una sola computadora, ya sea en pantalla dividida o cada uno con su propia pantalla, además de contar con salida de audio y dispositivos de entrada dedicados.

---

<p align="center">
  <img width="850" height="650" alt="multiscope_ui" src="https://raw.githubusercontent.com/Mallor705/MultiScope/master/share/screenshots/multiscope-ui.png" />
</p>

## ✨ Características Principales

MultiScope está diseñado como una solución flexible para jugar múltiples juegos al mismo tiempo en Linux. Aquí están algunas de sus características principales:

1.  **Gestión Sencilla de Múltiples Instancias:** Ejecuta varias instancias de Steam al mismo tiempo, permitiendo que tú y tus amigos disfruten sus bibliotecas de juegos por separado.
2.  **Asignación de Hardware por Instancia:** Asigna ratones, teclados y controles específicos a cada instancia del juego. (El ratón/teclado solo se puede asignar a una instancia a la vez)
3.  **Canales de Audio Dedicados:** Envía el audio de cada instancia del juego a un dispositivo de salida de audio separado.
4.  **Directorio Home Separado:** MultiScope te permite tener un directorio "home" nuevo y separado para cada instancia, lo que te permite personalizar configuraciones y archivos individualmente. (No interfiere con tu directorio Home principal)
5.  **Biblioteca de Juegos Compartida:** MultiScope te permite compartir el directorio de juegos de Steam entre varias instancias, ahorrando espacio en disco y facilitando las actualizaciones de juegos. (Los usuarios necesitan tener el juego en sus bibliotecas de Steam para poder ejecutarlo)
6.  **Usa Cualquier Proton:** MultiScope te permite usar cualquier versión de Proton para ejecutar tus juegos, incluyendo versiones personalizadas como [ProtonGE](https://github.com/GloriousEggroll/proton-ge-custom).
7.  **Juega lo que Quieras:** Las instancias no están limitadas a jugar el mismo juego; cada instancia puede jugar el juego que desee (siempre que el usuario tenga el juego en su biblioteca de Steam).

---

## 🎬 Demostración

[horizontal-demo](https://github.com/user-attachments/assets/e0ca4937-fd38-48cf-b56c-1c825b047572)

---

## 📦 Instalación

### Flatpak (Recomendado)
La forma recomendada de instalar MultiScope es a través de Flatpak, que proporciona un entorno aislado y actualizaciones más sencillas. Puedes instalarlo desde Flathub (una vez que esté disponible) o desde un archivo `.flatpak` desde la [página de releases](https://github.com/Mallor705/MultiScope/releases).

**Opción 1: Instalar desde Flathub (Próximamente)**
Una vez que MultiScope esté disponible en Flathub, puedes instalarlo usando los siguientes comandos:
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub io.github.mallor.MultiScope
```

**Opción 2: Instalar desde un archivo .flatpak**
1. **Descarga el último archivo .flatpak:**
   Ve a la página de [**Releases**](https://github.com/Mallor705/MultiScope/releases) y descarga el último archivo `.flatpak`.

2. **Instala el Flatpak:**
   Puedes instalar el Flatpak con el siguiente comando:
   ```bash
   flatpak install MultiScope.flatpak
   ```

### AppImage
Alternativamente, puedes usar la versión AppImage. Este archivo único funciona en la mayoría de las distribuciones modernas de Linux sin necesidad de instalación en el sistema.

1.  **Descarga la AppImage más reciente:**
    Ve a la página de [**Releases**](https://github.com/Mallor705/MultiScope/releases) y descarga el archivo `.AppImage` más reciente.

2.  **Hazlo Ejecutable:**
    Después de descargarlo, haz clic derecho en el archivo, ve a "Propiedades" y marca la casilla "Permitir ejecutar el archivo como programa". Alternativamente, puedes usar la terminal:
    ```bash
    chmod +x MultiScope-*.AppImage
    ```

3.  **Ejecuta la Aplicación:**
    Ejecuta el AppImage y disfruta. ¡Eso es todo!

#### Integración de AppImage (Opcional)

Para una mejor integración con el sistema (por ejemplo, agregar una entrada en el menú de aplicaciones), puedes usar una herramienta como **[Gear Lever](https://github.com/mijorus/gearlever)** para gestionar tu AppImage.

## 📖 ¿Cómo usarlo?

Consulta nuestra [Guía](./GUIDE.es.md) para obtener más información sobre cómo usar MultiScope.

---

## 🚀 Estado y Compatibilidad del Proyecto

Necesita tener los paquetes `steam` y `gamescope` nativos de su distribución. MultiScope debería funcionar correctamente en sistemas que ya ejecutan `Gamescope` y `Steam` con normalidad.

Para que el mosaico automático de ventanas funcione correctamente, se recomienda usar KDE Plasma 6.0 o superior. En otros entornos de escritorio (DE), deberá mover las ventanas usted mismo.

MultiScope está en desarrollo activo; todavía se pueden encontrar algunos errores.

Si encuentras problemas, no dudes en compartir tus comentarios y reportar errores en la sección de [Issues](https://github.com/Mallor705/MultiScope/issues/new).

---

## ⚙️ Cómo Funciona

MultiScope utiliza **Bubblewrap (`bwrap`)**, una herramienta de sandbox de bajo nivel para Linux, para aislar cada instancia de Steam. Esto garantiza que las instancias no interfieran entre sí ni con el sistema principal del usuario. Además, la línea de comandos de `Gamescope` se genera dinámicamente según la configuración del usuario, involucrando el comando `bwrap`, que, a su vez, inicia `Steam`.

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

MultiScope proporciona un Makefile para gestionar compilaciones y versiones. Puedes compilar la aplicación usando el siguiente comando:

```bash
make build
```

Alternativamente, puedes usar el script de compilación directamente:

```bash
./scripts/build.sh
```

### Empaquetar un AppImage

El script `scripts/package-appimage.sh` automatiza el proceso de creación de un AppImage. Primero ejecuta el script de compilación y luego usa `linuxdeploy` para empaquetar la aplicación en un archivo `.appimage` distribuible.

```bash
make appimage
```

O usando el script directamente:

```bash
./scripts/package-appimage.sh
```

### Empaquetar un Flatpak
El script `scripts/package-flatpak.sh` automatiza el proceso de creación de un Flatpak. Construirá la aplicación y luego la empaquetará en un archivo `.flatpak`.

```bash
make flatpak
```

O usando el script directamente:

```bash
./scripts/package-flatpak.sh
```


## 🤝 Cómo Contribuir

¡Aceptamos contribuciones de todos! Si estás interesado en ayudar a mejorar MultiScope, sigue estos pasos:

1.  **Haz un Fork del Repositorio:** Crea tu propia copia del proyecto en GitHub.
2.  **Crea una Rama:** Crea una nueva rama para tu función o corrección de errores (`git checkout -b mi-funcion-increible`).
3.  **Haz tus Cambios:** Implementa tus mejoras.
4.  **Envía un Pull Request:** Abre un "pull request" detallando tus cambios para revisión.

---

## 📜 Licencia

Este proyecto está bajo la **Licencia Pública General de GNU v3.0 (GPL-3.0)**. Para más detalles, consulta el archivo [LICENSE](../LICENSE).

## ⚖️ Aviso Legal

MultiScope es un proyecto independiente de código abierto y no está afiliado, respaldado o de ninguna manera conectado oficialmente con Valve Corporation o Steam.

Esta herramienta actúa como una capa de orquestación que aprovecha tecnologías de aislamiento (`bubblewrap`) para ejecutar múltiples instancias aisladas del cliente oficial de Steam. MultiScope **no modifica, parchea, realiza ingeniería inversa ni altera** ningún archivo de Steam o su funcionamiento normal. Todas las instancias de Steam lanzadas por esta herramienta son las versiones oficiales y no modificadas proporcionadas por Valve.

Los usuarios son los únicos responsables de cumplir con los términos del Acuerdo de Suscriptor de Steam.

---

## 🙏 Créditos

Este proyecto se inspiró en el trabajo de:

-   [NaviVani-dev](https://github.com/NaviVani-dev) y su script [dualscope.sh](https://gist.github.com/NaviVani-dev/9a8a704a31313fd5ed5fa68babf7bc3a).
-   [Tau5](https://github.com/Tau5) y su proyecto [Co-op-on-Linux](https://github.com/Tau5/Co-op-on-Linux).
-   [wunnr](https://github.com/wunnr) y su proyecto [Partydeck](https://github.com/wunnr/partydeck) (Recomiendo usarlo si buscas un enfoque más cercano a [Nucleus Co-op](https://github.com/SplitScreen-Me/splitscreenme-nucleus)).
