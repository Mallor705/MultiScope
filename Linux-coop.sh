#!/bin/bash
# filepath: /home/mallor/Documentos/GitHub/Linux-Coop/Linux-coop.sh

# INÍCIO DO SCRIPT
# Este script inicia instâncias de um jogo utilizando Proton, InputPlumber e Bubblewrap. 
# Ele lê um perfil com configurações, valida dependências, encontra dispositivos físicos e cria dispositivos virtuais.

# --- Configuração Inicial ---
# Define variáveis de ambiente e diretórios essenciais.
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROFILE_DIR="${SCRIPT_DIR}/profiles"
LOG_DIR="$HOME/.local/share/linux-coop/logs"         # Diretório para arquivos de log
PREFIX_BASE_DIR="$HOME/.local/share/linux-coop/prefixes" # Diretório base para Prefixos (Wine)
# Diretório temporário para configs do InputPlumber geradas por este script
INPUTPLUMBER_TEMP_CONFIG_DIR="/tmp/linux-coop-inputplumber-configs"
INPUTPLUMBER_SERVICE_NAME="inputplumber" # Nome correto do serviço
INPUTPLUMBER_SUSPEND_SERVICE_NAME="inputplumber-suspend" # Nome do serviço de suspensão
INPUTPLUMBER_DBUS_SERVICE="org.shadowblip.InputPlumber"  # Usa a interface padrão do D-Bus
INPUTPLUMBER_DBUS_PATH="/org/shadowblip/InputPlumber/CompositeDevice0"   # Caminho do objeto
# Diretório para configs YAML temporárias do InputPlumber
INPUTPLUMBER_TEMP_YAML_DIR="/tmp/linux-coop-ip-yamls"

# --- Funções Auxiliares ---
# Função para registrar mensagens com timestamp.
log_message() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"  # Imprime a mensagem com data/hora
}

# Função para localizar o script do Proton baseado na versão informada.
find_proton_path() {
  local version_string="$1"
  local proton_run_script=""
  local steam_root
  local search_paths=(
    "$HOME/.steam/root" "$HOME/.local/share/Steam" "$HOME/.steam/steam"
    "$HOME/.steam/debian-installation" "/var/mnt/games/messi/Games/Steam"
  )
  log_message "Procurando por Proton: $version_string"
  for steam_path in "${search_paths[@]}"; do
    [ ! -d "$steam_path" ] && continue
    log_message "Verificando diretório Steam: $steam_path"
    steam_root="$steam_path"
    local potential_path=""
    if [[ "$version_string" == "Experimental" ]]; then
      potential_path=$(find "$steam_path/steamapps/common/" -maxdepth 1 -type d -name "Proton - Experimental" 2>/dev/null | head -n 1)
    else
      potential_path=$(find "$steam_path/steamapps/common/" "$steam_path/compatibilitytools.d/" -maxdepth 1 -type d \( -name "Proton $version_string" -o -name "$version_string" \) 2>/dev/null | head -n 1)
    fi
    if [ -n "$potential_path" ] && [ -f "$potential_path/proton" ]; then
      proton_run_script="$potential_path/proton"
      break
    fi
  done
  if [ -z "$proton_run_script" ]; then
    log_message "ERRO: Proton '$version_string' não encontrado."
    return 1
  fi
  log_message "Proton encontrado: $proton_run_script"
  export STEAM_COMPAT_CLIENT_INSTALL_PATH="$steam_root"
  echo "$proton_run_script"
  return 0
}

# --- Funções de Joystick e Propriedades ---
# Função que procura nós de eventos de joysticks e gamepads (por symlinks em /dev/input/by-id/) e os retorna.
find_joystick_event_nodes() {
    local -n _out_array=$1  # Output array reference
    _out_array=()
    local count=0
    while IFS= read -r line; do
        if [[ $count -lt 2 ]]; then
            local real_dev
            real_dev=$(readlink -f "$line")
            if [[ "$real_dev" == /dev/input/event* ]]; then
                _out_array+=("$real_dev")
                ((count++))
                log_message "Joystick $count encontrado: $line -> $real_dev"
            fi
        else
            break
        fi
    done < <(find /dev/input/by-id/ \( -name '*event-joystick*' -o -name '*joystick*' -o -name '*gamepad*' \) -type l 2>/dev/null | sort)
    log_message "Total de joysticks identificados: ${#_out_array[@]} - ${_out_array[*]}"
    if [[ ${#_out_array[@]} -lt 2 ]]; then
        log_message "ERRO: Menos de 2 joysticks encontrados em /dev/input/by-id/. Verifique se estão conectados."
        return 1
    fi
    return 0
}

# Função que extrai uma propriedade (ex.: NAME, PHYS) de um dispositivo evdev usando udevadm.
get_evdev_property() {
    local event_node="$1"
    local property_name="$2"
    local value
    value=$(udevadm info --query=property --name="$event_node" | grep "^$property_name=" | cut -d'=' -f2)
    value="${value%\"}"
    value="${value#\"}"
    echo "$value"
}

# --- Funções InputPlumber ---
# Função que garante que o serviço InputPlumber esteja ativo.
ensure_inputplumber_running() {
  log_message "Verificando status dos serviços..."
  sudo systemctl enable "$INPUTPLUMBER_SERVICE_NAME" "$INPUTPLUMBER_SUSPEND_SERVICE_NAME" --now || {
    log_message "ERRO: Falha ao iniciar os serviços do InputPlumber."
    exit 1
  }
  log_message "Serviços ativos."
}

# Função que gera um arquivo YAML para definir um dispositivo composto para um jogador.
generate_composite_yaml() {
    local player_num="$1"
    local yaml_file="$2"
    local event_node="$3"
    local match_prop_name="ID_MODEL"
    local match_prop_value
    match_prop_value=$(get_evdev_property "$event_node" "$match_prop_name")
    local virtual_device_name="VirtualCoop_P${player_num}"
    if [ -z "$match_prop_value" ]; then
        log_message "ERRO: Não foi possível obter a propriedade '$match_prop_name' para $event_node."
        return 1
    fi
    log_message "Gerando YAML para Jogador $player_num ($event_node - Nome: '$match_prop_value') em $yaml_file"
    cat > "$yaml_file" << EOF
# yaml-language-server: \$schema=https://raw.githubusercontent.com/ShadowBlip/InputPlumber/main/rootfs/usr/share/inputplumber/schema/composite_device_v1.json
version: 1
kind: CompositeDevice
name: LinuxCoop_Player_${player_num}_Composite
matches: []
source_devices:
  - group: gamepad
    evdev:
      name: "$match_prop_value"
target_devices:
  - gamepad
capability_map_id: "generic"  # Mapeamento genérico
EOF
}

# Função que envia a definição do dispositivo composto via D-Bus para o InputPlumber.
load_composite_device_via_dbus() {
    local yaml_file="$1"
    log_message "Carregando perfil via LoadProfilePath..."
    busctl call "$INPUTPLUMBER_DBUS_SERVICE" \
      "/org/shadowblip/InputPlumber/CompositeDevice0" \
      "org.shadowblip.Input.CompositeDevice" \
      LoadProfilePath "s" "$yaml_file"
    if [ $? -ne 0 ]; then
        log_message "ERRO: Comando busctl para carregar Composite Device falhou para $yaml_file."
        return 1
    fi
    log_message "Solicitação para carregar $yaml_file enviada. Aguarde a criação do dispositivo virtual..."
    sleep 4
    return 0
}

# Função que busca o nó do dispositivo virtual criado pelo InputPlumber.
find_virtual_device_node() {
    local player_num="$1"
    local expected_name="LinuxCoop_Player_${player_num}_Composite"
    local found_path=""
    local attempt=0
    log_message "Procurando por nó de dispositivo virtual com nome contendo '$expected_name'..."
    while [[ $attempt -lt 5 ]]; do
       found_path=$(find /dev/input/event* 2>/dev/null | while IFS= read -r ev_node; do
           if udevadm info --query=property --name="$ev_node" | grep -q "NAME=.*$expected_name"; then
               echo "$ev_node"
               break
           fi
       done)
       if [ -n "$found_path" ]; then
           log_message "Dispositivo virtual encontrado para Jogador $player_num: $found_path"
           echo "$found_path"
           return 0
       fi
       log_message "Tentativa $attempt: Dispositivo virtual para Jogador $player_num não encontrado, aguardando..."
       sleep 2
       ((attempt++))
    done
    log_message "ERRO: Não foi possível encontrar o nó do dispositivo virtual para Jogador $player_num após várias tentativas."
    return 1
}

# Função para descarregar as definições compostas e reiniciar o serviço para limpar as configurações.
unload_composite_definitions() {
    log_message "Tentando descarregar definições de Composite Device..."
    log_message "Removendo arquivos YAML temporários..."
    rm -rf "$INPUTPLUMBER_TEMP_YAML_DIR"
    log_message "Reiniciando serviço $INPUTPLUMBER_SERVICE_NAME para garantir a limpeza..."
    sudo systemctl restart "$INPUTPLUMBER_SERVICE_NAME" || log_message "Aviso: Falha ao reiniciar $INPUTPLUMBER_SERVICE_NAME."
}

# --- Função de Limpeza Geral ---
# Função que encerra instâncias anteriores do jogo, se existirem.
cleanup_previous_instances() {
  local proton_cmd_path="$1"
  local exe_path_pattern="$2"
  log_message "Tentando encerrar instâncias anteriores de '$exe_path_pattern'..."
  pkill -f "gamescope.*-- '$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true
  pkill -f "'$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true
}

# Função que trata a interrupção (Ctrl+C) para finalizar as instâncias e limpar configurações.
terminate_instances() {
  log_message "Recebido sinal de interrupção. Encerrando instâncias..."
  if [ ${#PIDS[@]} -gt 0 ]; then
    log_message "Encerrando PIDs das instâncias: ${PIDS[@]}"
    kill "${PIDS[@]}" 2>/dev/null && sleep 2
    kill -9 "${PIDS[@]}" 2>/dev/null
  fi
  unload_composite_definitions
  log_message "Limpeza concluída."
  exit 0
}

# Nova função para solicitar a senha sudo quando necessário.
prompt_sudo_password() {
  echo "Por favor, insira sua senha de sudo (será solicitada se necessário):"
  sudo -v  # Valida as credenciais sudo
}

# --- Script Principal ---
# Validação de argumentos e carregamento do perfil com as configurações do jogo.
if [ -z "$1" ]; then
  echo "Uso: $SCRIPT_NAME <nome_do_perfil>"  # Exibe mensagem de uso caso nenhum perfil seja informado
  exit 1
fi
PROFILE_NAME="$1"
PROFILE_FILE="$PROFILE_DIR/$PROFILE_NAME.profile"
if [ ! -f "$PROFILE_FILE" ]; then
  echo "Erro: Perfil não encontrado: $PROFILE_FILE"  # Erro se o perfil não existir
  exit 1
fi

log_message "Carregando perfil: $PROFILE_NAME"
source "$PROFILE_FILE"  # Carrega o perfil contendo variáveis de configuração

# Validação das variáveis obrigatórias definidas no perfil
missing_vars=()
[[ -z "$GAME_NAME" ]] && missing_vars+=("GAME_NAME")
[[ -z "$EXE_PATH" ]] && missing_vars+=("EXE_PATH")
[[ -z "$PROTON_VERSION" ]] && missing_vars+=("PROTON_VERSION")
[[ -z "$NUM_PLAYERS" ]] && missing_vars+=("NUM_PLAYERS")
[[ -z "$INSTANCE_WIDTH" ]] && missing_vars+=("INSTANCE_WIDTH")
[[ -z "$INSTANCE_HEIGHT" ]] && missing_vars+=("INSTANCE_HEIGHT")
[[ -z "$VIRTUAL_DEVICE_BASENAME" ]] && missing_vars+=("VIRTUAL_DEVICE_BASENAME")
[[ ${#PLAYER_PHYSICAL_DEVICE_IDS[@]} -eq 0 && "$NUM_PLAYERS" -gt 0 ]] && missing_vars+=("PLAYER_PHYSICAL_DEVICE_IDS (array não pode ser vazio para NUM_PLAYERS > 0)")
[[ ${#PLAYER_PHYSICAL_DEVICE_IDS[@]} -ne "$NUM_PLAYERS" && "$NUM_PLAYERS" -gt 0 ]] && missing_vars+=("Número de elementos em PLAYER_PHYSICAL_DEVICE_IDS (${#PLAYER_PHYSICAL_DEVICE_IDS[@]}) diferente de NUM_PLAYERS ($NUM_PLAYERS)")

if [ ${#missing_vars[@]} -gt 0 ]; then
  echo "Erro: Variáveis obrigatórias faltando no perfil:"
  printf " - %s\n" "${missing_vars[@]}"
  exit 1
fi

if [ "$NUM_PLAYERS" -ne 2 ]; then
    log_message "ERRO: Este script está atualmente configurado para exatamente 2 jogadores."
    exit 1
fi

# Verifica se as dependências (gamescope, bwrap, udevadm, busctl) estão instaladas.
log_message "Verificando dependências..."
command -v gamescope &> /dev/null || { echo "Erro: 'gamescope' não encontrado."; exit 1; }
command -v bwrap &> /dev/null || { echo "Erro: 'bwrap' (bubblewrap) não encontrado."; exit 1; }
command -v udevadm &> /dev/null || { echo "Erro: 'udevadm' não encontrado."; exit 1; }
command -v busctl &> /dev/null || { echo "Erro: 'busctl' não encontrado."; exit 1; }
log_message "Dependências verificadas com sucesso."

prompt_sudo_password  # Solicita a senha do usuário para executar comandos com sudo

# Criação dos diretórios necessários (logs, prefixos, configs temporárias)
mkdir -p "$LOG_DIR"
mkdir -p "$PREFIX_BASE_DIR"
mkdir -p "$INPUTPLUMBER_TEMP_CONFIG_DIR" || { echo "ERRO: Não foi possível criar diretório temporário para InputPlumber: $INPUTPLUMBER_TEMP_CONFIG_DIR"; exit 1; }
mkdir -p "$INPUTPLUMBER_TEMP_YAML_DIR" || { echo "ERRO: Não foi possível criar diretório temporário $INPUTPLUMBER_TEMP_YAML_DIR"; exit 1; }

# Localiza o script do Proton com base na versão informada
PROTON_CMD_PATH=$(find_proton_path "$PROTON_VERSION") || exit 1 
[ ! -f "$EXE_PATH" ] && { echo "Erro: Executável do jogo não existe: $EXE_PATH"; exit 1; }
EXE_NAME=$(basename "$EXE_PATH") 

# Verifica novamente a existência do executável do jogo
if [ ! -f "$EXE_PATH" ]; then
    echo "Erro: Executável do jogo não encontrado em: $EXE_PATH"
    exit 1
fi

# --- Encontrar Joysticks Físicos ---
# Busca os nós de eventos de joysticks necessários para criar os dispositivos virtuais.
declare -a PHYSICAL_EVENT_NODES
find_joystick_event_nodes PHYSICAL_EVENT_NODES || exit 1

# Garante que o InputPlumber esteja rodando antes de configurar os dispositivos.
ensure_inputplumber_running

# Prepara os arquivos YAML e obtém os nós dos dispositivos virtuais para cada jogador.
declare -a TEMP_YAML_FILES
declare -a VIRTUAL_DEVICE_NODES
for p_idx in 0 1; do
    player_num=$((p_idx + 1))
    event_node="${PHYSICAL_EVENT_NODES[$p_idx]}"
    yaml_file="$INPUTPLUMBER_TEMP_YAML_DIR/player_${player_num}.yaml"
    TEMP_YAML_FILES+=("$yaml_file")
    generate_composite_yaml "$player_num" "$yaml_file" "$event_node" || { unload_composite_definitions; exit 1; }
    load_composite_device_via_dbus "$yaml_file" || { unload_composite_definitions; exit 1; }
    virt_node=$(find_virtual_device_node "$player_num") || { unload_composite_definitions; exit 1; }
    VIRTUAL_DEVICE_NODES+=("$virt_node")
done
if [ ${#VIRTUAL_DEVICE_NODES[@]} -ne 2 ]; then
   log_message "ERRO: Número incorreto de dispositivos virtuais encontrados (${#VIRTUAL_DEVICE_NODES[@]})."
   unload_composite_definitions
   exit 1
fi

# Finaliza instâncias anteriores do jogo para evitar conflitos.
cleanup_previous_instances "$PROTON_CMD_PATH" "$EXE_PATH"

# Declaração do array que armazenará os PIDs das instâncias iniciadas
declare -a PIDS=()
# Configura a captura de sinais (Ctrl+C) e direciona para a limpeza
trap terminate_instances SIGINT SIGTERM

log_message "Iniciando $NUM_PLAYERS instância(s) de '$GAME_NAME' usando InputPlumber e Bubblewrap..."

# --- Lançamento das Instâncias ---
# Loop que prepara e inicia as instâncias do jogo para cada jogador.
for (( i=1; i<=NUM_PLAYERS; i++ )); do
  instance_num=$i
  player_index=$((i-1))
  log_message "Preparando instância $instance_num..."

  prefix_dir="$PREFIX_BASE_DIR/${PROFILE_NAME}_instance_${instance_num}"
  mkdir -p "$prefix_dir/pfx" || { log_message "Erro ao criar diretório do prefixo: $prefix_dir"; terminate_instances; exit 1; }
  log_message "WINEPREFIX para instância $instance_num: $prefix_dir/pfx"

  # Mapeia o dispositivo virtual obtido para uso dentro do sandbox
  current_virtual_device_node="${VIRTUAL_DEVICE_NODES[$player_index]}"
  log_message "Instância $instance_num usará o dispositivo virtual: $current_virtual_device_node"

  # Monta o comando Bubblewrap (bwrap) com os binds e configurações necessárias
  bwrap_cmd=(
    bwrap
    --unshare-all --share-net
    --proc /proc --dev /dev
    --dev-bind /dev/dri /dev/dri
    --dev-bind /dev/snd /dev/snd
    --ro-bind /dev/shm /dev/shm
    --ro-bind /etc/machine-id /etc/machine-id
    --ro-bind /var/lib/dbus /var/lib/dbus
    --bind /tmp/.X11-unix /tmp/.X11-unix
    --bind "$XDG_RUNTIME_DIR/pulse" "$XDG_RUNTIME_DIR/pulse"
    "--dev-bind" "$current_virtual_device_node" "/dev/input/event0"
    --ro-bind /usr /usr
    --bind "$prefix_dir" "$prefix_dir"
    --bind "$HOME" "$HOME"
    --bind "$(dirname "$EXE_PATH")" "$(dirname "$EXE_PATH")"
    --bind "$(dirname "$PROTON_CMD_PATH")/../../.." "$(dirname "$PROTON_CMD_PATH")/../../.."
    --setenv STEAM_COMPAT_DATA_PATH "$prefix_dir"
    --setenv WINEPREFIX "$prefix_dir/pfx"
    --setenv DXVK_ASYNC "1"
    --setenv PROTON_LOG "1"
    --setenv PROTON_LOG_DIR "$LOG_DIR"
  )

  # Configura o comando gamescope para resolução e tela cheia.
  gamescope_cmd=(
    gamescope
    -W "$INSTANCE_WIDTH" -H "$INSTANCE_HEIGHT" -f
    -- 
  )

  # Define o comando do Proton para executar o jogo.
  proton_cmd=(
    "$PROTON_CMD_PATH" run "$EXE_PATH"
  )

  log_file="$LOG_DIR/${PROFILE_NAME}_instance_${instance_num}.log"
  log_message "Lançando instância $instance_num (Log: $log_file)..."

  # Executa o comando completo unindo bwrap, gamescope e proton; redireciona a saída para o log.
  "${bwrap_cmd[@]}" "${gamescope_cmd[@]}" "${proton_cmd[@]}" > "$log_file" 2>&1 &
  pid=$!
  PIDS+=($pid)
  log_message "Instância $instance_num iniciada com PID: $pid"
  sleep 5  # Aguarda um breve momento para evitar sobrecarga
done

# Exibe mensagem informando que todas as instâncias foram lançadas e mostra os PIDs.
log_message "Todas as $NUM_PLAYERS instâncias foram lançadas."
log_message "PIDs: ${PIDS[@]}"
log_message "Pressione CTRL+C neste terminal para encerrar todas as instâncias e liberar os controles."

# Loop de monitoramento: aguarda o término das instâncias.
while true; do
    all_dead=true
    for pid in "${PIDS[@]}"; do
        [ -e "/proc/$pid" ] && all_dead=false && break
    done
    if $all_dead; then
      log_message "Todas as instâncias parecem ter sido encerradas."
      break
    fi
    sleep 5
done

# Limpa as definições compostas do InputPlumber e finaliza o script.
unload_composite_definitions
log_message "Script concluído."
exit 0