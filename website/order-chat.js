(() => {
 const API=window.ALI_KURYER_API_URL||"https://ali-kuryer-api.onrender.com";
 const token=async()=>{const u=window.AliKuryerWebAuth?.auth?.currentUser||window.AliKuryerStaff?.currentUser;if(!u)throw Error("Avval tizimga kiring");return u.getIdToken();};
 async function request(path,opts={}){const t=await token();const r=await fetch(API+path,{...opts,headers:{"Content-Type":"application/json",Authorization:"Bearer "+t,...opts.headers}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.message||d.error||"Chat xatosi");return d;}
 function attach(container,orderId){
  if(container.querySelector("[data-chat-panel]"))return;
  const panel=document.createElement("section");panel.dataset.chatPanel="1";panel.className="portal-card";
  const heading=document.createElement("h3");heading.textContent="Buyurtma bo‘yicha chat";
  const list=document.createElement("div");list.style.cssText="max-height:220px;overflow:auto;display:grid;gap:8px;margin:12px 0";
  const form=document.createElement("form");form.style.cssText="display:flex;gap:8px";
  const input=document.createElement("input");input.placeholder="Xabar yozing…";input.maxLength=4000;input.required;input.style.flex="1";
  const send=document.createElement("button");send.type="submit";send.textContent="Yuborish";
  form.append(input,send);panel.append(heading,list,form);container.append(panel);
  let stopped=false;
  async function refresh(){try{const d=await request("/api/v1/orders/"+encodeURIComponent(orderId)+"/chat");list.replaceChildren();for(const m of d.messages){const p=document.createElement("p");p.textContent=(m.sender_role==="customer"?"Mijoz: ":"Kuryer: ")+m.body;p.style.cssText="margin:0;padding:8px 10px;background:#f3f4f6;border-radius:10px";list.append(p);}list.scrollTop=list.scrollHeight;}catch(e){if(/contact_closed/.test(e.message)){stopped=true;clearInterval(timer);heading.textContent="Buyurtma aloqasi yopilgan";}else heading.textContent="Chat: "+e.message;}}
  form.addEventListener("submit",async e=>{e.preventDefault();send.disabled=true;try{await request("/api/v1/orders/"+encodeURIComponent(orderId)+"/chat",{method:"POST",body:JSON.stringify({body:input.value})});input.value="";await refresh();}catch(err){heading.textContent="Chat: "+err.message;}finally{send.disabled=false;}});
  const timer=setInterval(()=>{if(!stopped)refresh();},5000);refresh();
 }
 window.AliKuryerOrderChat={attach};
})();