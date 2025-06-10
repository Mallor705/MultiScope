#!/usr/bin/env python3
"""
Teste independente para a funcionalidade de prompt sudo com zenity.
Este script testa apenas a parte de autenticação sudo sem executar o jogo.
"""

import shutil
import subprocess
import sys

def test_sudo_prompt():
    """Testa o prompt sudo com zenity, similar ao usado no Linux-Coop."""
    print("=== Teste de Prompt Sudo com Zenity ===\n")
    
    # Verifica se zenity está disponível
    zenity_available = shutil.which('zenity') is not None
    print(f"Zenity disponível: {'Sim' if zenity_available else 'Não'}")
    
    # Primeiro verifica se já tem privilégios sudo válidos
    try:
        subprocess.run(['sudo', '-n', 'true'], check=True, capture_output=True)
        print("✓ Sudo já está válido, não precisa solicitar senha.")
        return True
    except subprocess.CalledProcessError:
        print("⚠ Sudo não está válido, precisando solicitar senha...")
    
    # Tenta usar zenity para interface gráfica
    if zenity_available:
        try:
            print("\n🖥️ Testando interface gráfica com zenity...")
            result = subprocess.run([
                'zenity', '--password', 
                '--title=Teste Linux-Coop', 
                '--text=Digite sua senha sudo para testar:'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                password = result.stdout.strip()
                print("✓ Senha recebida via zenity")
                
                # Testa a senha com sudo
                print("🔐 Validando senha...")
                sudo_process = subprocess.Popen(
                    ['sudo', '-S', 'true'], 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = sudo_process.communicate(input=password + '\n')
                
                if sudo_process.returncode == 0:
                    print("✅ Senha válida! Teste bem-sucedido.")
                    return True
                else:
                    print("❌ Senha inválida!")
                    return False
            else:
                print("❌ Diálogo cancelado pelo usuário")
                return False
                
        except Exception as e:
            print(f"❌ Erro com zenity: {e}")
            print("📋 Tentando fallback para terminal...")
    
    # Fallback para prompt de terminal
    try:
        print("\n💻 Usando prompt de terminal...")
        subprocess.run(['sudo', '-v'], check=True)
        print("✅ Senha validada via terminal!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Falha na validação sudo via terminal")
        return False
    except FileNotFoundError:
        print("❌ Comando 'sudo' não encontrado!")
        return False

def main():
    """Função principal do teste."""
    print("Este script testa a funcionalidade de prompt sudo do Linux-Coop.\n")
    
    success = test_sudo_prompt()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 TESTE PASSOU! A funcionalidade sudo está funcionando.")
    else:
        print("💥 TESTE FALHOU! Verifique os erros acima.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())