<p align="right">
  <a href="https://github.com/mall0r/Twinverse/blob/master/docs/GUIDE.md"><img src="https://img.shields.io/badge/EN-🇬🇧-darkblue.svg" alt="English"/></a>
  <a href="https://github.com/mall0r/Twinverse/blob/master/docs/GUIDE.es.md"><img src="https://img.shields.io/badge/ES-🇪🇸-darkred.svg" alt="Spanish"/></a>
</p>

# Guia do Twinverse

Bem-vindo ao guia do Twinverse! Este documento irá guiá-lo pelo processo de configuração e uso do aplicativo Twinverse para executar múltiplas instâncias do Steam.

> [!NOTE]
> Para usar o Twinverse, é necessário adicionar seu usuário ao grupo `input` para permitir que o programa gerencie os dispositivos de entrada.
>
> ```bash
> sudo usermod -aG input $USER
> ```
> no Bazzite:
> ```bash
> ujust add-user-to-input-group
> ```
> **Reinicie o sistema para que as alterações entrem em vigor.**

## 1. Número de Instâncias

Primeiro, você precisa decidir quantas instâncias do Steam deseja executar. O Twinverse suporta até 8 instâncias no total.

- **Tela Dividida (Splitscreen):** Você pode executar no máximo 4 instâncias por monitor.
- **Tela Cheia (Fullscreen):** Você pode executar no máximo 1 instância por monitor.

Use o seletor numérico "Número de Instâncias" para definir a quantidade desejada.

<img width="708" height="127" alt="general-layout" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/general-layout.png" />

## 2. Modo de Tela

Você pode escolher entre dois modos de tela:

- **Tela Cheia (Fullscreen):** Cada instância será executada em um monitor separado.
- **Tela Dividida (Splitscreen):** As instâncias serão dispostas em um único monitor, seja horizontal ou verticalmente.

<img width="708" height="204" alt="screen-settings" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/screen-settings.png" />

### Opções de Tela Dividida

Ao selecionar "Splitscreen", você pode escolher entre duas orientações:

- **Horizontal:** As instâncias são dispostas lado a lado.
- **Vertical:** As instâncias são dispostas uma acima da outra.

Posições e formatos variam automaticamente de acordo com o número de instâncias.

Nota: O auto-tiling das instâncias funciona apenas com ambientes `KDE Plasma`.

<img width="1280" height="720" alt="horizontal-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/horizontal-game.png" />
<img width="1280" height="720" alt="vertical-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/vertical-game.png" />

## 3. Configuração da Instância

Para cada instância, você pode configurar as seguintes opções:

- **Controle (Gamepad):** Atribuir um controle específico à instância.
- **Capturar Mouse:** Dedicar o mouse a uma única instância. Por enquanto, apenas uma instância por vez pode usar o mouse e o teclado.
- **Dispositivo de Áudio:** Selecionar um dispositivo de saída de áudio específico para a instância.
- **Taxa de Atualização (Refresh Rate):** Definir a taxa de atualização para a instância. Util se você quer travar o FPS ou usar uma taxa de atualização específica.
- **Variável de Ambiente (Environment Variables):** Definir variáveis de ambiente específicas para a instância.

<img width="595" height="409" alt="player-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/player-config.png" />

## 4. Iniciando uma Instância

Após configurar uma instância, clique no botão **"Start"** ao lado dela para iniciar uma instância isolada do Steam sem o gamescope. Na primeira vez, o Steam será instalado automaticamente — esse processo pode levar alguns minutos.

Cada instância pode ser iniciada individualmente pelo seu botão **"Start"**. Para executar várias de uma só vez, utilize o botão **"Play"** localizado na parte inferior da janela.

Apenas instâncias que já possuem o Steam instalado podem ser iniciadas com o **"Play"**. Você pode verificar isso pelo ícone de visto (check) na instância. Se o ícone não estiver presente, instale o Steam clicando no botão **"Start"** daquela instância. Isso permite configurar, adicionar jogos ou aplicativos de maneira rápida e direta em uma instância específica.

<img width="651" height="178" alt="instance-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/instance-config.png" />

## 5. Modo Big Picture do Steam (Opicional)

Para uma melhor experiência, recomenda-se ativar o "Modo Big Picture" nas configurações do Steam. Isso fornecerá uma interface amigável a controles, ideal para o Twinverse.

Para fazer isso, vá em `Configurações > Interface` e marque a caixa para `Iniciar Steam no Modo Big Picture`.

Repita esse processo para todas as instâncias que você deseja iniciar no Modo Big Picture.

<img width="850" height="722" alt="enable-bigpicture" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/enable-bigpicture.png" />

## 6. Jogar

Quando todas as suas instâncias estiverem configuradas e em execução, você pode começar a jogar! Cada instância terá seus próprios dispositivos de entrada e áudio dedicados, permitindo que você jogue com seus amigos ou familiares no mesmo computador.

Divirta-se em sua sessão de jogos!

### Atalhos de teclado:
```
Super + F       Alternar tela cheia
```
```
Super + N       Alternar filtragem por vizinho mais próximo
```
```
Super + U       Alternar e aumentar a escala FSR
```
```
Super + Y       Alternar e aumentar a escala NIS
```
```
Super + I       Aumentar a nitidez FSR em 1
```
```
Super + O       Diminuir a nitidez FSR em 1
```
```
Super + S       Tirar uma captura de tela
```
```
Super + G       Alternar captura de tela com o teclado
```

# Opcional

## Aplicativos

Para adicionar aplicativos à sua instância, vá em `Adicionar Jogo` e clique em `Adicionar um jogo não Steam...`. Selecione o aplicativo que deseja adicionar.

<img width="364" height="142" alt="add-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/add-game.png" />

### Por que fazer isso?

Isso permite que você execute aplicativos diretamente da instância, assim é possível ter uma configuração única por instância para esse aplicativo. Isso acontece pois cada instância tem seu próprio diretório `HOME` único. Eles podem ser encontrados em `~/.local/share/twinverse/home_{n}`.

Um bom exemplo de uso é o [mangojuice](https://github.com/radiolamp/mangojuice); caso queira usá-lo com configurações personalizadas você precisará executar e configurá-lo para cada instância individualmente.

## Suporte a Multiplas GPUs

> [!NOTE]
> Isso deve ser adicionado diretamente no argumento dos jogos, não adicione isso ao enviroments variables.

O Twinverse suporta a execução de múltiplas Games em GPUs diferentes. 

Adicione a seguinte linha aos argumentos do Steam do seu jogo:

```bash
DRI_PRIME=1!

```

Isso faz a GPU 1 ser usada no jogo. Você pode ajustar os numeros de acordo com a configuração do seu sistema.
