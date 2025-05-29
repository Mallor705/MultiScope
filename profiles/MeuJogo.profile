# Nome do Jogo
GAME_NAME="Palworld"

# Caminho do Executável
EXE_PATH="/mnt/games/messi/Games/Steam/steamapps/common/Palworld/Palworld.exe"

# Versão do Proton
PROTON_VERSION="GE-Proton10-3"

# Número de jogadores/instâncias
NUM_PLAYERS=2

# Resolução por instância
INSTANCE_WIDTH=1920
INSTANCE_HEIGHT=1080

# --- Configuração InputPlumber ---
# Nome base para os dispositivos virtuais que serão criados
# (Resultará em: virtual-gamepad-p1, virtual-gamepad-p2)
VIRTUAL_DEVICE_BASENAME="virtual-gamepad-p"

# Array com identificadores PERSISTENTES dos controles FÍSICOS
# Use caminhos de /dev/input/by-id/* ou nomes/IDs únicos
PLAYER_PHYSICAL_DEVICE_IDS=(
  "/dev/input/by-id/usb-045e_Gamesir-T4w_1.39-event-joystick" # Jogador 1 
  "/dev/input/by-id/usb-8BitDo_8BitDo_Ultimate_wireless_Controller_for_PC_4057CAD817E4-event-joystick" # Jogador 2
)
# Garantir que a ordem aqui corresponda à ordem dos jogadores

# (Opcional) Argumentos do jogo
GAME_ARGS="-dx12"
