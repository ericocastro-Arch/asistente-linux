'use strict';
const $ = id => document.getElementById(id);
const labels = {native: 'Nativa en Linux', alternative: 'Alternativa · probar archivos', compatibility: 'Compatibilidad por juego', review: 'Pendiente de revisar'};
let catalog = [], entries = [], checks = {}, catalogRequest = 0, connected = false;
let saveQueue = Promise.resolve();
let selectedCraft = null;
const api = () => window.pywebview?.api;
const status = text => { $('status').textContent = text; };
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function button(text, action) {
  const el = node('button', text); el.type = 'button';
  el.addEventListener('click', async () => {
    el.disabled = true;
    try { await action(); } catch (err) { status(err.message || String(err)); }
    finally { el.disabled = false; }
  });
  return el;
}
function tab(id) {
  if (!['catalog','plan','install','compatibility','data','concepts'].includes(id)) return;
  document.querySelectorAll('.pane').forEach(el => { el.hidden = el.id !== id; });
  document.querySelectorAll('nav [data-tab]').forEach(el => {
    if (el.dataset.tab === id) el.setAttribute('aria-current', 'page');
    else el.removeAttribute('aria-current');
  });
  if (id === 'compatibility') window.CompatibilityHub?.load();
}
function save() {
  const payload=JSON.parse(JSON.stringify({inventory:$('inventory').value,entries,checks}));
  $('saved').textContent='Guardando plan…';
  saveQueue=saveQueue.then(async()=>{
    try {
      const result=await api().save_migration_plan(payload);
      if(!result.success)throw new Error(result.message);
      $('saved').textContent='Plan guardado en tu equipo.';
    }catch(err){$('saved').textContent='No se pudo guardar: '+err.message;}
  });
}
function renderCatalog() {
  const query = $('search').value.toLocaleLowerCase();
  $('catalogItems').replaceChildren();
  const family = $('catalogFamily').value, format = $('catalogFormat').value;
  const visible = catalog.filter(item =>
    (family === 'all' || (family === 'artcraft' ? item.family === 'artcraft' : item.family !== 'artcraft')) &&
    (format === 'all' || item.methods?.some(method => method.id === format && method.available)) &&
    [item.windows,item.linux,item.category || '',...item.aliases].join(' ').toLocaleLowerCase().includes(query));
  $('catalogCount').textContent = visible.length + ' equivalencias · Los formatos de ArtCraft se verificaron el 10/11/2026.';
  visible.forEach(item => {
    const card = node('article');
    if (item.family === 'artcraft') {
      card.classList.add('craft-card');
      card.append(craftHeading(item), node('p','Equivalente por función a '+item.windows,'equivalence'),
        node('span',item.maturity+' · Experimental','badge compatibility'), node('p',item.note));
      const formats = node('div',undefined,'format-chips');
      item.methods.forEach(method => {
        const chip=node('span',method.available ? method.label : method.label+' · no verificado',method.available ? 'format-chip' : 'format-chip unavailable');
        formats.append(chip);
      });
      card.append(formats, button('Ver instalación y descargas',()=>showCraft(item)));
    } else card.append(node('span', labels[item.route], 'badge '+item.route), node('h3', item.windows),
      appLogo(item),
      node('strong', item.linux), node('p', item.note),
      button('Buscar alternativas',()=>searchPackages(item.searches[0]?.query || item.linux)));
    card.append(button('Añadir a mi plan', () => {
        if(entries.length>=100)throw new Error('El plan admite hasta 100 programas.');
        if (!entries.some(entry => entry.match?.id === item.id)) entries.push({input:item.windows,match:item,route:item.route});
        renderPlan(); save(); status(item.windows + ' añadido a tu plan.');
      }));
    $('catalogItems').append(card);
  });
  if (!$('catalogItems').children.length) $('catalogItems').append(node('p','Sin coincidencias. Añade el nombre a Mi plan para revisarlo.', 'empty'));
}
function renderPlan() {
  $('planItems').replaceChildren();
  const counts = {};
  entries.forEach(entry => { counts[entry.route] = (counts[entry.route] || 0) + 1; });
  $('planSummary').textContent = entries.length ? Object.entries(counts).map(([key,n]) => n + ' · ' + labels[key]).join(' / ') : 'Tu plan está vacío. Añade aplicaciones o pega tu inventario.';
  entries.forEach((entry,index) => {
    const item = entry.match;
    const card = node('article');
    card.append(node('span',labels[entry.route] || labels.review,'badge '+entry.route),node('h3',entry.input));
    if (item) {
      if(item.family==='artcraft')card.append(craftHeading(item),button('Ver métodos de instalación',()=>showCraft(item)));
      card.append(node('strong',item.linux),node('p',item.note));
      item.searches.forEach(search => card.append(button('Buscar '+search.name, () => searchPackages(search.query))));
      const check = node('label',undefined,'check');
      const input = node('input'); input.type='checkbox'; input.checked=Boolean(entry.tested);
      input.addEventListener('change',()=>{ entry.tested=input.checked; save(); });
      check.append(input,document.createTextNode('Probé mis archivos y funciones')); card.append(check);
    } else {
      card.append(node('p','No hay una equivalencia confirmada. Revisa la versión del programa y las rutas web, Wine o Windows antes de decidir.'));
      if (entry.suggestion) card.append(button('Usar coincidencia: '+entry.suggestion.windows,()=>{
        entry.match=entry.suggestion; entry.route=entry.match.route; delete entry.suggestion; renderPlan(); save();
      }));
      card.append(button('Ver rutas de compatibilidad',()=>tab('compatibility')));
    }
    card.append(button('Quitar del plan',()=>{entries.splice(index,1);renderPlan();save();}));
    $('planItems').append(card);
  });
}
async function searchPackages(query) {
  tab('install'); $('packageQuery').value=query;
  const request=++catalogRequest;
  $('packages').replaceChildren(); $('packageStatus').textContent='Consultando los gestores disponibles…';
  try {
    const response=await api().get_app_catalog('all','all',query,0,24,true);
    if(request!==catalogRequest)return;
    $('packageStatus').textContent='Resultados del catálogo. La disponibilidad depende de tus repositorios. Usa Actualizar estado después de terminar la instalación.';
    for(const app of response.apps || []) {
      const card=node('article');
      card.append(node('span',app.source.toUpperCase(),'badge'),node('h3',app.name),node('p',app.description),node('code',app.package));
      card.append(app.installed ? node('p','Detectada como instalada') : button('Revisar instalación',()=>install(app)));
      $('packages').append(card);
    }
    if(!$('packages').children.length) $('packages').append(node('p','No hay resultados en los gestores configurados. Prueba otro nombre o revisa el origen de la aplicación.', 'empty'));
  } catch(err) {
    if(request===catalogRequest) $('packageStatus').textContent='No se pudo consultar el catálogo: '+err.message;
  }
}
async function install(app) {
  if($('preview').open)return;
  const result=await api().install_catalog_app(app.package,app.source,app.name);
  await confirmInstall(result);
}
async function confirmInstall(result) {
  if(!result.success || !result.preview) { status(result.message || 'No se pudo preparar la instalación.'); return; }
  const preview=result.preview;
  $('previewName').textContent=preview.name+' · '+preview.source;
  $('previewCommand').textContent=preview.command;
  $('previewDetail').textContent=preview.size_and_dependencies;
  const confirmed=await new Promise(resolve=>{
    $('preview').returnValue='cancel';
    $('preview').addEventListener('close',()=>resolve($('preview').returnValue==='confirm'),{once:true});
    $('preview').showModal();
  });
  const response=await api().confirm_catalog_app_install(preview.token,confirmed);
  status(response.message);
  $('packageStatus').textContent=response.message;
}
function link(label,url) {
  const el=node('a',label);el.href=url;el.target='_blank';el.rel='noopener noreferrer';return el;
}
function appLogo(item) {
  const wrap=node('span',undefined,'app-logo');
  const fallback=node('span',item.linux.slice(0,2).toUpperCase(),'logo-fallback');
  wrap.append(fallback);
  if(item.icon) {
    const img=node('img');img.alt='Logo de '+item.linux;img.loading='lazy';img.referrerPolicy='no-referrer';
    img.addEventListener('load',()=>{fallback.hidden=true;});
    img.addEventListener('error',()=>{img.remove();fallback.hidden=false;wrap.title='Logo no disponible sin conexión';});
    img.src=item.icon;wrap.append(img);
  }
  return wrap;
}
function craftHeading(item) {
  const heading=node('div',undefined,'craft-heading'),text=node('div');
  text.append(node('span','ARTCRAFT · '+item.category,'craft-eyebrow'),node('h3',item.linux));
  heading.append(appLogo(item),text);return heading;
}
function showCraft(item) {
  selectedCraft=item;
  $('craftTitle').textContent=item.linux+' · Instalación';
  $('craftDescription').textContent=item.description+' Equivalente por función a '+item.windows+'. '+item.maturity+'.';
  $('craftSources').replaceChildren(link('Página y descargas oficiales ↗',item.website),link('Repositorios oficiales ↗',item.repositories));
  $('craftMethods').replaceChildren();
  item.methods.forEach(method=>{
    const btn=button(method.label,()=>showMethod(method));
    btn.disabled=!method.available;btn.title=method.detail;
    $('craftMethods').append(btn);
  });
  $('craftArchitecture').textContent='Elige x86_64 o ARM64 según tu equipo. Las descargas se completan en la página oficial.';
  api()?.get_distro_info().then(info=>{
    if(selectedCraft?.id===item.id)$('craftArchitecture').textContent=info.name+' · Arquitectura: '+info.arch+'. Elige el paquete correspondiente en las descargas oficiales.';
  }).catch(()=>{});
  showMethod(item.methods[0]);
  $('craftDialog').showModal();
}
function showMethod(method) {
  $('craftSteps').textContent=method.detail+' '+method.steps;
  $('craftCommand').textContent=method.command || '';
  $('craftDownload').replaceChildren(link('Ver descarga '+method.label+' en el sitio oficial ↗',selectedCraft.website));
  $('craftLocal').hidden=!['deb','appimage'].includes(method.id);
  $('craftMethodNote').textContent='ARCHIVO es un ejemplo: sustitúyelo por el nombre descargado. Snap no está verificado. Flatpak se obtiene del editor; no se presupone disponibilidad en Flathub.';
}
async function openTool(id) {
  const result=await api().welcome_navigate(id);
  status(result.success ? 'Herramienta abierta en la ventana principal.' : result.message);
}
async function connect() {
  if(connected || !api())return;
  connected=true;
  try {
    catalog=await api().get_migration_catalog();
    const concepts=await api().get_windows_guide('', 'feature');
    renderCatalog();
    // Logos de las alternativas existentes, desde el catálogo de aplicaciones.
    const queries=[...new Set(catalog.filter(item=>item.family!=='artcraft').flatMap(item=>item.searches.map(s=>s.query)))];
    api().get_windows_guide_icons(queries).then(icons=>{
      catalog.forEach(item=>{if(item.family!=='artcraft')item.icon=icons[item.searches[0]?.query] || '';});
      renderCatalog();
    }).catch(()=>{});
    $('conceptItems').replaceChildren();
    concepts.forEach(item=>{
      const card=node('article');card.append(node('h3',item.windows),node('strong',item.linux),node('p',item.note));$('conceptItems').append(card);
    });
    // Restore only references to current catalog records, never persisted commands.
    try {
      const stored=await api().get_migration_plan();
      if(!stored.success)throw new Error(stored.message);
      const saved=stored.plan;
      if(typeof saved.inventory==='string') $('inventory').value=saved.inventory.slice(0,20000);
      if(saved.checks && typeof saved.checks==='object')checks=saved.checks;
      if(Array.isArray(saved.entries)) entries=saved.entries.slice(0,100).filter(e=>e && typeof e.input==='string').map(e=>{
        const match=catalog.find(item=>item.id===e.match?.id);
        return {input:e.input.slice(0,160),match:match||null,route:match?.route||'review',tested:e.tested===true};
      });
    } catch(err) { $('saved').textContent='No se pudo recuperar el plan: '+err.message; }
    document.querySelectorAll('[data-check]').forEach(el=>{el.checked=checks[el.dataset.check]===true;});
    renderPlan(); status('Listo. Empieza por tus aplicaciones o crea tu plan.');
  }catch(err){connected=false;status('No se pudo cargar el módulo: '+err.message);}
}
document.querySelectorAll('[data-tab]').forEach(el=>el.addEventListener('click',()=>tab(el.dataset.tab)));
document.querySelectorAll('[data-tool]').forEach(el=>el.addEventListener('click',()=>openTool(el.dataset.tool).catch(err=>status(err.message))));
document.querySelectorAll('[data-package]').forEach(el=>el.addEventListener('click',()=>searchPackages(el.dataset.package)));
document.querySelectorAll('[data-check]').forEach(el=>el.addEventListener('change',()=>{checks[el.dataset.check]=el.checked;save();}));
$('search').addEventListener('input',renderCatalog);
$('catalogFamily').addEventListener('change',renderCatalog);
$('catalogFormat').addEventListener('change',renderCatalog);
$('craftClose').addEventListener('click',()=>$('craftDialog').close());
$('craftLocal').addEventListener('click',async()=>{
  $('craftDialog').close();
  try { await confirmInstall(await api().choose_local_package('migration')); } catch(err) { status(err.message); }
});
$('inventory').addEventListener('input',save);
$('build').addEventListener('click',async()=>{
  $('build').disabled=true;
  try{
    const result=await api().plan_windows_migration($('inventory').value);
    if(!result.success)throw new Error(result.message);
    const additions=result.entries.filter(entry=>!entries.some(e=>e.input.toLowerCase()===entry.input.toLowerCase()));
    if(entries.length+additions.length>100)throw new Error('El plan admite hasta 100 programas.');
    entries.push(...additions);
    renderPlan();save();status('Plan preparado. Revisa las alternativas y prueba tus archivos antes de marcar cada aplicación.');
  }catch(err){status(err.message);}finally{$('build').disabled=false;}
});
$('reset').addEventListener('click',()=>{entries=[];$('inventory').value='';save();renderPlan();});
$('packageForm').addEventListener('submit',event=>{event.preventDefault();searchPackages($('packageQuery').value.trim());});
$('refreshPackages').addEventListener('click',()=>searchPackages($('packageQuery').value.trim()));
$('openFiles').addEventListener('click',async()=>{try{status(await api().open_windows_guide_application('explorador'));}catch(err){status(err.message);}});
window.addEventListener('pywebviewready',connect);
connect();
