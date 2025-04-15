# Nome do Jogo (para logs e diretórios)
GAME_NAME="Meu Jogo Incrível"

# Caminho COMPLETO para o executável principal do jogo
EXE_PATH="/path/to/your/steamapps/common/Meu Jogo Incrível/Binaries/Win64/MeuJogo-Win64-Shipping.exe"

# Versão do Proton a ser usada (Ex: "8.0-5", "GE-Proton8-25", "Experimental")
PROTON_VERSION="GE-Proton8-25"

# Número de jogadores/instâncias
NUM_PLAYERS=2

# Resolução para CADA instância dentro do gamescope
INSTANCE_WIDTH=960
INSTANCE_HEIGHT=1080 # Ex: Para tela dividida verticalmente em um monitor 1920x1080

# Array com os caminhos dos dispositivos de controle para cada jogador
# Use 'evtest' ou olhe em /dev/input/by-id/ para encontrar os caminhos persistentes!
CONTROLLER_PATHS=(
  "/dev/input/by-id/usb-Sony_Interactive_Entertainment_Wireless_Controller-event-joystick" # Jogador 1
  "/dev/input/by-id/usb-Microsoft_X-Box_360_pad_12345678-event-joystick" # Jogador 2
)

# (Opcional) Argumentos adicionais para passar para o executável do jogo
# GAME_ARGS="-nologin -windowed"
