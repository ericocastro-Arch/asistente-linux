const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '../src/gui/web');

function setup() {
  class Element {
    constructor(tag) { this.tagName=tag; this.children=[]; this.listeners={}; this.value=''; this.classList={add(){}}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children=children; }
    addEventListener(event, callback) { this.listeners[event]=callback; }
    setAttribute() {}
    removeAttribute() {}
    showModal() { this.open=true; }
    close() { this.open=false; }
  }
  const ids = new Map([...fs.readFileSync(path.join(root,'migration.html'),'utf8').matchAll(/id="([^"]+)"/g)]
    .map(match=>[match[1],new Element('div')]));
  ids.get('catalogFamily').value='all';ids.get('catalogFormat').value='all';
  const context=vm.createContext({
    document:{
      getElementById(id){ assert.ok(ids.has(id),'HTML missing '+id);return ids.get(id); },
      createElement(tag){return new Element(tag);},
      createTextNode(text){return text;},
      querySelectorAll(){return [];}
    },
    window:{addEventListener(){}},console
  });
  vm.runInContext(fs.readFileSync(path.join(root,'migration.js'),'utf8'),context);
  vm.runInContext('catalog='+JSON.stringify([{
    id:'artcraft-photocraft',windows:'Adobe Photoshop',linux:'PhotoCraft',aliases:['PhotoCraft'],
    family:'artcraft',route:'alternative',category:'Imagen',description:'Edición',maturity:'Alpha temprana',
    note:'Experimental',icon:'https://getartcraft.com/images/apps/photocraft/icon.webp',
    website:'https://getartcraft.com/apps/photocraft',repositories:'https://getartcraft.com/linux',searches:[],
    methods:[{id:'flatpak',label:'Flatpak',available:true,detail:'Descargable',steps:'Descarga oficial',command:'flatpak install --user "./ARCHIVO.flatpak"'},
             {id:'snap',label:'Snap',available:false,detail:'No verificado'}]
  }]),context);
  return {context,ids,run:code=>vm.runInContext(code,context)};
}

test('ArtCraft is searchable by Windows name and unavailable Snap is not offered',()=>{
  const {ids,run}=setup();
  ids.get('search').value='photoshop';run('renderCatalog()');
  assert.equal(ids.get('catalogItems').children.length,1);
  assert.equal(ids.get('catalogItems').children[0].tagName,'article');
  ids.get('catalogFormat').value='snap';run('renderCatalog()');
  assert.equal(ids.get('catalogItems').children[0].tagName,'p');
  ids.get('catalogFormat').value='flatpak';run('renderCatalog()');
  assert.equal(ids.get('catalogItems').children[0].tagName,'article');
});

test('Installation sheet opens with official download, literal command and disabled Snap',()=>{
  const {ids,run}=setup();
  run('showCraft(catalog[0])');
  assert.equal(ids.get('craftDialog').open,true);
  assert.equal(ids.get('craftMethods').children[1].disabled,true);
  assert.equal(ids.get('craftCommand').textContent,'flatpak install --user "./ARCHIVO.flatpak"');
  assert.equal(ids.get('craftDownload').children[0].href,'https://getartcraft.com/apps/photocraft');
  assert.equal(ids.get('craftLocal').hidden,true);
});
