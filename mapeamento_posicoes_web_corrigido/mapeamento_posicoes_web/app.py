from flask import Flask, render_template, request, jsonify
import sqlite3, io, unicodedata
from pathlib import Path
from openpyxl import load_workbook

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
DB = Path(__file__).with_name('inventario.db')

CAMPOS = ['andar','codigo','usuario','racf','hostname','inventario','modelo','ip','area','status','observacao']
ALIASES = {
 'andar':['andar','piso'], 'codigo':['posicao','posição','codigo','código','posto','mesa'],
 'usuario':['usuario','usuário','nome'], 'racf':['racf','funcional'],
 'hostname':['hostname','host','nome do computador'], 'inventario':['inventario','inventário','patrimonio','patrimônio'],
 'modelo':['modelo','modelo equipamento','equipamento'], 'ip':['ip','endereco ip','endereço ip'],
 'area':['area','área','setor'], 'status':['status','situacao','situação'],
 'observacao':['observacao','observação','obs']}

def norm(v):
    s='' if v is None else str(v).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn').rstrip(':')

def conectar():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def iniciar_banco():
    with conectar() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS posicoes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, andar TEXT NOT NULL, codigo TEXT NOT NULL,
          x REAL NOT NULL DEFAULT 100, y REAL NOT NULL DEFAULT 100,
          largura REAL NOT NULL DEFAULT 120, altura REAL NOT NULL DEFAULT 72,
          usuario TEXT DEFAULT '', racf TEXT DEFAULT '', hostname TEXT DEFAULT '', inventario TEXT DEFAULT '',
          modelo TEXT DEFAULT '', ip TEXT DEFAULT '', area TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'Livre',
          observacao TEXT DEFAULT '', UNIQUE(andar,codigo));
        CREATE TABLE IF NOT EXISTS importacoes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, arquivo TEXT NOT NULL, planilha TEXT NOT NULL,
          importados INTEGER NOT NULL, atualizados INTEGER NOT NULL, ignorados INTEGER NOT NULL,
          criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        ''')

def achar_cabecalho(ws):
    melhor=None
    alias_norm={a:campo for campo,als in ALIASES.items() for a in map(norm,als)}
    for n,row in enumerate(ws.iter_rows(min_row=1,max_row=min(ws.max_row,30),values_only=True),1):
        mapa={}
        for i,v in enumerate(row):
            campo=alias_norm.get(norm(v))
            if campo and campo not in mapa: mapa[campo]=i
        if not melhor or len(mapa)>len(melhor[1]): melhor=(n,mapa)
    return melhor if melhor and 'andar' in melhor[1] and 'codigo' in melhor[1] else None

@app.route('/')
def inicio(): return render_template('index.html')

@app.get('/api/posicoes')
def listar():
    andar=request.args.get('andar','').strip(); busca=request.args.get('busca','').strip()
    sql='SELECT * FROM posicoes WHERE 1=1'; args=[]
    if andar: sql+=" AND TRIM(andar)=?"; args.append(andar)
    if busca:
        termo=f'%{busca}%'; sql+=' AND (codigo LIKE ? OR usuario LIKE ? OR racf LIKE ? OR hostname LIKE ? OR inventario LIKE ? OR area LIKE ?)'; args += [termo]*6
    with conectar() as con: return jsonify([dict(r) for r in con.execute(sql+' ORDER BY andar,codigo',args)])

@app.get('/api/andares')
def andares():
    with conectar() as con: return jsonify([dict(r) for r in con.execute("SELECT TRIM(andar) AS nome, COUNT(*) AS quantidade FROM posicoes WHERE TRIM(andar) <> '' GROUP BY TRIM(andar) ORDER BY TRIM(andar)")])

@app.get('/api/importacoes')
def importacoes():
    with conectar() as con: return jsonify([dict(r) for r in con.execute('SELECT * FROM importacoes ORDER BY id DESC LIMIT 10')])

@app.post('/api/importar')
def importar():
    arq=request.files.get('arquivo')
    if not arq or not arq.filename: return jsonify(erro='Selecione um arquivo Excel.'),400
    if Path(arq.filename).suffix.lower() not in ('.xlsx','.xlsm'): return jsonify(erro='Use um arquivo .xlsx ou .xlsm.'),400
    try:
        wb=load_workbook(io.BytesIO(arq.read()),read_only=True,data_only=True)
    except Exception: return jsonify(erro='Não foi possível ler o arquivo Excel.'),400
    nome=request.form.get('planilha','').strip(); ws=wb[nome] if nome in wb.sheetnames else None
    if ws is None:
        for cand in wb.worksheets:
            if achar_cabecalho(cand): ws=cand; break
    if ws is None: return jsonify(erro='Nenhuma planilha com as colunas Andar e Posição foi encontrada.'),400
    achado=achar_cabecalho(ws)
    if not achado: return jsonify(erro='Cabeçalho não reconhecido. Inclua ao menos Andar e Posição.'),400
    linha_cab,mapa=achado; novos=atualizados=ignorados=0
    with conectar() as con:
        for row in ws.iter_rows(min_row=linha_cab+1,values_only=True):
            d={c: (row[i] if i<len(row) else None) for c,i in mapa.items()}
            andar=str(d.get('andar') or '').strip(); codigo=str(d.get('codigo') or '').strip()
            if not andar or not codigo: ignorados+=1; continue
            dados={c:str(d.get(c) or '').strip() for c in CAMPOS}; dados['andar']=andar; dados['codigo']=codigo
            if dados['status'] not in ('Livre','Ocupada','Manutenção'): dados['status']='Ocupada' if dados['usuario'] or dados['hostname'] else 'Livre'
            ant=con.execute('SELECT id FROM posicoes WHERE andar=? AND codigo=?',(andar,codigo)).fetchone()
            if ant:
                sets=', '.join(f'{c}=?' for c in CAMPOS if c not in ('andar','codigo'))
                vals=[dados[c] for c in CAMPOS if c not in ('andar','codigo')]
                con.execute(f'UPDATE posicoes SET {sets} WHERE id=?',vals+[ant['id']]); atualizados+=1
            else:
                i=novos; x=60+(i%5)*155; y=70+(i//5)*105
                cols=','.join(CAMPOS)+',x,y'; marks=','.join('?' for _ in CAMPOS)+',?,?'
                con.execute(f'INSERT INTO posicoes ({cols}) VALUES ({marks})',[dados[c] for c in CAMPOS]+[x,y]); novos+=1
        con.execute('INSERT INTO importacoes (arquivo,planilha,importados,atualizados,ignorados) VALUES (?,?,?,?,?)',(Path(arq.filename).name,ws.title,novos,atualizados,ignorados))
    return jsonify(arquivo=Path(arq.filename).name,planilha=ws.title,importados=novos,atualizados=atualizados,ignorados=ignorados)

@app.post('/api/posicoes')
def criar():
    d=request.get_json(force=True)
    try:
        with conectar() as con:
            cur=con.execute('INSERT INTO posicoes (andar,codigo,x,y,status) VALUES (?,?,?,?,?)',(d['andar'],d['codigo'].strip(),float(d.get('x',100)),float(d.get('y',100)),d.get('status','Livre')))
            item=con.execute('SELECT * FROM posicoes WHERE id=?',(cur.lastrowid,)).fetchone()
        return jsonify(dict(item)),201
    except (KeyError,ValueError): return jsonify(erro='Dados inválidos.'),400
    except sqlite3.IntegrityError: return jsonify(erro='Já existe essa posição neste andar.'),409

@app.put('/api/posicoes/<int:pid>')
def atualizar(pid):
    d=request.get_json(force=True); campos=['andar','codigo','x','y','largura','altura','usuario','racf','hostname','inventario','modelo','ip','area','status','observacao']; valores={k:d[k] for k in campos if k in d}
    if not valores:return jsonify(erro='Nenhum dado recebido.'),400
    try:
        with conectar() as con:
            con.execute('UPDATE posicoes SET '+', '.join(f'{k}=?' for k in valores)+' WHERE id=?',[*valores.values(),pid]); item=con.execute('SELECT * FROM posicoes WHERE id=?',(pid,)).fetchone()
        return jsonify(dict(item)) if item else (jsonify(erro='Posição não encontrada.'),404)
    except sqlite3.IntegrityError:return jsonify(erro='Código duplicado neste andar.'),409

@app.delete('/api/posicoes/<int:pid>')
def excluir(pid):
    with conectar() as con: con.execute('DELETE FROM posicoes WHERE id=?',(pid,))
    return '',204

if __name__=='__main__': iniciar_banco(); app.run(host='127.0.0.1',port=5000,debug=False)
