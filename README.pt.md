# Linux-Coop

![Linux-Coop Banner](https://github.com/Mallor705/Linux-Coop/assets/80993074/399081e7-295e-4c55-b040-02d242407559)

Permite jogar títulos Windows em modo cooperativo local no Linux, rodando múltiplas instâncias do mesmo jogo via Proton e Gamescope, com perfis independentes e suporte a controles.

## Funcionalidades Principais

- **Co-op Local Avançado:** Execute até duas instâncias do mesmo jogo simultaneamente para uma experiência cooperativa local perfeita.
- **Perfis de Jogo Isolados:** Mantenha saves e configurações independentes para cada jogo através de perfis customizáveis.
- **Flexibilidade de Execução:** Suporte a seleção de qualquer executável `.exe` e diversas versões do Proton, incluindo o GE-Proton.
- **Configuração de Resolução:** Ajuste a resolução para cada instância do jogo individualmente.
- **Depuração Simplificada:** Geração automática de logs para facilitar a identificação e correção de problemas.
- **Mapeamento de Controles:** Configure controles físicos específicos para cada jogador.
- **Compatibilidade Ampla:** Suporte a múltiplos jogos através do sistema de perfis.

## Status do Projeto

- **Funcionalidade Central:** Jogos abrem em instâncias separadas com saves independentes.
- **Desempenho:** Desempenho otimizado para uma experiência de jogo fluida.
- **Gerenciamento de Proton:** Versão do Proton totalmente selecionável, incluindo suporte ao Proton GE.
- **Organização:** Perfis dedicados para cada jogo.

### Problemas Conhecidos

- **Reconhecimento de Controles:** Em alguns casos, os controles podem não ser reconhecidos (prioridade de correção).
- **Disposição de Janelas:** As instâncias podem abrir no mesmo monitor, exigindo movimentação manual.

## Pré-requisitos do Sistema

Para garantir o funcionamento correto do Linux-Coop, os seguintes pré-requisitos são essenciais:

- **Steam:** Deve estar instalado e configurado em seu sistema.
- **Proton:** Instale o Proton (ou GE-Proton) através do Steam.
- **Gamescope:** Instale o Gamescope seguindo as [instruções oficiais](https://github.com/ValveSoftware/gamescope).
- **Bubblewrap (`bwrap`):** Ferramenta essencial para isolamento de processos.
- **Permissões de Dispositivo:** Garanta permissões de acesso aos dispositivos de controle em `/dev/input/by-id/`.
- **Utilitários Linux:** Bash e utilitários básicos do sistema Linux.
- **Python 3.8+:** O projeto requer Python versão 3.8 ou superior.

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Mallor705/Linux-Coop.git
    cd Linux-Coop
    ```
2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

    Alternativamente, se você estiver desenvolvendo ou preferir uma instalação editável:

    ```bash
    pip install -e .
    ```

## Como Usar

### 1. Crie um Perfil de Jogo

Crie um arquivo JSON na pasta `profiles/` com um nome descritivo (ex: `MeuJogo.json`).

**Exemplo de Conteúdo para Splitscreen Horizontal:**

```json
{
  "game_name": "GAME",
  "exe_path": ".steam/Steam/steamapps/common/GAME/game.exe",
  "players": [
    {
      "account_name": "Player1",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000001"
    },
    {
      "account_name": "Player2",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000002"
    }
  ],
  "proton_version": "GE-Proton10-4",
  "instance_width": 1920,
  "instance_height": 1080,
  "player_physical_device_ids": [
    "", 
    ""
  ],
  "player_mouse_event_paths": [
    "",
    ""
  ],
  "player_keyboard_event_paths": [
    "",
    ""
  ],
  "app_id": "12345678",
  "game_args": "",
  "use_goldberg_emu": false,
  "env_vars": {
    "WINEDLLOVERRIDES": "",
    "MANGOHUD": "1"
  },
  "is_native": false,
  "mode": "splitscreen",
  "splitscreen": {
    "orientation": "horizontal",
    "instances": 2
  }
}
```

**Exemplo de Conteúdo para Splitscreen Vertical:**

```json
{
  "game_name": "GAME",
  "exe_path": ".steam/Steam/steamapps/common/GAME/game.exe",
  "players": [
    {
      "account_name": "Player1",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000001"
    },
    {
      "account_name": "Player2",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000002"
    }
  ],
  "proton_version": "GE-Proton10-4",
  "instance_width": 1920,
  "instance_height": 1080,
  "player_physical_device_ids": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],
  "player_mouse_event_paths": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],
  "player_keyboard_event_paths": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],

  "player_audio_device_ids": [
    "",
    ""
  ],
  "app_id": "12345678",
  "game_args": "",
  "use_goldberg_emu": false,
  "env_vars": {
    "WINEDLLOVERRIDES": "",
    "MANGOHUD": "1"
  },
  "is_native": false,
  "mode": "splitscreen",
  "splitscreen": {
    "orientation": "vertical",
    "instances": 2
  }
}
```

### 2. Execute o Script Principal

A partir da raiz do projeto, execute o comando, substituindo `<nome_do_perfil>` pelo nome do arquivo JSON do seu perfil (sem a extensão `.json`):

```bash
python ./linuxcoop.py <nome_do_perfil>
# Ou, se instalado via setuptools:
linux-coop <nome_do_perfil>
```

Ao executar, o script irá:

- Validar todas as dependências necessárias.
- Carregar o perfil de jogo especificado.
- Criar prefixos Proton separados para cada instância do jogo.
- Iniciar as duas janelas do jogo via Gamescope.
- Gerar logs detalhados em `~/.local/share/linux-coop/logs/` para depuração.

### 3. Mapeamento de Controles

- Os controles são configurados no arquivo de perfil ou em arquivos específicos dentro de `controller_config/`.
- Para evitar conflitos, blacklists de controle (ex: `Player1_Controller_Blacklist`) são geradas automaticamente.
- **Importante:** Conecte todos os seus controles físicos antes de iniciar o script.

## Testando a Instalação

Para verificar se os pré-requisitos estão corretamente instalados, execute os seguintes comandos:

```bash
gamescope --version
bwrap --version
```

## Dicas e Solução de Problemas

-   **Controles não reconhecidos:** Verifique as permissões em `/dev/input/by-id/` e confirme se os IDs dos dispositivos estão corretos no seu arquivo de perfil.
-   **Proton não encontrado:** Certifique-se de que o nome da versão do Proton no seu perfil corresponde exatamente ao nome de instalação no Steam.
-   **Instâncias no mesmo monitor:** As instâncias do jogo podem abrir no mesmo monitor. Para movê-las e organizá-las, você pode usar os seguintes atalhos de teclado. **Note que os atalhos podem variar dependendo do seu ambiente de desktop Linux e configurações personalizadas:**
      *   `Super + W` (ou `Ctrl + F9` / `Ctrl + F10`): Exibe uma visão geral de todos os workspaces e janelas abertas (Atividades/Overview), similar a encostar o mouse no canto superior esquerdo.
      *   `Super + Setas (↑ ↓ ← →)`: Move e ajusta a janela ativa para um lado da tela (snapping).
      *   `Super + PgDn`: Minimiza a janela ativa.
      *   `Super + PgUp`: Maximiza a janela ativa.
      *   `Alt + Tab`: Alterna entre as janelas abertas de diferentes aplicativos.
      *   `Super + D`: Minimiza todas as janelas e mostra a área de trabalho.
-   **Logs para depuração:** Consulte o diretório `~/.local/share/linux-coop/logs/` para informações detalhadas sobre erros e o comportamento do script.

## Observações Importantes

-   Testado e otimizado com Palworld, mas pode ser compatível com outros jogos (podendo exigir ajustes no arquivo de perfil).
-   Atualmente, o script suporta apenas a configuração para dois jogadores.
-   Para jogos que não suportam múltiplas instâncias nativamente, pode ser necessário explorar soluções adicionais como sandboxes ou contas Steam separadas.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo `LICENSE` no repositório para mais detalhes.
