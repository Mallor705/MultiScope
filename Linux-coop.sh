#!/bin/bash

# --- Configuração Inicial ---
mkdir -p profiles
mkdir -p "$HOME/.local/share/linux-coop/logs"
mkdir -p "$HOME/.local/share/linux-coop/prefixes"

SCRIPT_NAME=$(basename "$0") # Nome do script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")") # Diretório onde o script está localizado
PROFILE_DIR="${SCRIPT_DIR}/profiles"       # Diretório para guardar os perfis
LOG_DIR="$HOME/.local/share/linux-coop/logs" # Diretório para logs
PREFIX_BASE_DIR="$HOME/.local/share/linux-coop/prefixes" # Base para WINEPREFIXes

# --- Funções Auxiliares ---

# Função para exibir mensagens de log com timestamp
log_message() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Função para encontrar o caminho de instalação do Proton
find_proton_path() {
  local version_string="$1"
  local proton_run_script=""
  local steam_root
  local search_paths=(
    "$HOME/.steam/root"
    "$HOME/.local/share/Steam"
    "$HOME/.steam/steam"
    "$HOME/.steam/debian-installation"
    # Adicione outros caminhos comuns se necessário
    "/var/mnt/games/messi/Games/Steam" # Exemplo do seu script original
  )

  log_message "Procurando por Proton: $version_string"

  for steam_path in "${search_paths[@]}"; do
    if [ ! -d "$steam_path" ]; then continue; fi

    log_message "Verificando diretório Steam: $steam_path"
    steam_root="$steam_path" # Guarda o caminho raiz encontrado

    local potential_path=""
    # Tratamento especial para Experimental
    if [[ "$version_string" == "Experimental" ]]; then
      potential_path=$(find "$steam_path/steamapps/common/" -maxdepth 1 -type d -name "Proton - Experimental" 2>/dev/null | head -n 1)
      if [ -n "$potential_path" ]; then
        proton_run_script="$potential_path/proton"
        break
      fi
    fi

    # Tenta encontrar versões oficiais ou GE
    potential_path=$(find "$steam_path/steamapps/common/" "$steam_path/compatibilitytools.d/" -maxdepth 1 -type d \( -name "Proton $version_string" -o -name "$version_string" \) 2>/dev/null | head -n 1)
     if [ -n "$potential_path" ]; then
        # Verifica se o script 'proton' existe dentro do diretório encontrado
        if [ -f "$potential_path/proton" ]; then
          proton_run_script="$potential_path/proton"
          break
        fi
     fi
  done

  if [ -z "$proton_run_script" ]; then
    log_message "ERRO: Proton '$version_string' não encontrado nos caminhos verificados."
    return 1
  else
    log_message "Proton encontrado: $proton_run_script"
    # Exporta o caminho raiz do Steam para uso no Proton
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$steam_root"
    echo "$proton_run_script" # Retorna o caminho do script 'proton'
    return 0
  fi
}

# Função para limpar processos gamescope/proton relacionados a este jogo
cleanup_previous_instances() {
  local proton_cmd_path="$1"
  local exe_path_pattern="$2" # Usar o caminho do executável para ser mais específico

  log_message "Tentando encerrar instâncias anteriores de '$exe_path_pattern' com '$proton_cmd_path'..."
  # Tenta encontrar e matar processos gamescope que lançaram este jogo específico com este Proton
  # É uma heurística, pode não ser 100% precisa
  pkill -f "gamescope.*-- '$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true
  pkill -f "'$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true # Mata processos Proton órfãos
}

# Função para encerrar as instâncias lançadas por este script
terminate_instances() {
  log_message "Recebido sinal de interrupção. Encerrando instâncias..."
  if [ ${#PIDS[@]} -gt 0 ]; then
    for pid in "${PIDS[@]}"; do
      if ps -p $pid > /dev/null; then
        log_message "Encerrando PID: $pid"
        kill $pid 2>/dev/null
      fi
    done
    sleep 2 # Dá um tempo para os processos fecharem
    for pid in "${PIDS[@]}"; do
       if ps -p $pid > /dev/null; then
         log_message "Forçando encerramento do PID: $pid"
         kill -9 $pid 2>/dev/null
       fi
    done
  fi
  log_message "Limpeza concluída."
  exit 0
}

# --- Verificação de Argumentos e Carregamento do Perfil ---

if [ -z "$1" ]; then
  echo "Uso: $SCRIPT_NAME <nome_do_perfil>"
  echo "Perfis disponíveis em $PROFILE_DIR:"
  ls "$PROFILE_DIR" | sed 's/\.profile$//'
  exit 1
fi

PROFILE_NAME="$1"
PROFILE_FILE="$PROFILE_DIR/$PROFILE_NAME.profile"

if [ ! -f "$PROFILE_FILE" ]; then
  echo "Erro: Arquivo de perfil não encontrado: $PROFILE_FILE"
  echo "Certifique-se de que o perfil '$PROFILE_NAME' existe em $PROFILE_DIR."
  exit 1
fi

log_message "Carregando perfil: $PROFILE_NAME"
# Carrega as variáveis do arquivo de perfil
source "$PROFILE_FILE"

# Validar variáveis obrigatórias do perfil
missing_vars=()
[[ -z "$GAME_NAME" ]] && missing_vars+=("GAME_NAME")
[[ -z "$EXE_PATH" ]] && missing_vars+=("EXE_PATH")
[[ -z "$PROTON_VERSION" ]] && missing_vars+=("PROTON_VERSION")
[[ -z "$NUM_PLAYERS" ]] && missing_vars+=("NUM_PLAYERS")
[[ -z "$INSTANCE_WIDTH" ]] && missing_vars+=("INSTANCE_WIDTH")
[[ -z "$INSTANCE_HEIGHT" ]] && missing_vars+=("INSTANCE_HEIGHT")

if [ ${#missing_vars[@]} -gt 0 ]; then
  echo "Erro: As seguintes variáveis obrigatórias não estão definidas no perfil '$PROFILE_FILE':"
  printf " - %s\n" "${missing_vars[@]}"
  exit 1
fi

# Validar array de controles (obrigatório se NUM_PLAYERS > 0)
if [[ "$NUM_PLAYERS" -gt 0 && ${#CONTROLLER_PATHS[@]} -eq 0 ]]; then
  echo "Erro: A variável 'CONTROLLER_PATHS' (array) é obrigatória no perfil quando NUM_PLAYERS > 0."
  echo "Exemplo: CONTROLLER_PATHS=('/dev/input/by-id/usb-Controller_Vendor_Model_1-event-joystick' '/dev/input/by-id/usb-Controller_Vendor_Model_2-event-joystick')"
  exit 1
fi
if [[ "$NUM_PLAYERS" -gt 0 && ${#CONTROLLER_PATHS[@]} -ne "$NUM_PLAYERS" ]]; then
  echo "Erro: O número de caminhos em 'CONTROLLER_PATHS' (${#CONTROLLER_PATHS[@]}) não corresponde a NUM_PLAYERS ($NUM_PLAYERS)."
  exit 1
fi

# --- Verificações de Dependências ---

log_message "Verificando dependências..."
if ! command -v gamescope &> /dev/null; then
  echo "Erro: 'gamescope' não encontrado. Instale-o (geralmente via gerenciador de pacotes)."
  exit 1
fi

if ! pgrep -x "steam" > /dev/null && ! pgrep -x "steamwebhelper" > /dev/null; then
  log_message "Aviso: Steam não parece estar em execução. Proton pode não funcionar corretamente sem o Steam Runtime."
  # Descomente para iniciar o Steam automaticamente, se desejar
  # log_message "Iniciando Steam..."
  # steam &
  # sleep 10 # Espera um pouco mais para o Steam iniciar completamente
fi

# --- Preparação ---

mkdir -p "$LOG_DIR"
mkdir -p "$PREFIX_BASE_DIR"

PROTON_CMD_PATH=$(find_proton_path "$PROTON_VERSION")
if [ $? -ne 0 ]; then
  exit 1
fi

if [ ! -x "$PROTON_CMD_PATH" ]; then
    log_message "ERRO: O caminho do Proton encontrado não é executável: $PROTON_CMD_PATH"
    exit 1
fi


if [ ! -f "$EXE_PATH" ]; then
  echo "Erro: O arquivo executável do jogo não existe: $EXE_PATH"
  exit 1
fi

# Define o EXE_NAME para logs e nomes de prefixo
EXE_NAME=$(basename "$EXE_PATH")

# Limpa instâncias anteriores deste jogo/proton ANTES de iniciar novas
cleanup_previous_instances "$PROTON_CMD_PATH" "$EXE_PATH"

# Configura o trap para lidar com Ctrl+C e outros sinais de término
declare -a PIDS=() # Array para armazenar PIDs das instâncias
trap terminate_instances SIGINT SIGTERM

# --- Lançamento das Instâncias ---

log_message "Iniciando $NUM_PLAYERS instância(s) de '$GAME_NAME'..."

for (( i=1; i<=NUM_PLAYERS; i++ )); do
  instance_num=$i
  log_message "Preparando instância $instance_num..."

  # Define o diretório do prefixo Wine para esta instância
  prefix_dir="$PREFIX_BASE_DIR/${PROFILE_NAME}_instance_${instance_num}"
  mkdir -p "$prefix_dir/pfx" || { log_message "Erro ao criar diretório do prefixo: $prefix_dir"; terminate_instances; exit 1; }
  log_message "WINEPREFIX para instância $instance_num: $prefix_dir/pfx"

  # Prepara variáveis de ambiente específicas da instância
  export STEAM_COMPAT_DATA_PATH="$prefix_dir"
  export WINEPREFIX="$prefix_dir/pfx"

  # --- Configuração de Input (A parte mais complexa) ---
  current_controller_path=""
  sdl_env_vars=() # Array para guardar variáveis de ambiente SDL

  if [[ $NUM_PLAYERS -gt 0 && $i -le ${#CONTROLLER_PATHS[@]} ]]; then
    controller_index=$((i-1))
    current_controller_path="${CONTROLLER_PATHS[$controller_index]}"
    if [ -e "$current_controller_path" ]; then
      log_message "Instância $instance_num usará o controle: $current_controller_path"
      # Tenta forçar o SDL a usar este dispositivo. A eficácia varia!
      # Usar o caminho completo pode ser mais robusto que apenas o nome.
      sdl_env_vars+=("SDL_JOYSTICK_DEVICE=$current_controller_path")
      # Você também pode tentar configurar o mapeamento diretamente se souber o GUID do SDL
      # sdl_env_vars+=("SDL_GAMECONTROLLERCONFIG=...")
    else
      log_message "Aviso: O caminho do controle '$current_controller_path' para instância $instance_num não existe. Input pode não funcionar como esperado."
    fi
  fi

  # Configuração do Gamescope
  # TODO: Adicionar lógica para posicionar as janelas (ex: lado a lado)
  # Por enquanto, todas iniciam no mesmo lugar (sobrepostas)
  gamescope_pos_x=0
  gamescope_pos_y=$(( (i-1) * INSTANCE_HEIGHT )) # Empilha verticalmente como exemplo simples

  gamescope_cmd=(
    gamescope
    -W "$INSTANCE_WIDTH" -H "$INSTANCE_HEIGHT" # Define resolução interna
    #-w "$INSTANCE_WIDTH" -h "$INSTANCE_HEIGHT" # Define tamanho da janela (se não for fullscreen)
    -o "$gamescope_pos_x","$gamescope_pos_y" # Define a posição da janela na tela principal
    -f # Modo fullscreen (dentro do gamescope, não necessariamente da tela inteira)
    # Opções de Input do Gamescope (EXPERIMENTAIS - verifique a documentação do seu gamescope):
    # --map-device "$current_controller_path=virt-0" # Mapeia dispositivo físico para virtual (se suportado)
    # --filter-device /dev/input/eventX # Filtra outros dispositivos (precisaria listar todos os outros)
    -- # Separador antes do comando a ser executado
  )

  # Prepara o comando Proton
  proton_cmd=(
     "$PROTON_CMD_PATH" run "$EXE_PATH"
     # Adicione aqui quaisquer argumentos de linha de comando específicos do jogo do perfil:
     # $GAME_ARGS
  )

  # Define variáveis de ambiente adicionais para o Proton/Jogo
  export DXVK_ASYNC=1
  export PROTON_LOG=1 # Gera log do proton em $STEAM_COMPAT_DATA_PATH/proton-$PID.log
  export PROTON_LOG_DIR="$LOG_DIR" # Tenta direcionar logs para nosso diretório

  log_file="$LOG_DIR/${PROFILE_NAME}_instance_${instance_num}.log"

  log_message "Comando Gamescope: ${gamescope_cmd[@]}"
  log_message "Comando Proton: ${proton_cmd[@]}"
  log_message "Variáveis SDL: ${sdl_env_vars[@]}"
  log_message "Lançando instância $instance_num (Log: $log_file)..."

  # Executa o comando combinando variáveis de ambiente, gamescope e proton
  # A execução é feita em um subshell para que as variáveis SDL afetem apenas este comando
  (
    # Exporta as variáveis SDL apenas para este subshell/processo
    export "${sdl_env_vars[@]}"
    "${gamescope_cmd[@]}" "${proton_cmd[@]}" > "$log_file" 2>&1
  ) &

  # Captura o PID do processo gamescope (que é o pai direto)
  pid=$!
  PIDS+=($pid)
  log_message "Instância $instance_num iniciada com PID: $pid"

  # Pequeno atraso para estabilidade, especialmente se houver mutexes
  sleep 5
done

# --- Conclusão e Espera ---

log_message "Todas as $NUM_PLAYERS instâncias foram lançadas."
log_message "PIDs: ${PIDS[@]}"
log_message "Pressione CTRL+C neste terminal para encerrar todas as instâncias."

# Mantém o script principal rodando enquanto as instâncias estiverem ativas
# A função 'wait' espera por processos filhos específicos, mas aqui esperamos qualquer um
# O trap cuidará do encerramento. Poderíamos usar 'wait' nos PIDs, mas o trap é mais geral.
while true; do
    all_dead=true
    for pid in "${PIDS[@]}"; do
        if ps -p $pid > /dev/null; then
            all_dead=false
            break
        fi
    done
    if $all_dead; then
        log_message "Todas as instâncias parecem ter sido encerradas."
        break
    fi
    sleep 5 # Verifica a cada 5 segundos
done

log_message "Script concluído."
exit 0
