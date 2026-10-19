const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../src/assets/theme.js'),'utf8');
function browser(saved = null, dark = false, blocked = false) {
  const events = {}, media = {matches:dark, addEventListener:(_,fn)=>media.change=fn};
  const values = new Map(saved === null ? [] : [['arena.theme.v1',saved]]);
  const document = {documentElement:{dataset:{},style:{}},querySelector:()=>({setAttribute(){}})};
  const window = {matchMedia:()=>media, addEventListener:(name,fn)=>events[name]=fn,dispatchEvent(){}};
  const localStorage = {getItem:k=>{if(blocked)throw Error('blocked');return values.get(k);},setItem:(k,v)=>{if(blocked)throw Error('blocked');values.set(k,v);},removeItem:k=>{if(blocked)throw Error('blocked');values.delete(k);}};
  vm.runInNewContext(source,{window,document,localStorage,Event});
  return {theme:window.arenaTheme,values,events,document,system(dark){media.matches=dark;media.change();},effective:()=>document.documentElement.dataset.theme};
}
test('first application follows system, including malformed persisted preferences',()=>{
  for(const saved of [null,'garbage','"dark"']) {const b=browser(saved,true);assert.equal(b.effective(),'dark');b.system(false);assert.equal(b.effective(),'light');}
});
test('explicit choice persists across reload and ignores system until reset',()=>{
  const b=browser(null,true);assert.equal(b.theme.set('light'),true);b.system(true);assert.equal(b.effective(),'light');
  assert.equal(browser(b.values.get('arena.theme.v1'),true).effective(),'light');
  b.theme.set('dark');b.system(false);assert.equal(b.effective(),'dark');
  b.theme.set('system');assert.equal(b.values.has('arena.theme.v1'),false);assert.equal(b.effective(),'light');b.system(true);assert.equal(b.effective(),'dark');
});
test('unavailable storage applies theme without claiming persistence',()=>{
  const b=browser(null,true,true);assert.equal(b.effective(),'dark');assert.equal(b.theme.set('light'),false);assert.equal(b.effective(),'light');
  assert.equal(b.theme.set('invalid'),false);assert.equal(b.theme.preference,'light');
});
test('other tabs and clearing browser storage update preference',()=>{
  const b=browser(null,true);b.events.storage({key:'arena.theme.v1',newValue:'light'});assert.equal(b.effective(),'light');
  b.events.storage({key:null,newValue:null});assert.equal(b.theme.preference,'system');assert.equal(b.effective(),'dark');
});
test('both palettes provide AA text, control boundaries and focus contrast',()=>{
  const css=fs.readFileSync(path.join(__dirname,'../src/theme.css'),'utf8');
  const luminance=hex=>{
    let h=hex.slice(1);if(h.length===3)h=[...h].map(c=>c+c).join('');
    return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  };
  for(const block of css.split(':root[data-theme="dark"]')) {
    const palette=Object.fromEntries([...block.matchAll(/(--[\w-]+):\s*(#[0-9a-f]+)/g)].map(m=>[m[1],m[2]]));
    if(!palette['--text'])continue;
    for(const [fg,bg,min] of [['--text','--page',4.5],['--muted','--surface-subtle',4.5],['--muted-3','--surface',4.5],['--error','--error-surface',4.5],['--branch-a-text','--branch-a-surface',4.5],['--branch-b-text','--branch-b-surface',4.5],['--on-action','--action',4.5],['--control-border','--surface',3],['--focus-2','--page',3]]) {
      const a=luminance(palette[fg]),b=luminance(palette[bg]);
      assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=min,`${fg} on ${bg}`);
    }
  }
});
