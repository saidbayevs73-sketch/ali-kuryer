(() => {
 const API=window.ALI_KURYER_API_URL||"https://ali-kuryer-api.onrender.com";
 const token=async()=>{const u=window.AliKuryerWebAuth?.auth?.currentUser||window.AliKuryerStaff?.currentUser;if(!u)throw Error("Avval tizimga kiring");return u.getIdToken();};
 async function request(path,opts={}){const t=await token();const r=await fetch(API+path,{...opts,headers:{"Content-Type":"application/json",Authorization:"Bearer "+t,...opts.headers}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.message||d.error||"Aloqa xatosi");return d;}
 function attach(container,orderId){
  if(container.querySelector("[data-chat-panel]"))return;
  const panel=document.createElement("section");panel.dataset.chatPanel="1";panel.className="portal-card";
  const heading=document.createElement("h3");heading.textContent="Buyurtma bo‘yicha chat";
  const list=document.createElement("div");list.style.cssText="max-height:220px;overflow:auto;display:grid;gap:8px;margin:12px 0";
  const form=document.createElement("form");form.style.cssText="display:flex;gap:8px";
  const input=document.createElement("input");input.placeholder="Xabar yozing…";input.maxLength=4000;input.required=true;input.style.flex="1";
  const send=document.createElement("button");send.type="submit";send.textContent="Yuborish";
  const callButton=document.createElement("button");callButton.type="button";callButton.textContent="Audio qo‘ng‘iroq";
  const callStatus=document.createElement("p");callStatus.setAttribute("aria-live","polite");
  const remoteAudio=document.createElement("audio");remoteAudio.autoplay=true;remoteAudio.playsInline=true;
  form.append(input,send);panel.append(heading,list,form,callButton,callStatus,remoteAudio);container.append(panel);
  let stopped=false, pc=null, localStream=null, callId=null, role=null, seen=new Set(), queuedIce=[];
  const base="/api/v1/orders/"+encodeURIComponent(orderId);
  function closeMedia(){if(pc){pc.close();pc=null;}if(localStream){localStream.getTracks().forEach(t=>t.stop());localStream=null;}remoteAudio.srcObject=null;}
  async function postSignal(type,payload={}){if(!callId)return;await request(base+"/calls/"+callId+"/signals",{method:"POST",body:JSON.stringify({signalType:type,payload})});}
  async function ensurePeer(){
   if(pc)return pc;
   pc=new RTCPeerConnection({iceServers:[{urls:"stun:stun.l.google.com:19302"}]});
   pc.onicecandidate=e=>{if(e.candidate)postSignal("ice",e.candidate.toJSON()).catch(err=>callStatus.textContent=err.message);};
   pc.ontrack=e=>{remoteAudio.srcObject=e.streams[0];remoteAudio.play().catch(()=>{callStatus.textContent="Ovoz eshitish uchun sahifada Play tugmasini bosing.";});};
   pc.onconnectionstatechange=()=>{if(pc&&["failed","disconnected","closed"].includes(pc.connectionState))callStatus.textContent="Aloqa uzildi yoki tarmoq cheklovi mavjud.";};
   return pc;
  }
  async function getMicrophone(){if(!navigator.mediaDevices?.getUserMedia)throw Error("Bu brauzer audio ruxsatini qo‘llamaydi. HTTPS orqali oching.");localStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});return localStream;}
  async function applySignals(signals){
   for(const s of signals||[]){if(seen.has(s.id))continue;seen.add(s.id);
    if(s.signal_type==="hangup"){callStatus.textContent="Qo‘ng‘iroq yakunlandi.";closeMedia();callId=null;callButton.disabled=false;continue;}
    if(s.signal_type==="offer"&&role==="callee"){
     const peer=await ensurePeer();await peer.setRemoteDescription(s.payload);
     for(const ice of queuedIce)await peer.addIceCandidate(ice);queuedIce=[];
     const stream=localStream||await getMicrophone();stream.getTracks().forEach(t=>peer.addTrack(t,stream));
     const answer=await peer.createAnswer();await peer.setLocalDescription(answer);await postSignal("answer",peer.localDescription.toJSON());callStatus.textContent="Qo‘ng‘iroqqa ulandingiz.";
    }else if(s.signal_type==="answer"&&role==="caller"){
     const peer=await ensurePeer();if(peer.signalingState==="have-local-offer")await peer.setRemoteDescription(s.payload);
     for(const ice of queuedIce)await peer.addIceCandidate(ice);queuedIce=[];callStatus.textContent="Ovozli aloqa ulandi.";
    }else if(s.signal_type==="ice"){
     const peer=await ensurePeer();if(peer.remoteDescription)await peer.addIceCandidate(s.payload);else queuedIce.push(s.payload);
    }
   }
  }
  async function pollCall(){
   if(stopped)return;
   try{
    const d=await request(base+"/calls/current");
    if(!callId&&d.call&&d.call.status==="ringing"&&d.call.callee_uid===(await tokenUserUid())){callId=d.call.id;role="callee";callStatus.textContent="Kiruvchi audio qo‘ng‘iroq. Qabul qilish uchun tugmani bosing.";callButton.textContent="Qo‘ng‘iroqni qabul qilish";callButton.disabled=false;}
    if(callId&&d.call?.id===callId){await applySignals(d.signals);if(d.call.status==="rejected"||d.call.status==="ended"){callStatus.textContent="Qo‘ng‘iroq tugadi.";closeMedia();callId=null;callButton.textContent="Audio qo‘ng‘iroq";callButton.disabled=false;}} 
   }catch(e){if(/contact_closed/.test(e.message)){stopped=true;clearInterval(chatTimer);clearInterval(callTimer);callStatus.textContent="Buyurtma aloqasi yopilgan.";closeMedia();} }
  }
  async function tokenUserUid(){const u=window.AliKuryerWebAuth?.auth?.currentUser||window.AliKuryerStaff?.currentUser;return u?.uid||"";}
  callButton.addEventListener("click",async()=>{
   callButton.disabled=true;
   try{
    if(callId&&role==="callee"){
     await request(base+"/calls/"+callId,{method:"PATCH",body:JSON.stringify({status:"accepted"})});
     callStatus.textContent="Mikrofon yoqilmoqda…";await getMicrophone();await pollCall();return;
    }
    if(callId){await postSignal("hangup");closeMedia();callId=null;role=null;callButton.textContent="Audio qo‘ng‘iroq";callStatus.textContent="Qo‘ng‘iroq yakunlandi.";return;}
    const d=await request(base+"/calls",{method:"POST",body:"{}"});callId=d.call.id;role="caller";
    const peer=await ensurePeer(),stream=await getMicrophone();stream.getTracks().forEach(t=>peer.addTrack(t,stream));
    const offer=await peer.createOffer();await peer.setLocalDescription(offer);await postSignal("offer",peer.localDescription.toJSON());
    callStatus.textContent="Kuryer javob berishi kutilmoqda…";callButton.textContent="Qo‘ng‘iroqni tugatish";
   }catch(e){callStatus.textContent=e.message;closeMedia();callId=null;role=null;callButton.textContent="Audio qo‘ng‘iroq";}
   finally{callButton.disabled=false;}
  });
  form.addEventListener("submit",async e=>{e.preventDefault();send.disabled=true;try{await request(base+"/chat",{method:"POST",body:JSON.stringify({body:input.value})});input.value="";await refresh();}catch(err){heading.textContent="Chat: "+err.message;}finally{send.disabled=false;}});
  async function refresh(){try{const d=await request(base+"/chat");list.replaceChildren();for(const m of d.messages){const p=document.createElement("p");p.textContent=(m.sender_role==="customer"?"Mijoz: ":"Kuryer: ")+m.body;p.style.cssText="margin:0;padding:8px 10px;background:#f3f4f6;border-radius:10px";list.append(p);}list.scrollTop=list.scrollHeight;}catch(e){if(/contact_closed/.test(e.message)){stopped=true;heading.textContent="Buyurtma aloqasi yopilgan";clearInterval(chatTimer);clearInterval(callTimer);closeMedia();}else heading.textContent="Chat: "+e.message;}}
  const chatTimer=setInterval(()=>{if(!stopped)refresh();},5000),callTimer=setInterval(pollCall,1500);refresh();pollCall();
 }
 window.AliKuryerOrderChat={attach};
})();