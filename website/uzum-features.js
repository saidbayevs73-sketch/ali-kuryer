(function(){
"use strict";
const $=(s,r=document)=>r.querySelector(s);
const read=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}};
const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
let installPrompt=null,coords=read("aliLocationCoords",null);
const addresses=()=>read("aliSavedAddresses",[]);
const backdrop=document.createElement("div");
backdrop.className="ak-modal-backdrop";
backdrop.innerHTML='<section class="ak-sheet" role="dialog" aria-modal="true" aria-label="Ali Kuryer"><div class="ak-sheet-head"><h2 id="akTitle">Yetkazib berish</h2><button class="ak-close" aria-label="Yopish">×</button></div><div id="akContent"></div></section>';
document.body.appendChild(backdrop);
const content=$("#akContent",backdrop),title=$("#akTitle",backdrop);
function open(name,html){title.textContent=name;content.innerHTML=html;backdrop.classList.add("open");}
function close(){backdrop.classList.remove("open");}
$(".ak-close",backdrop).onclick=close;
backdrop.addEventListener("click",e=>{if(e.target===backdrop)close()});
function saveLocation(label,point){localStorage.setItem("aliLocationName",label);if(point){coords=point;write("aliLocationCoords",point)}const t=$("#locationText");if(t)t.textContent=label;const address=$("#customerAddress");if(address)address.value=label;close();}
function reverse(lat,lon){return fetch("https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+lat+"&lon="+lon+"&zoom=16&accept-language=uz").then(r=>r.json()).then(d=>{const a=d.address||{};return [a.road,a.house_number,a.suburb||a.neighbourhood,a.city||a.town||a.village||a.county].filter(Boolean).join(", ")||d.display_name||"Tanlangan joy"})}
function locationSheet(){
const list=addresses();
open("Yetkazib berish manzili",'<p class="ak-muted">Manzilingizni aniqlang yoki xaritada tanlang. Saqlangan manzillar keyingi buyurtmalarda ham ishlatiladi.</p><button class="ak-action" id="akLocate"><span class="ak-ico">⌖</span><span>Hozirgi joylashuvimni aniqlash<small class="ak-muted">Telefon GPS ruxsati kerak bo‘lishi mumkin</small></span></button><div id="akMapWrap"></div><label class="ak-field">Manzil nomi<input id="akAddressName" placeholder="Masalan: Uyim, Ishxonam"></label><label class="ak-field">To‘liq manzil<input id="akAddressText" placeholder="Ko‘cha, uy, xonadon, mo‘ljal"></label><button class="ak-primary" id="akSaveAddress">Manzilni saqlash</button><h3 style="font-size:14px;margin:20px 0 8px">Saqlangan manzillar</h3><div id="akAddressList">'+(list.length?list.map((a,i)=>'<div class="ak-address"><div><b>'+escapeHtml(a.name)+'</b><small>'+escapeHtml(a.address)+'</small></div><button data-use="'+i+'">Tanlash</button></div>').join(""):'<p class="ak-muted">Hozircha saqlangan manzil yo‘q.</p>')+'</div>');
$("#akLocate",content).onclick=()=>{
 if(!navigator.geolocation){alert("Qurilmada joylashuv aniqlash mavjud emas.");return}
 $("#akLocate",content).textContent="Joylashuv aniqlanmoqda…";
 navigator.geolocation.getCurrentPosition(async p=>{coords={lat:p.coords.latitude,lon:p.coords.longitude};try{$("#akAddressText",content).value=await reverse(coords.lat,coords.lon)}catch{$("#akAddressText",content).value="GPS joylashuv: "+coords.lat.toFixed(5)+", "+coords.lon.toFixed(5)}$("#akAddressName",content).value=$("#akAddressName",content).value||"Mening manzilim";$("#akLocate",content).textContent="Joylashuv aniqlandi ✓";showMap()},error=>{const messages={1:"Joylashuvga ruxsat berilmadi. Telefon sozlamalaridan ruxsat bering yoki manzilni qo‘lda kiriting.",2:"GPS joylashuvi topilmadi. Telefoningizda GPS va internetni yoqing yoki manzilni qo‘lda kiriting.",3:"Joylashuvni aniqlash vaqti tugadi. Qayta urinib ko‘ring yoki manzilni qo‘lda kiriting."};$("#akLocate",content).textContent=messages[error&&error.code]||"Joylashuv aniqlanmadi. Manzilni qo‘lda kiriting.";},{enableHighAccuracy:true,timeout:20000,maximumAge:60000});
 };
 function showMap(){if(!coords)return;$("#akMapWrap",content).innerHTML='<iframe class="ak-map" title="Tanlangan manzil xaritasi" src="https://www.openstreetmap.org/export/embed.html?bbox='+(coords.lon-.008)+'%2C'+(coords.lat-.005)+'%2C'+(coords.lon+.008)+'%2C'+(coords.lat+.005)+'&layer=mapnik&marker='+coords.lat+'%2C'+coords.lon+'"></iframe><p class="ak-muted">Xaritadagi nuqtani tekshiring. Aniq uy raqamini pastdagi maydonga kiriting.</p>'}
 if(coords)showMap();
 $("#akSaveAddress",content).onclick=()=>{const name=$("#akAddressName",content).value.trim()||"Manzil",address=$("#akAddressText",content).value.trim();if(!address){alert("Iltimos, manzilni kiriting yoki GPS orqali aniqlang.");return}const all=addresses();all.push({name,address,coords});write("aliSavedAddresses",all);saveLocation(name+": "+address,coords)};
 content.querySelectorAll("[data-use]").forEach(b=>b.onclick=()=>{const a=addresses()[Number(b.dataset.use)];saveLocation(a.name+": "+a.address,a.coords)});
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function accountSheet(){
open("Kabinet",'<button class="ak-action" data-page="orders"><span class="ak-ico">▣</span>Buyurtmalarim</button><button class="ak-action" data-page="addresses"><span class="ak-ico">⌖</span>Yetkazib berish manzillari</button><button class="ak-action" data-page="favorites"><span class="ak-ico">♡</span>Saralanganlar</button><button class="ak-action" data-page="faq"><span class="ak-ico">?</span>Savol-javob</button><button class="ak-action" data-page="contact"><span class="ak-ico">✉</span>Biz bilan bog‘lanish</button><div class="ak-bottom-tools"><button id="akLanguage">🌐 Til: O‘zbekcha</button><button id="akInstall">＋ Ilovani o‘rnatish</button></div><p class="ak-muted">Admin, oshxona va kuryer panellari mijozlar sahifasida ko‘rsatilmaydi.</p>');
content.querySelectorAll("[data-page]").forEach(b=>b.onclick=()=>{const p=b.dataset.page;if(p==="orders"){const orders=read("aliOrders",[]);open("Buyurtmalarim",orders.length?orders.map(o=>'<div class="ak-address"><div><b>'+escapeHtml(o.id)+'</b><small>'+escapeHtml(o.created||"")+' · '+escapeHtml(o.status||"Holat noma’lum")+'</small></div><b>'+new Intl.NumberFormat("uz-UZ").format(o.total)+' so‘m</b></div>').join(""):'<p class="ak-muted">Hozircha buyurtmalar yo‘q.</p>')}else if(p==="addresses")locationSheet();else if(p==="favorites"){close();$(".favorite-jump")?.click()}else if(p==="faq")open("Savol-javob",'<div class="ak-faq"><details open><summary>Buyurtmani qanday beraman?</summary><p>Katalogdan mahsulot tanlang, savatchaga qo‘shing, manzil va telefon raqamingizni kiriting, so‘ng buyurtmani tasdiqlang.</p></details><details><summary>Yetkazib berish manzilini qanday o‘zgartiraman?</summary><p>Yuqoridagi joylashuv tugmasini bosing va yangi manzilni tanlang yoki saqlang.</p></details><details><summary>Buyurtmam holatini qayerdan ko‘raman?</summary><p>Kabinetdagi “Buyurtmalarim” bo‘limida. Serverga ulangan buyurtmalarni kuzatish funksiyasi API bilan yakuniy ulanadi.</p></details><details><summary>To‘lov qanday amalga oshiriladi?</summary><p>Hozirgi loyihadagi buyurtma oqimi naqd to‘lovga mo‘ljallangan. Boshqa to‘lov usullari alohida integratsiya talab qiladi.</p></details></div>');else if(p==="contact")open("Biz bilan bog‘lanish",'<p class="ak-muted">Operator telefon raqami va Telegram manzili loyiha egasi tomonidan tasdiqlangach shu yerga joylanadi.</p><p>Hozircha aloqa ma’lumotlari sozlanmagan.</p>')});
 $("#akLanguage",content).onclick=()=>{open("Tilni tanlang",'<button class="ak-action" data-lang="uz">🇺🇿 O‘zbekcha</button><button class="ak-action" data-lang="ru">🇷🇺 Русский</button><button class="ak-action" data-lang="zh">🇨🇳 中文</button>');content.querySelectorAll("[data-lang]").forEach(b=>b.onclick=()=>window.AliKuryerI18n?.setLanguage(b.dataset.lang));};
 $("#akInstall",content).onclick=installApp;
}
async function installApp(){if(installPrompt){installPrompt.prompt();try{await installPrompt.userChoice}catch{}installPrompt=null;return}open("Ilovani o‘rnatish",'<p class="ak-muted">Brauzer menyusidan “Bosh ekranga qo‘shish” yoki “Install app” bandini tanlang. Shunda Ali Kuryer telefoningizda ilova kabi ochiladi.</p>')}
window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();installPrompt=e});
function autoDetectLocation(){
 if(localStorage.getItem("aliLocationName")||!navigator.geolocation)return;
 navigator.geolocation.getCurrentPosition(async p=>{
  coords={lat:p.coords.latitude,lon:p.coords.longitude};write("aliLocationCoords",coords);
  try{const label=await reverse(coords.lat,coords.lon);localStorage.setItem("aliLocationName",label);const t=$("#locationText");if(t)t.textContent=label;}
  catch{const t=$("#locationText");if(t)t.textContent="Joylashuv aniqlandi";}
 },()=>{}, {enableHighAccuracy:true,timeout:12000,maximumAge:300000});
}
const loc=$("#locationBtn");if(loc){loc.onclick=e=>{e.preventDefault();locationSheet()};}
const login=$("#loginBtn");if(login)login.onclick=e=>{e.preventDefault();if(window.AliKuryerNative&&window.AliKuryerNative.signInWithGoogle){window.AliKuryerNative.signInWithGoogle();}else{open("Google orqali kirish",'<p class="ak-muted">Google orqali haqiqiy kirish Android ilovasida ishlaydi. Veb-sayt uchun Firebase Web OAuth sozlamasi hali ulanmagan.</p>');}};

// Existing profile and order navigation open the richer account menu.
document.querySelectorAll('.bottom-nav [data-action="profile"],.bottom-nav [data-action="orders"]').forEach(a=>a.addEventListener("click",e=>{e.preventDefault();accountSheet()}));
autoDetectLocation();\n})();
