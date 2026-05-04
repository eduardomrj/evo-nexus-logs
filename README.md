# EvoNexus Log Viewer

Micro-servidor HTTP para visualizar logs de rotinas do EvoNexus. Roda na porta 8082, zero dependências externas.

## Iniciar

```bash
chmod +x /home/evonexus/evo-projects/log-viewer/start.sh
/home/evonexus/evo-projects/log-viewer/start.sh
```

Com o `start.sh` (ou systemd), o prefixo padrão é `BASE_PATH=/log-viewer`. Acesse: `http://127.0.0.1:8082/log-viewer/` (ou o host público equivalente). Se rodar só `python3 server.py` sem variáveis, o prefixo padrão no código é `/logs`.

## Parar

```bash
/home/evonexus/evo-projects/log-viewer/stop.sh
```

## Iniciar manualmente (foreground, para debug)

```bash
python3 /home/evonexus/evo-projects/log-viewer/server.py
```

## Rotas

Todas as rotas abaixo ficam sob o prefixo `BASE_PATH` (ex.: `/log-viewer`).

| Rota | Descrição |
|------|-----------|
| `GET ${BASE_PATH}/` | Lista de execuções do dia. Parâmetros: `?date=YYYY-MM-DD`, `?routine=nome` |
| `GET ${BASE_PATH}/detail/<arquivo>.log` | Conteúdo formatado de um arquivo de detalhe |
| `GET ${BASE_PATH}/health` | `{"status": "ok"}` |

## Adicionar no painel Systems do EvoNexus

No dashboard do EvoNexus, adicione um link externo apontando para:

```
http://localhost:8082/log-viewer/
```

Ou, se acessado remotamente (ajuste host e porta conforme o proxy):

```
http://nexus.myworkhome.com.br:8082/log-viewer/
```

## Logs do servidor

```bash
tail -f /home/evonexus/evo-projects/log-viewer/log-viewer.out
```

## systemd (recomendado)

```bash
sudo ./systemd/INSTALL.sh     # instala log-viewer.service, enable + start
sudo ./systemd/UNINSTALL.sh   # remove a unidade
journalctl -u log-viewer.service -f
```

A unidade usa `Type=forking`, `PIDFile`, `start.sh`, `User=evonexus` e variáveis `BASE_PATH`, `LOG_VIEWER_PORT`, `LOG_VIEWER_HOST`. Ajuste caminhos em `systemd/log-viewer.service` se o projecto não estiver em `/home/evonexus/evo-projects/log-viewer`.

Variáveis opcionais no ambiente ou na unidade: `LOG_VIEWER_LOGS_DIR` (pasta dos logs EvoNexus), `LOG_VIEWER_PYTHON`.

## Auto-start via crontab (alternativa)

```bash
crontab -e
# Linha a adicionar:
@reboot /home/evonexus/evo-projects/log-viewer/start.sh
```
