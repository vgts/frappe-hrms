import{t as h,v as D,w as M}from"./index-D9qwwsoE.js";import"./frappe-ui-BoBzcGmG.js";/*!
 * (C) Ionic http://ionicframework.com - MIT License
 */const G=(n,m,g,p,w)=>{const c=n.ownerDocument.defaultView;let s=h(n);const X=t=>{const{startX:e}=t;return s?e>=c.innerWidth-50:e<=50},a=t=>s?-t.deltaX:t.deltaX,v=t=>s?-t.velocityX:t.velocityX;return D({el:n,gestureName:"goback-swipe",gesturePriority:40,threshold:10,canStart:t=>(s=h(n),X(t)&&m()),onStart:g,onMove:t=>{const e=a(t)/c.innerWidth;p(e)},onEnd:t=>{const o=a(t),e=c.innerWidth,r=o/e,i=v(t),y=e/2,l=i>=0&&(i>.2||o>y),u=(l?1-r:r)*e;let d=0;if(u>5){const f=u/Math.abs(i);d=Math.min(f,540)}w(l,r<=0?.01:M(0,r,.9999),d)}})};export{G as createSwipeBackGesture};
//# sourceMappingURL=swipe-back-BRZb6193.js.map
