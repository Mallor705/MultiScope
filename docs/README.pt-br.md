[English](../README.md) | [Español](./README.es.md)

# MultiScope

<p align="center">
  <img src="https://github.com/user-attachments/assets/cca94b1c-f465-4f69-806b-4d853e432563" alt="MultiScope Logo" width="128" height="128">
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

O **MultiScope** é uma ferramenta para Linux/SteamOS que permite criar e gerenciar múltiplas instâncias do `gamescope` e `steam` simultaneamente. Isso possibilita que vários jogadores aproveitem sua biblioteca de jogos em um único computador, seja em tela dividida ou cada um com sua própria tela, além de saída de áudio e dispositivos de entrada dedicados.

---

<img width="850" height="650" alt="multiscope_ui" src="https://github.com/user-attachments/assets/b4618997-7136-44b4-9398-7b0a569a641e" />

## ✨ Principais Funcionalidades

O MultiScope foi projetado para ser uma solução flexível para múltiplos jogos simultaneos no Linux. Aqui estão algumas de suas principais funcionalidades:

1.  **Gerenciamento Simples de Múltiplas Instâncias:** Execute várias instâncias da steam simultaneamente, permitindo que você e seus amigos aproveitem suas bibliotecas de jogos separadamente.
2.  **Atribuição de Hardware por Instância:** Atribua mouse, teclado e controle específicos para cada instância do jogo. (Mouse/Teclado só podem ser atribuídos a uma instância por vez)
3.  **Canais de Áudio Dedicados:** Direcione o áudio de cada instância do jogo para um dispositivo de saída de áudio separado.
4.  **Home Separada:** MultiScope permite que você tenha uma home nova e separada para cada instância, permitindo que você personalize suas configurações e arquivos individualmente. (Não interfere na sua Home padrão)
5.  **Pasta de Jogos Compartilhada:** MultiScope permite que você compartilhe o diretório de jogos steam entre várias instâncias, economizando espaço em disco e facilitando a atualização de jogos. (Os usuários precisam ter o jogo em suas bibliotecas steam para que seja possível executá-lo)
6.  **Use Qualquer Proton:** MultiScope permite que você use qualquer versão do Proton para executar seus jogos, incluindo protons personalizados como o [ProtonGE](https://github.com/GloriousEggroll/proton-ge-custom).
7.  **Jogue o Que Quiser** A instancias não precisam se limitar a jogar o mesmo jogo, cada instancia pode jogar o jogo que quiser (desde que o usuario tenha o jogo em sua biblioteca steam)

## 🎬 Demonstração

[horizontal-demo.webm](https://github.com/user-attachments/assets/7f74342f-415f-4296-8dbf-1c66e8286092)

## 📦 Instalação

### Flatpak (Recomendado)
A maneira recomendada de instalar o MultiScope é via Flatpak, que oferece um ambiente em sandbox e atualizações mais fáceis. Você pode instalá-lo do Flathub (assim que estiver disponível) ou de um arquivo `.flatpak` da [página de releases](https://github.com/Mallor705/MultiScope/releases).

**Opção 1: Instalar do Flathub (Em Breve)**
Assim que o MultiScope estiver disponível no Flathub, você poderá instalá-lo usando os seguintes comandos:
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub io.github.mallor.MultiScope
```

**Opção 2: Instalar de um arquivo .flatpak**
1. **Baixe o último arquivo .flatpak:**
   Acesse a página de [**Releases**](https://github.com/Mallor705/MultiScope/releases) e baixe o último arquivo `.flatpak`.

2. **Instale o Flatpak:**
   Você pode instalar o Flatpak com o seguinte comando:
   ```bash
   flatpak install MultiScope.flatpak
   ```

### AppImage
Alternativamente, você pode usar a versão AppImage. Este arquivo único funciona na maioria das distribuições Linux modernas sem a necessidade de instalação no sistema.

1.  **Baixe o AppImage mais recente:**
    Acesse a página de [**Releases**](https://github.com/Mallor705/MultiScope/releases) e baixe o arquivo `.AppImage` mais recente.

2.  **Torne-o Executável:**
    Após o download, clique com o botão direito no arquivo, vá para "Propriedades" e marque a caixa "Permitir a execução do arquivo como programa". Alternativamente, você pode usar o terminal:
    ```bash
    chmod +x MultiScope-*.AppImage
    ```

3.  **Execute o Aplicativo:**
    Execute o appimage e aproveite. É isso!

#### Integração de AppImage (Opcional)

Para uma melhor integração com o sistema (por exemplo, adicionar uma entrada no menu de aplicativos), você pode usar uma ferramenta como o **[Gear Lever](https://github.com/mijorus/gearlever)** para gerenciar seu AppImage.

## 📖 Como Usar?

Acesse nosso [Guia](./GUIDE.pt-br.md) para mais informações sobre como usar o MultiScope.

---

## 🚀 Status e Compatibilidade do Projeto

É necessário ter os pacotes `steam` e `gamescope` nativos de sua distro. O MultiScope deve funcionar bem em sistemas que já conseguem executar o `Gamescope` e `Steam` normalmente.

Para que o auto-tiling das janelas funcione bem, é recomendado usar KDE Plasma 6.0 ou superior. Em outras DE, será necessário mover as janelas você mesmo. 

O MultiScope está em desenvolvimento ativo, alguns bugs ainda podem ser encontrados.

Caso tenha problemas, sinta-se a vontade para compartilhar seu feedback e reportar bugs em [Issues](https://github.com/Mallor705/MultiScope/issues/new).

---

## ⚙️ Como Funciona

O MultiScope utiliza o **Bubblewrap (`bwrap`)**, uma ferramenta de sandboxing de baixo nível do Linux, para isolar cada instância do Steam. Isso garante que as instâncias não interfiram umas com as outras ou com o sistema principal do usuário. Além disso, a linha de comando do `Gamescope` é gerada dinamicamente com base nas configurações do usuário, envolvendo o comando `bwrap` que, por sua vez, executa o `Steam`.

---

## 🛠️ Para Desenvolvedores

Se você deseja contribuir com o MultiScope ou executá-lo diretamente do código-fonte, siga as instruções abaixo.

### Executando a Partir do Código-Fonte

O script `run.sh` oferece uma maneira rápida de configurar um ambiente local e executar o aplicativo. Ele criará automaticamente um ambiente virtual e instalará as dependências necessárias.

```bash
# Clone o repositório
git clone https://github.com/Mallor705/MultiScope.git
cd MultiScope

# Execute o script de execução
./run.sh
```

### Compilando a Partir do Código-Fonte

O script `build.sh` compila o aplicativo em um executável independente usando o PyInstaller. O binário final será colocado no diretório `dist/`.

```bash
./build.sh
```

### Empacotando um AppImage

O script `package-appimage.sh` automatiza o processo de criação de um AppImage. Ele primeiro executa o script de compilação e, em seguida, usa o `linuxdeploy` para empacotar o aplicativo em um arquivo `.appimage` distribuível.

```bash
./package-appimage.sh
```

### Empacotando um Flatpak
O script `package-flatpak.sh` automatiza o processo de criação de um Flatpak. Ele irá construir o aplicativo e, em seguida, empacotá-lo em um arquivo `.flatpak`.

```bash
./package-flatpak.sh
```


## 🤝 Como Contribuir

Recebemos contribuições de todos! Se você estiver interessado em ajudar a melhorar o MultiScope, siga estes passos:

1.  **Faça um Fork do Repositório:** Crie sua própria cópia do projeto no GitHub.
2.  **Crie uma Branch:** Crie uma nova branch para sua funcionalidade ou correção de bug (`git checkout -b minha-feature-incrivel`).
3.  **Faça Suas Alterações:** Implemente suas melhorias.
4.  **Envie um Pull Request:** Abra um pull request detalhando suas alterações para revisão.

## 📜 Licença

Este projeto está licenciado sob a **Licença Pública Geral GNU v3.0 (GPL-3.0)**. Para mais detalhes, consulte o arquivo [LICENSE](../LICENSE).

## ⚖️ Aviso Legal

O MultiScope é um projeto independente de código aberto e não é afiliado, endossado por, ou de qualquer forma oficialmente conectado à Valve Corporation ou ao Steam.

Esta ferramenta atua como uma camada de orquestração que aproveita tecnologias de sandboxing (`bubblewrap`) para executar múltiplas instâncias isoladas do cliente oficial do Steam. O MultiScope **não modifica, aplica patches, faz engenharia reversa ou altera** quaisquer arquivos do Steam ou seu funcionamento normal. Todas as instâncias do Steam iniciadas por esta ferramenta são as versões oficiais e não modificadas fornecidas pela Valve.

Os usuários são os únicos responsáveis por cumprir os termos do Acordo de Assinante do Steam.

## 🙏 Créditos

Este projeto foi inspirado pelo trabalho de:

-   [NaviVani-dev](https://github.com/NaviVani-dev) e seu script [dualscope.sh](https://gist.github.com/NaviVani-dev/9a8a704a31313fd5ed5fa68babf7bc3a).
-   [Tau5](https://github.com/Tau5) e seu projeto [Co-op-on-Linux](https://github.com/Tau5/Co-op-on-Linux).
-   [wunnr](https://github.com/wunnr) e seu projeto [Partydeck](https://github.com/wunnr/partydeck) (Recomendo usa-lo caso você esteja procurando uma abordagem mais próxima ao [Nucleus Co-op](https://github.com/SplitScreen-Me/splitscreenme-nucleus)).
