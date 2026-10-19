// WCAG contrast from rendered text against its composed opaque background.
// Complements screenshots; excludes disabled controls and non-visible content.
async function checkContrast(page) {
  const failures = await page.evaluate(() => {
    const rgba = value => (value.match(/[\d.]+/g) || []).map(Number);
    const blend = (fg,bg) => fg.slice(0,3).map((v,i)=>v*(fg[3]??1)+bg[i]*(1-(fg[3]??1)));
    const luminance = rgb => rgb.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
    const failures=[];
    for(const el of document.querySelectorAll('body *')) {
      if(!el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) || el.closest('[disabled]') || ['OPTION','SCRIPT','STYLE'].includes(el.tagName)) continue;
      const control=el.matches('input:not([type=checkbox]):not([type=radio]):not([type=file]), textarea, select');
      const placeholder=control && !el.value && el.getAttribute('placeholder');
      const text=control ? (el.tagName==='SELECT' ? el.selectedOptions[0]?.textContent : el.value || placeholder)
        : [...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent.trim()).join(' ');
      if(!text) continue;
      const ancestors=[];for(let node=el;node;node=node.parentElement) ancestors.unshift(node);
      let bg=[255,255,255];for(const node of ancestors) bg=blend(rgba(getComputedStyle(node).backgroundColor),bg);
      const style=getComputedStyle(el,placeholder?'::placeholder':null),fg=blend(rgba(style.color),bg);
      const a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
      const large=parseFloat(style.fontSize)>=24 || (parseFloat(style.fontSize)>=18.66 && parseInt(style.fontWeight)>=700);
      if(ratio < (large?3:4.5)) failures.push({text:text.slice(0,70),ratio:+ratio.toFixed(2),color:style.color,bg});
    }
    return failures;
  });
  require('node:assert/strict').deepEqual(failures, [], 'Rendered text must meet WCAG AA');
}
module.exports={checkContrast};
