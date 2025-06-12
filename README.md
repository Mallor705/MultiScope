# Linux-Coop

Permite jogar títulos Windows em modo cooperativo local no Linux, rodando múltiplas instâncias do mesmo jogo via Proton e gamescope, com perfis independentes e suporte a controles.

## Funcionalidades

- Executa duas instâncias do mesmo jogo simultaneamente (co-op local).
- Perfis separados para cada jogo, com saves e configurações independentes.
- Seleção de qualquer executável `.exe` e versão do Proton (incluindo GE-Proton).
- Resolução customizável por instância.
- Logs automáticos para depuração.
- Mapeamento de controles físicos para cada jogador.
- Suporte a múltiplos jogos via perfis.

## Status

- Jogos abrem em duas instâncias e saves são separados.
- Coop funcional.
- Desempenho esperado.
- Versão do Proton é selecionável.
- Suporte ao Proton GE.
- Perfis para cada jogo.
- **Problemas conhecidos:**
  - Controles podem não ser reconhecidos em alguns casos (prioridade de correção).
  - Instâncias abrem no mesmo monitor (mover manualmente se necessário).

## Pré-requisitos

- **Steam** instalado e configurado.
- **Proton** (ou GE-Proton) instalado via Steam.
- **Gamescope** instalado ([instruções oficiais](https://github.com/ValveSoftware/gamescope)).
- **Bubblewrap** (`bwrap`).
- Permissões para acessar dispositivos de controle em `/dev/input/by-id/`.
- Bash, utilitários básicos do Linux.

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/Mallor705/Linux-Coop.git
   cd Linux-Coop
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Como executar corretamente

Para evitar erros de importação relativa, execute o comando principal da seguinte forma, a partir da raiz do projeto:

```bash
python ./linuxcoop.py <nome_do_perfil>
```

Certifique-se de que o diretório `src` está presente e que o Python está na versão correta.

## Como Usar

### 1. Configure um perfil de jogo

Crie um arquivo JSON em `profiles/` com o nome desejado. Exemplo: `MeuJogo.json`.

Exemplo de conteúdo:
```json
{
  "game_name": "GAME",
  "exe_path": ".steam/Steam/steamapps/common/GAME/game.exe",
  "players": [
    {
      "account_name": "Player1",
      "language": "brazilian",
      "listen_port": "47584",
      "user_steam_id": "76561190000000001"
    },
    {
      "account_name": "Player2",
      "language": "brazilian",
      "listen_port": "47584",
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
  "USE_GOLDBERG_EMULATOR": false,
  "ENV_VARS": {
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

### 2. Execute o script principal

```bash
python ./linuxcoop.py MeuJogo
```
- O script irá:
  - Validar dependências.
  - Carregar o perfil.
  - Criar prefixos separados para cada instância.
  - Iniciar duas janelas do jogo via gamescope.
  - Gerar logs em `~/.local/share/linux-coop/logs/`.

### 3. Mapeamento de controles

- Os controles são definidos no perfil ou em arquivos dentro de `controller_config/`.
- Para evitar conflitos, blacklists são criados automaticamente (exemplo: `Player1_Controller_Blacklist`).
- Certifique-se de conectar os controles antes de iniciar o script.

## Testando a Instalação

### Verificação de Dependências
```bash
# Verificar se todas as dependências estão instaladas
gamescope --version
bwrap --version
```

## Dicas e Solução de Problemas

- **Controles não reconhecidos:** Verifique permissões em `/dev/input/by-id/` e IDs corretos no perfil.
- **Proton não encontrado:** Confirme o nome e instalação da versão desejada no Steam.
- **Instâncias no mesmo monitor:** Mova manualmente cada janela para o monitor desejado.
- **Logs:** Consulte `~/.local/share/linux-coop/logs/` para depuração.

## Observações

- Testado com Palworld, mas pode funcionar com outros jogos (pode exigir ajustes no perfil).
- O script atualmente suporta apenas dois jogadores.
- Para jogos que não suportam múltiplas instâncias, pode ser necessário usar sandboxes ou contas Steam separadas.

## Licença

Consulte o arquivo LICENSE (se houver) ou o repositório para detalhes.
