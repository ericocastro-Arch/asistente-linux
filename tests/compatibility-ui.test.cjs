const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '../src/gui/web');

function setup() {
  class Element {
    constructor(tag) { this.tagName=tag; this.children=[]; this.listeners={}; this.attributes={}; this.value=''; this.checked=false; this.hidden=false; this.classList={add(){}}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children=children; }
    addEventListener(event, callback) { this.listeners[event]=callback; }
    setAttribute(key,value) { this.attributes[key]=value; }
    removeAttribute(key) { delete this.attributes[key]; }
    showModal() { this.open=true; }
    close() { this.open=false; }
  }
  const ids = new Map([...fs.readFileSync(path.join(root,'migration.html'),'utf8').matchAll(/id="([^"]+)"/g)]
    .map(match=>[match[1],new Element('div')]));
  ids.get('compatibility').hidden=true;
  const base = {summary:'Descripción',kind:'Aplicaciones',mark:'B',best_for:'Caso',limits:'No garantiza compatibilidad',requirements:['Dependencia'],steps:['Preparar'],troubleshooting:['Revisar registro'],sources:[{label:'Oficial',url:'https://example.org/'}]};
  const tools=[{...base,id:'bottles',name:'Bottles',methods:[{label:'Flatpak',package:'com.usebottles.bottles',source:'flatpak'}]},
               {...base,id:'winboat',name:'WinBoat',methods:[{label:'Descargar',url:'https://github.com/winboat-org/winboat/releases'},{label:'Elegir archivo',local:true}]}];
  const bridge={get_compatibility_catalog:async()=>({tools})};
  const context=vm.createContext({document:{
    getElementById(id){assert.ok(ids.has(id),'HTML missing '+id);return ids.get(id);},
    createElement(tag){return new Element(tag);},querySelectorAll(){return [];}
  },window:{addEventListener(){}},console});
  vm.runInContext(fs.readFileSync(path.join(root,'migration.js'),'utf8'),context);
  context.window.pywebview={api:bridge};
  vm.runInContext(fs.readFileSync(path.join(root,'compatibility.js'),'utf8'),context);
  return {context,bridge,ids,load:()=>context.window.CompatibilityHub.load()};
}
function descendants(el) { return [el,...el.children.flatMap(descendants)]; }
const findButton=(el,text)=>descendants(el).find(item=>item.tagName==='button' && item.textContent===text);

test('loads lazily, retries bridge errors and selects accessible tool sheets',async()=>{
  const {ids,bridge,load}=setup();
  const get=bridge.get_compatibility_catalog;
  let calls=0;bridge.get_compatibility_catalog=async()=>{calls++;throw new Error('offline');};
  assert.equal(calls,0);
  await load();assert.match(ids.get('compatStatus').textContent,/offline/);assert.equal(ids.get('compatRetry').hidden,false);
  bridge.get_compatibility_catalog=get;await load();
  const rows=ids.get('compatTools').children;
  assert.equal(rows.length,2);assert.equal(rows[0].attributes['aria-pressed'],'true');
  await rows[1].listeners.click();
  assert.equal(ids.get('compatTools').children[1].attributes['aria-pressed'],'true');
  assert.ok(descendants(ids.get('compatDetail')).some(el=>el.href==='https://github.com/winboat-org/winboat/releases'));
});

test('recommendations preserve literal names and provide alternatives without installation',async()=>{
  const {ids,bridge,load}=setup();await load();
  const name='<img src=x onerror=alert(1)>';
  ids.get('compatUse').value='application';ids.get('compatApp').value=name;ids.get('compatSpecial').checked=true;
  bridge.recommend_windows_compatibility=async payload=>{
    assert.equal(payload.application,name);assert.equal(payload.special_requirements,true);
    return {success:true,tool:'bottles',application:name,reason:'Ruta',notice:'Sin verificar',checks:['Prueba'],alternatives:['winboat']};
  };
  await ids.get('compatForm').listeners.submit({preventDefault(){}});
  assert.ok(descendants(ids.get('compatResult')).some(el=>el.textContent==='Bottles · '+name));
  assert.equal(ids.get('compatRecommend').disabled,false);
  await findButton(ids.get('compatResult'),'WinBoat').listeners.click();
  assert.equal(ids.get('compatTools').children[1].attributes['aria-pressed'],'true');
});

test('install actions reuse preview and do not install before confirmation',async()=>{
  const {ids,bridge,load}=setup();await load();
  let calls=0;
  bridge.install_catalog_app=async(pkg,source,name)=>{
    calls++;assert.equal(pkg,'com.usebottles.bottles');assert.equal(source,'flatpak');assert.equal(name,'Bottles');
    return {success:false,message:'Flatpak no disponible'};
  };
  bridge.confirm_catalog_app_install=async()=>assert.fail('No preview was approved');
  await findButton(ids.get('compatDetail'),'Flatpak').listeners.click();
  assert.equal(calls,1);assert.equal(ids.get('status').textContent,'Flatpak no disponible');
  await ids.get('compatTools').children[1].listeners.click();
  bridge.choose_local_package=async owner=>{
    assert.equal(owner,'migration');
    return {success:false,cancelled:true,message:'No se seleccionó ningún archivo.'};
  };
  await findButton(ids.get('compatDetail'),'Elegir archivo').listeners.click();
  assert.equal(ids.get('status').textContent,'No se seleccionó ningún archivo.');
});

test('refresh updates tools and clears stale information after failure',async()=>{
  const {ids,bridge,load}=setup();await load();
  bridge.get_compatibility_overview=async()=>({tools:{bottles:{status:'Detectado',formats:['Flatpak'],note:''}},
    machine:{architecture:'x86_64',ram_gib:8,cpu_threads:4,home_free_gib:40,kvm_present:true,kvm_access:false},notices:['Versiones sin verificar']});
  await ids.get('compatRefresh').listeners.click();
  assert.equal(ids.get('compatEnvironment').children.length,7);
  assert.ok(descendants(ids.get('compatTools')).some(el=>el.textContent==='Detectado · Flatpak'));
  bridge.get_compatibility_overview=async()=>{throw new Error('No disponible');};
  await ids.get('compatRefresh').listeners.click();
  assert.equal(ids.get('compatEnvironment').children.length,0);
  assert.match(ids.get('compatEnvironmentStatus').textContent,/No disponible/);
  assert.equal(ids.get('compatRefresh').disabled,false);
  assert.ok(descendants(ids.get('compatTools')).some(el=>el.textContent==='Estado sin comprobar'));
});
