// Compile: gcc -shared -fPIC -o intercept_workdir.so intercept_workdir.c -ldl

#define _GNU_SOURCE
#include <dlfcn.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/file.h>

// Ponteiros para funções originais
static char* (*original_getcwd)(char*, size_t) = NULL;

// Função para obter o caminho do arquivo de log
char* get_log_path() {
    static char log_path[1024] = {0};
    if (log_path[0] == '\0') {
        const char* home = getenv("HOME");
        if (home == NULL) {
            strcpy(log_path, "/tmp/game_cwd.log");
        } else {
            snprintf(log_path, sizeof(log_path), "%s/game_cwd.log", home);
        }
    }
    return log_path;
}

void __attribute__((constructor)) init() {
    original_getcwd = dlsym(RTLD_NEXT, "getcwd");
}

// Intercept getcwd - apenas uma chamada é logada com lock de arquivo
char* getcwd(char* buf, size_t size) {
    if (!original_getcwd) original_getcwd = dlsym(RTLD_NEXT, "getcwd");

    char* result = original_getcwd(buf, size);

    // Log apenas se for bem-sucedido e se conseguirmos o lock
    if (result) {
        char* log_path = get_log_path();
        int fd = open(log_path, O_CREAT | O_WRONLY | O_TRUNC, 0644);
        if (fd >= 0) {
            // Tentar obter lock exclusivo no arquivo
            if (flock(fd, LOCK_EX | LOCK_NB) == 0) {
                dprintf(fd, "GETCWD: %s\n", result);
                flock(fd, LOCK_UN);
            }
            close(fd);
        }
    }

    return result;
}
