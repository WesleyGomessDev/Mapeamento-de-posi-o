const $=s=>document.querySelector(s);let itens=[],arrastando=null,dx=0,dy=0,moved=false;
const campos=['andar','codigo','status','usuario','racf','area','hostname','inventario','modelo','ip','observacao'];
function toast(t){$('#toast').textContent=t;$('#toast').classList.add('on');setTimeout(()=>$('#toast').classList.remove('on'),2200)}
async function api(url,opt={}){let r=await fetch(url,{headers:{'Content-Type':'application/json'},...opt});if(!r.ok){let e=await r.json().catch(()=>({erro:'Erro inesperado'}));throw Error(e.erro)}return r.status===204?null:r.json()}
let requisicaoMapa=0;
async function carregarAndares(preferido=null){
  const select=$('#andar');
  const anterior=preferido ?? select.value;
  const andares=await api('/api/andares');
  select.innerHTML='<option value="">Todos os andares</option>'+andares.map(a=>`<option value="${escapeHtml(a.nome)}">${escapeHtml(a.nome)} (${a.quantidade})</option>`).join('');
  if([...select.options].some(o=>o.value===anterior)) select.value=anterior;
  await carregar();
}
function escapeHtml(v){return String(v).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function carregar(){
  const numero=++requisicaoMapa;
  const andar=$('#andar').value.trim();
  const busca=$('#busca').value.trim();
  const q=new URLSearchParams();
  if(andar) q.set('andar',andar);
  if(busca) q.set('busca',busca);
  try{
    const resultado=await api('/api/posicoes?'+q.toString());
    if(numero!==requisicaoMapa) return;
    itens=resultado; render();
  }catch(e){if(numero===requisicaoMapa) toast(e.message)}
}
function render(){let mapa=$('#mapa');mapa.innerHTML='';itens.forEach(p=>{let d=document.createElement('div');d.className='posicao';d.dataset.id=p.id;d.dataset.status=p.status;d.style.cssText=`left:${p.x}px;top:${p.y}px;width:${p.largura}px;height:${p.altura}px`;d.innerHTML=`<b>${p.codigo}</b><span>${p.usuario||p.status}</span><span>${p.hostname||p.inventario||''}</span>`;d.onpointerdown=e=>inicioArraste(e,p,d);d.onclick=()=>{if(!moved)abrir(p)};mapa.appendChild(d)});$('#contador').textContent=`${itens.length} posições`;$('#tituloAndar').textContent=$('#andar').value||'Planta'}
function inicioArraste(e,p,d){arrastando={p,d};dx=e.clientX-d.offsetLeft;dy=e.clientY-d.offsetTop;moved=false;d.setPointerCapture(e.pointerId)}
window.onpointermove=e=>{if(!arrastando)return;let mapa=$('#mapa'),x=Math.max(0,e.clientX-mapa.getBoundingClientRect().left+mapa.scrollLeft-dx),y=Math.max(0,e.clientY-mapa.getBoundingClientRect().top+mapa.scrollTop-dy);if(Math.abs(x-arrastando.p.x)>3||Math.abs(y-arrastando.p.y)>3)moved=true;arrastando.d.style.left=x+'px';arrastando.d.style.top=y+'px';arrastando.nx=x;arrastando.ny=y}
window.onpointerup=async()=>{if(!arrastando)return;let a=arrastando;arrastando=null;if(moved){$('#salvamento').textContent='Salvando...';try{await api('/api/posicoes/'+a.p.id,{method:'PUT',body:JSON.stringify({x:Math.round(a.nx),y:Math.round(a.ny)})});$('#salvamento').textContent='Posição salva'}catch(e){toast(e.message);carregar()}}setTimeout(()=>moved=false,50)}
function abrir(p={andar:$('#andar').value,status:'Livre'}){$('#id').value=p.id||'';campos.forEach(c=>$('#'+(c==='andar'?'f-andar':c)).value=p[c]||'');$('#excluir').style.visibility=p.id?'visible':'hidden';$('#modal').classList.remove('oculto')}
function fechar(){$('#modal').classList.add('oculto')}
$('#form').onsubmit=async e=>{e.preventDefault();let d={};campos.forEach(c=>d[c]=$('#'+(c==='andar'?'f-andar':c)).value.trim());let id=$('#id').value;try{await api(id?'/api/posicoes/'+id:'/api/posicoes',{method:id?'PUT':'POST',body:JSON.stringify(d)});fechar();await carregar();toast('Dados salvos com sucesso.')}catch(e){toast(e.message)}}
$('#excluir').onclick=async()=>{let id=$('#id').value;if(id&&confirm('Excluir esta posição?')){await api('/api/posicoes/'+id,{method:'DELETE'});fechar();carregar();toast('Posição excluída.')}}
$('#novo').onclick=()=>abrir();$('#fechar').onclick=$('#cancelar').onclick=fechar;$('#andar').onchange=carregar;let timer;$('#busca').oninput=()=>{clearTimeout(timer);timer=setTimeout(carregar,250)};carregarAndares();
function abrirImportacao(){$('#formImportacao').reset();$('#progressoImportacao').textContent='';$('#modalImportacao').classList.remove('oculto')}
function fecharImportacao(){$('#modalImportacao').classList.add('oculto')}
$('#abrirImportacao').onclick=abrirImportacao;$('#fecharImportacao').onclick=$('#cancelarImportacao').onclick=fecharImportacao;
$('#formImportacao').onsubmit=async e=>{e.preventDefault();let f=$('#arquivoExcel').files[0];if(!f)return;let fd=new FormData();fd.append('arquivo',f);fd.append('planilha',$('#nomePlanilha').value.trim());let b=$('#botaoImportar');b.disabled=true;$('#progressoImportacao').textContent='Importando e salvando no SQLite...';try{let r=await fetch('/api/importar',{method:'POST',body:fd}),d=await r.json();if(!r.ok)throw Error(d.erro);$('#progressoImportacao').textContent=`Concluído: ${d.importados} novos, ${d.atualizados} atualizados e ${d.ignorados} ignorados.`;await carregarAndares($('#andar').value);toast('Excel importado e salvo no SQLite.');setTimeout(fecharImportacao,1800)}catch(err){$('#progressoImportacao').textContent=err.message;toast(err.message)}finally{b.disabled=false}}
