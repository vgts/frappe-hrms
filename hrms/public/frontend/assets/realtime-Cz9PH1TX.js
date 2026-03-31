import{U as u}from"./frappe-ui-C-rspyRq.js";const r=u({});function c(e,i,s){t(e,i),e.on("list_update",n=>{n.doctype==i&&s(n.name)})}function t(e,i){r[i]||(e.emit("doctype_subscribe",i),r[i]=!0,e.on("connect",()=>{e.emit("doctype_subscribe",i)}))}export{c as u};
//# sourceMappingURL=realtime-Cz9PH1TX.js.map
