const API=window.ALI_KURYER_API_URL||"https://ali-kuryer-api.onrender.com";
const el=s=>document.querySelector(s);
async function call(path,opts={}){const u=window.AliKuryerStaff?.currentUser;if(!u)throw Error("Qayta tizimga kiring");const token=await u.getIdToken();const r=await fetch(API+path,{...opts,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,...opts.headers}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.message||d.error||"Server xatosi");return d;}
function msg(t,b=false){const n=el("#notice");n.textContent=t;n.dataset.state=b?"error":"ok";}
async function refreshCourier(){try{const [available,mine]=await Promise.all([call("/api/v1/courier/orders/available"),call("/api/v1/courier/orders/mine")]);el("#availableOrders").replaceChildren();el("#myOrders").replaceChildren();
for(const o of available.orders){const row=document.createElement("article");row.className="staff-row";const info=document.createElement("div");info.className="staff-info";const title=document.createElement("strong");title.textContent=o.public_code;const detail=document.createElement("small");detail.textContent=o.delivery_address+" · "+o.kitchen_name;info.append(title,detail);const b=document.createElement("button");b.textContent="Buyurtmani olish";b.onclick=async()=>{b.disabled=true;try{await call("/api/v1/courier/orders/"+o.id+"/claim",{method:"POST"});await refreshCourier();msg("Buyurtma sizga biriktirildi.");}catch(e){msg(e.message,true);b.disabled=false;}};row.append(info,b);el("#availableOrders").append(row);}
for(const o of mine.orders){const row=document.createElement("article");row.className="staff-row";const info=document.createElement("div");info.className="staff-info";const title=document.createElement("strong");title.textContent=o.public_code;const detail=document.createElement("small");detail.textContent=o.delivery_address+" · "+o.status;info.append(title,detail);const next={assigned:"picked_up",picked_up:"on_the_way",on_the_way:"delivered"}[o.status];if(next){const b=document.createElement("button");b.textContent=({picked_up:"Olib ketdim",on_the_way:"Yo‘lda",delivered:"Yetkazildi"})[next];b.onclick=async()=>{b.disabled=true;try{await call("/api/v1/courier/orders/"+o.id+"/status",{method:"PATCH",body:JSON.stringify({status:next})});await refreshCourier();msg("Buyurtma holati yangilandi.");}catch(e){msg(e.message,true);b.disabled=false;}};row.append(b);}el("#myOrders").append(row);}
}catch(e){msg(e.message,true);}}
el("#refreshCourier")?.addEventListener("click",refreshCourier);
let gpsWatchId=null,lastGpsSent=0;
el("#onlineToggle")?.addEventListener("click",()=>{
 if(!navigator.geolocation){msg("Qurilmada GPS mavjud emas.",true);return;}
 if(gpsWatchId!==null){navigator.geolocation.clearWatch(gpsWatchId);gpsWatchId=null;msg("GPS kuzatuvi to‘xtatildi.");return;}
 msg("GPS kuzatuvi boshlandi…");
 gpsWatchId=navigator.geolocation.watchPosition(async p=>{
  const now=Date.now();if(now-lastGpsSent<8000)return;lastGpsSent=now;
  try{await call("/api/v1/courier/presence",{method:"POST",body:JSON.stringify({online:true,latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy})});msg("Jonli GPS yangilandi.");}
  catch(e){msg(e.message,true);}
 },()=>msg("GPS ruxsati berilmadi yoki joylashuv aniqlanmadi.",true),{enableHighAccuracy:true,maximumAge:5000,timeout:15000});
});
window.addEventListener("pagehide",()=>{if(gpsWatchId!==null)navigator.geolocation.clearWatch(gpsWatchId);});
window.addEventListener("ali-kuryer-staff-ready",refreshCourier);
