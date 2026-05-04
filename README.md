# EvoNexus Log Viewer

Micro-servidor HTTP para visualizar logs de rotinas do EvoNexus. Roda na porta 8082, zero dependências externas.

## Iniciar

```bash
chmod +x /home/evonexus/evo-projects/log-viewer/start.sh
/home/evonexus/evo-projects/log-viewer/start.sh
```

Acesse: http://localhost:8082 ou http://nexus.myworkhome.com.br:8082

## Parar

```bash
/home/evonexus/evo-projects/log-viewer/stop.sh
```

## Iniciar manualmente (foreground, para debug)

```bash
python3 /home/evonexus/evo-projects/log-viewer/server.py
```

## Rotas

| Rota | Descrição |
|------|-----------|
| `GET /` | Lista de execuções do dia. Parâmetros: `?date=YYYY-MM-DD`, `?routine=nome` |
| `GET /detail/<arquivo>.log` | Conteúdo formatado de um arquivo de detalhe |
| `GET /health` | `{"status": "ok"}` |

## Adicionar no painel Systems do EvoNexus

No dashboard do EvoNexus, adicione um link externo apontando para:

```
http://localhost:8082
```

Ou, se acessado remotamente:

```
http://nexus.myworkhome.com.br:8082
```

## Logs do servidor

```bash
tail -f /home/evonexus/evo-projects/log-viewer/log-viewer.out
```

## Auto-start via systemd (recomendado)

```bash
sudo cp /home/evonexus/evo-projects/log-viewer/log-viewer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable log-viewer
sudo systemctl start log-viewer
```

## Auto-start via crontab (alternativa)

```bash
crontab -e
# Linha a adicionar:
@reboot /home/evonexus/evo-projects/log-viewer/start.sh
```
