# Linux Local Co-Op with Proton and Gamescope

Este projeto permite executar jogos Windows em modo cooperativo local no Linux utilizando o Proton (via Steam) e o gamescope para gerenciar múltiplas instâncias do jogo.

## Pré-requisitos

- **Steam** instalado e configurado.
- **Gamescope** instalado (veja [instalação oficial](https://github.com/ValveSoftware/gamescope)).
- **Proton** ou **GE-Proton** instalado via Steam (ex: Proton Experimental, GE-Proton9-26).
- **Zenity** (para interfaces gráficas nos scripts).
- Dependências do Wine/Proton (gerenciadores de prefixo, Vulkan, etc.).

---

## Instalação

1. Clone este repositório ou baixe os scripts:
   ```bash
   git clone https://github.com/seu-usuario/linux-coop.git
   cd linux-coop
   ```

2. Dê permissão de execução aos scripts:
   ```bash
   chmod +x Linux-Co-Op_w-gamescope.sh Create-new-profile.sh
   ```

---

## Uso

### Passo 1: Criar um Perfil

Execute o script `Create-new-profile.sh` para configurar um novo perfil:
```bash
./Create-new-profile.sh
```

- **Selecione**:
  - O executável do jogo (.exe).
  - A versão do Proton (ex: Experimental, GE-Proton).
  - A resolução desejada (ex: 1920x1080).
  - Os controladores para cada jogador (conecte-os antes de executar).

Um arquivo de perfil será gerado em `./profiles/`.

---

### Passo 2: Executar o Jogo em Co-Op

Use o script principal para iniciar duas instâncias do jogo:
```bash
./Linux-Co-Op_w-gamescope.sh
```

- O script:
  - Verifica se o Steam está em execução (inicia automaticamente, se necessário).
  - Configura prefixos Wine separados para cada instância.
  - Isola os controladores para evitar conflitos.
  - Usa o gamescope para gerenciar janelas e resoluções.

---

## Configuração de Controladores

- Os controladores são mapeados para cada jogador via arquivos em `./controller_config/`.
- **Importante**: Conecte os controladores antes de executar os scripts.
- Para reconfigurar, exclua a pasta `controller_config` e execute `Create-new-profile.sh` novamente.

---

## Solução de Problemas

### Erro: "Gamescope não está instalado"
- Instale o gamescope seguindo as [instruções oficiais](https://github.com/ValveSoftware/gamescope#packaging).

### Erro: Proton não encontrado
- Verifique se a versão do Proton selecionada está instalada via Steam (ex: em `Steam/steamapps/common/`).

### Controladores não detectados
- Certifique-se de que estão conectados antes de executar o script.
- Verifique permissões de acesso a `/dev/input/by-id/`.

### Instâncias travando ou com baixo desempenho
- Ajuste a resolução no perfil para valores compatíveis com seu hardware.
- Verifique se o DXVK está habilitado (variável `DXVK_ASYNC=1` no script).

---

## Notas

- Testado com **Palworld**, mas pode funcionar com outros jogos (requer configuração manual).
- Para jogos sem suporte nativo a múltiplas instâncias, considere usar sandboxes ou contas separadas.

---

## Licença
