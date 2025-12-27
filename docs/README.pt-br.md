[English](../README.md) | [Español](./README.es.md)

# MultiScope

O **MultiScope** é uma ferramenta de código aberto para Linux/SteamOS que permite criar e gerenciar múltiplas instâncias do `gamescope` e `steam` simultaneamente. Isso possibilita que vários jogadores aproveitem sua biblioteca de jogos em um único computador, seja em tela dividida ou cada um com sua própria tela, além de saída de áudio e dispositivos de entrada dedicados.

---
<img width="800" height="729" alt="multiscope-ui" src="https://github.com/user-attachments/assets/aea8a9e3-7c11-4978-9141-572d2dce9613" />

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

A maneira mais fácil e recomendada de usar o MultiScope é através da versão AppImage. Este arquivo único funciona na maioria das distribuições Linux modernas sem a necessidade de instalação no sistema.

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

## Como Usar?

Acesse nosso [Guia](./GUIDE.pt-br.md) para mais informações sobre como usar o MultiScope.

---

## 🚀 Status e Compatibilidade do Projeto

É necessário ter os pacotes `steam` e `gamescope` nativos de sua distro. O MultiScope deve funcionar bem em sistemas que já conseguem executar o `Gamescope` e `Steam` normalmente, já que o funcionamento padrão deles não é alterado.

Para que o auto-tiling das janelas funcione bem, é recomendado usar KDE Plasma 6.0 ou superior. Em outras DE, será necessário mover as janelas você mesmo. 

O MultiScope está em desenvolvimento ativo, alguns bugs ainda podem ser encontrados.

Caso tenha problemas, sinta-se a vontade para compartilhar seu feedback e reportar bugs em [Issues](https://github.com/Mallor705/MultiScope/issues).

---

## ⚙️ Como Funciona

O MultiScope orquestra múltiplas instâncias independentes da Steam, aproveitando tecnologias de sandboxing e gerenciamento de exibição do Linux. O objetivo principal é executar sessões separadas da Steam que não entrem em conflito umas com as outras, permitindo que diferentes usuários façam login e joguem simultaneamente sem que aja interferência entre os clientes steam.

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
