# Mapeamento 2D de posições

Sistema web local em Flask, SQLite, HTML, CSS e JavaScript.

## Windows
Dê dois cliques em `iniciar.bat`.

## Manual
```bash
pip install -r requirements.txt
python app.py
```
Acesse http://127.0.0.1:5000

## Uso
- Selecione o andar.
- Arraste as posições no mapa. A coordenada é salva automaticamente.
- Clique em uma posição para editar equipamento, usuário, inventário e status.
- Use **Nova posição** para incluir uma mesa.
- A busca localiza código, usuário, RACF, hostname, inventário ou área.

Os dados ficam em `inventario.db`, criado automaticamente ao iniciar.

## Importação do Excel
Clique em **Importar Excel**, escolha um arquivo `.xlsx` ou `.xlsm` e importe. O sistema detecta a planilha e o cabeçalho automaticamente. São obrigatórias as colunas **Andar** e **Posição**. Também reconhece Usuário, RACF, Hostname, Inventário, Modelo, IP, Área, Status e Observação. Os dados ficam permanentemente em `inventario.db`. Se Andar + Posição já existirem, os dados são atualizados e as coordenadas 2D são preservadas.
