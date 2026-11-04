let products=[
{id:1,name:"Cheese Burger",price:32000,cat:"food",emoji:"🍔",desc:"Pishloq, sabzavot va maxsus sous",tag:"Mashhur",photo:"https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=1200&q=92"},
{id:2,name:"Pepperoni pitsa",price:65000,cat:"food",emoji:"🍕",desc:"Pepperoni va eritilgan pishloq",photo:"https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=1200&q=92"},
{id:3,name:"Lavash",price:29000,cat:"food",emoji:"🌯",desc:"Go‘sht va yangi sabzavotlar",photo:"https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=1200&q=92"},
{id:4,name:"Olma",price:14000,cat:"fruit",emoji:"🍎",desc:"Saralangan olma · 1 kg",tag:"Yangi",photo:"https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=1200&q=92"},
{id:5,name:"Banan",price:22000,cat:"fruit",emoji:"🍌",desc:"Shirin banan · 1 kg",photo:"https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=1200&q=92"},
{id:6,name:"Pomidor",price:16000,cat:"fruit",emoji:"🍅",desc:"Saralangan pomidor · 1 kg",photo:"https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=1200&q=92"},
{id:7,name:"Sut 1 litr",price:14000,cat:"grocery",emoji:"🥛",desc:"Kundalik yangi sut",photo:"https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=1200&q=92"},
{id:8,name:"Tuxum 10 dona",price:18000,cat:"grocery",emoji:"🥚",desc:"Saralangan tuxum",photo:"https://images.unsplash.com/photo-1518569656558-1f25e69d93d7?auto=format&fit=crop&w=1200&q=92"},
{id:9,name:"Guruch 1 kg",price:19000,cat:"grocery",emoji:"🍚",desc:"Osh uchun guruch",photo:"https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=1200&q=92"},
{id:10,name:"Ichimlik suvi 1.5 l",price:7000,cat:"drink",emoji:"💧",desc:"Toza ichimlik suvi",photo:"https://images.unsplash.com/photo-1548839140-29a749e1cf4d?auto=format&fit=crop&w=1200&q=92"},
{id:11,name:"Sharbat",price:16000,cat:"drink",emoji:"🧃",desc:"Mevali ichimlik",photo:"https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=1200&q=92"},
{id:12,name:"Kir yuvish vositasi",price:39000,cat:"home",emoji:"🧴",desc:"Uy-ro‘zg‘or uchun vosita"},
{id:13,name:"Idish yuvish geli",price:18000,cat:"home",emoji:"🫧",desc:"Oshxona uchun kundalik vosita"},
{id:14,name:"Gigiyena salfetkalari",price:12000,cat:"pharmacy",emoji:"🧻",desc:"Shaxsiy gigiyena mahsuloti"},
{id:15,name:"Birinchi yordam bintlari",price:9000,cat:"pharmacy",emoji:"🩹",desc:"Uy aptechkasi uchun oddiy buyum"},
{id:16,name:"Qo‘l antiseptigi",price:15000,cat:"pharmacy",emoji:"🧴",desc:"Qo‘l gigiyenasi uchun"},
{id:17,name:"Keks",price:12000,cat:"sweet",emoji:"🧁",desc:"Yangi pishirilgan shirinlik"},
{id:18,name:"Shokolad",price:17000,cat:"sweet",emoji:"🍫",desc:"Shirinlik"},
{id:19,name:"Shampun",price:28000,cat:"beauty",emoji:"🧴",desc:"Soch parvarishi uchun",photo:"https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=1200&q=92"},
{id:20,name:"Yuz kremi",price:35000,cat:"beauty",emoji:"🧴",desc:"Kundalik parvarish vositasi"},
{id:21,name:"Quloqchin",price:85000,cat:"electronics",emoji:"🎧",desc:"Kundalik foydalanish uchun",photo:"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=92"},
{id:22,name:"Zaryad kabeli",price:25000,cat:"electronics",emoji:"🔌",desc:"Telefon uchun aksessuar"}
];

const API_BASE=window.ALI_KURYER_API_URL||"";
let catalogReady=false;
async function loadServerCatalog(){
 if(!API_BASE)return;
 try{
  const response=await fetch(API_BASE+"/api/v1/catalog",{headers:{Accept:"application/json"}});
  if(!response.ok)throw new Error("catalog_unavailable");
  const payload=await response.json();
  const remote=(payload.categories||[]).flatMap(category=>(category.products||[]).map(p=>({
   id:p.id,name:p.name,price:Number(p.price),cat:category.slug,emoji:"🛍️",
   desc:p.description||"Ali Kuryer mahsuloti",photo:p.imageUrl||"",serverId:p.id
  })));
  if(remote.length){products=remote;catalogReady=true;renderProducts();renderCart();loadServerCatalog();}
 }catch(error){console.warn("Ali Kuryer katalogi hozircha serverdan olinmadi:",error.message);}
}

const money=n=>new Intl.NumberFormat("uz-UZ").format(n)+" so‘m";
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
let cart=read("aliCart",{}),favorites=read("aliFavorites",[]),activeFilter="all",favoritesOnly=false;
const grid=document.querySelector("#foodGrid");
const titles={all:"Ommabop mahsulotlar",food:"Taomlar",grocery:"Market mahsulotlari",fruit:"Meva va sabzavotlar",drink:"Ichimliklar",sweet:"Shirinliklar",home:"Uy-ro‘zg‘or buyumlari",beauty:"Go‘zallik va parvarish",pharmacy:"Gigiyena mahsulotlari",electronics:"Elektronika"};
function renderProducts(filter=activeFilter,query=""){
 activeFilter=filter;
 const list=products.filter(p=>(!favoritesOnly||favorites.includes(p.id))&&(filter==="all"||p.cat===filter)&&((p.name+" "+p.desc).toLowerCase().includes(query.toLowerCase())));
 const catalogTitle=document.querySelector("#catalogTitle");if(catalogTitle)catalogTitle.textContent=favoritesOnly?"Sevimlilar":(titles[filter]||titles.all);
 grid.innerHTML=list.length?list.map(p=>'<article class="product-card"><div class="product-image">'+(p.photo?'<img src="'+p.photo+'" alt="'+p.name+'" loading="lazy" onerror="this.remove();this.parentElement.insertAdjacentHTML(\'afterbegin\',\'<span class=&quot;product-fallback&quot;>'+p.emoji+'</span>\')">':'<span class="product-fallback">'+p.emoji+'</span>')+(p.tag?'<span class="product-badge">'+p.tag+'</span>':'')+'<button class="favorite-btn" data-fav="'+p.id+'">'+(favorites.includes(p.id)?"♥":"♡")+'</button></div><h3>'+p.name+'</h3><p>'+p.desc+'</p><div class="product-bottom"><b>'+money(p.price)+'</b><button class="add-btn" data-add="'+p.id+'">+</button></div></article>').join(""):'<p class="empty-cart">Bu bo‘limda mahsulot topilmadi.</p>';
 grid.querySelectorAll("[data-add]").forEach(b=>b.onclick=()=>{const id=b.dataset.add;cart[id]=(cart[id]||0)+1;saveCart();});
 grid.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>{const id=Number(b.dataset.fav);favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];localStorage.setItem("aliFavorites",JSON.stringify(favorites));renderProducts();});
}
function saveCart(){localStorage.setItem("aliCart",JSON.stringify(cart));renderCart();}
function renderCart(){
 const items=products.filter(p=>cart[p.id]),count=items.reduce((n,p)=>n+cart[p.id],0),subtotal=items.reduce((n,p)=>n+p.price*cart[p.id],0);
 document.querySelector("#cartCount").textContent=count;
 document.querySelector("#grandTotal").textContent=money(subtotal+(count?12000:0));
 document.querySelector("#cartItems").innerHTML=items.length?items.map(p=>'<div class="cart-line"><div class="cart-product"><span class="cart-emoji">'+p.emoji+'</span><span><b>'+p.name+'</b><br><small>'+money(p.price)+'</small></span></div><div class="qty-controls"><button data-minus="'+p.id+'">−</button><b>'+cart[p.id]+'</b><button data-plus="'+p.id+'">+</button></div></div>').join(""):'<div class="empty-cart">🛍️<br><b>Savatcha hozircha bo‘sh</b><br>Mahsulot tanlang va xaridni boshlang.</div>';
 document.querySelectorAll("[data-minus]").forEach(b=>b.onclick=()=>{const id=b.dataset.minus;cart[id]--;if(cart[id]<=0)delete cart[id];saveCart();});
 document.querySelectorAll("[data-plus]").forEach(b=>b.onclick=()=>{const id=b.dataset.plus;cart[id]++;saveCart();});
}
function selectFilter(filter){favoritesOnly=false;document.querySelectorAll(".category-tile").forEach(b=>b.classList.toggle("active",b.dataset.filter===filter));renderProducts(filter,document.querySelector("#searchInput").value);}
document.querySelectorAll(".category-tile").forEach(b=>b.onclick=()=>selectFilter(b.dataset.filter));
document.querySelectorAll("[data-quick-filter]").forEach(b=>b.onclick=()=>selectFilter(b.dataset.quickFilter));
document.querySelector("#searchInput").addEventListener("input",e=>{favoritesOnly=false;renderProducts(activeFilter,e.target.value);});
document.querySelector(".cart-jump").onclick=()=>document.querySelector("#checkout").scrollIntoView({behavior:"smooth"});
document.querySelector(".favorite-jump").onclick=()=>{favoritesOnly=true;renderProducts("all");document.querySelector("#catalog").scrollIntoView({behavior:"smooth"});};
function showAccount(type){
 const panel=document.querySelector("#accountPanel");panel.hidden=false;
 if(type==="orders"){const orders=read("aliOrders",[]);panel.innerHTML='<div class="panel-head"><h2>Buyurtmalarim</h2><button class="panel-close">Yopish</button></div>'+(orders.length?orders.map(o=>'<div class="account-order"><b>'+o.id+'</b><strong>'+money(o.total)+'</strong><small>'+o.created+' · '+o.status+'</small></div>').join(""):'<p>Hozircha buyurtmalar yo‘q.</p>');}
 else panel.innerHTML='<div class="panel-head"><h2>Profil</h2><button class="panel-close">Yopish</button></div><p>Profil va ro‘yxatdan o‘tish serverga ulanish bosqichida faollashtiriladi.</p>';
 panel.querySelector(".panel-close").onclick=()=>panel.hidden=true;panel.scrollIntoView({behavior:"smooth",block:"center"});
}
document.querySelector("#loginBtn").onclick=()=>showAccount("profile");
document.querySelectorAll("[data-action]").forEach(a=>a.onclick=e=>{e.preventDefault();if(a.dataset.action==="favorites"){favoritesOnly=true;renderProducts("all");document.querySelector("#catalog").scrollIntoView({behavior:"smooth"});}else if(a.dataset.action==="orders"){showAccount("orders");}else showAccount("profile");});
const loc=document.querySelector("#locationText");
const savedLoc=localStorage.getItem("aliLocationName");if(savedLoc)loc.textContent=savedLoc;
document.querySelector("#locationBtn").onclick=()=>{
 if(!navigator.geolocation){const value=prompt("Yetkazib berish manzilingizni kiriting");if(value){loc.textContent=value;localStorage.setItem("aliLocationName",value);}return;}
 loc.textContent="Joylashuv aniqlanmoqda…";
 navigator.geolocation.getCurrentPosition(async pos=>{
  try{const r=await fetch("https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+pos.coords.latitude+"&lon="+pos.coords.longitude+"&zoom=14&accept-language=uz");const d=await r.json(),a=d.address||{},city=a.city||a.town||a.village||a.county||"Manzil aniqlandi",district=a.suburb||a.neighbourhood||a.city_district||"";const value=(district?district+", ":"")+city;loc.textContent=value;localStorage.setItem("aliLocationName",value);localStorage.setItem("aliLocationCoords",JSON.stringify({lat:pos.coords.latitude,lon:pos.coords.longitude}));}
  catch{loc.textContent="Manzil aniqlandi";}
 },()=>{loc.textContent="Manzilni tanlang";alert("Joylashuvga ruxsat berilmadi. Manzilni qo‘lda kiritishingiz mumkin.");},{enableHighAccuracy:true,timeout:10000,maximumAge:300000});
};
document.querySelector("#orderForm").onsubmit=async e=>{
 e.preventDefault();if(!Object.keys(cart).length){document.querySelector("#orderNotice").textContent="Avval savatchaga mahsulot qo‘shing.";return;}
 const orderItems=products.filter(p=>cart[p.id]);
 if(API_BASE&&catalogReady){
  if(orderItems.some(p=>!p.serverId)){document.querySelector("#orderNotice").textContent="Mahsulot ma’lumoti serverda topilmadi. Sahifani yangilang.";return;}
  const submit=document.querySelector(".submit-order");submit.disabled=true;submit.textContent="Yuborilmoqda…";
  try{
   const response=await fetch(API_BASE+"/api/v1/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    customerName:document.querySelector("#customerName").value,
    customerPhone:document.querySelector("#customerPhone").value,
    address:document.querySelector("#customerAddress").value,
    items:orderItems.map(p=>({productId:p.serverId,quantity:cart[p.id]})),
    paymentMethod:"cash"
   })});
   const result=await response.json();
   if(!response.ok)throw new Error(result.message||"Buyurtma yuborilmadi");
   cart={};saveCart();e.target.reset();document.querySelector("#orderNotice").textContent="Buyurtma qabul qilindi. Raqami: "+result.order.code;
  }catch(error){document.querySelector("#orderNotice").textContent=error.message||"Server bilan aloqa yo‘q. Qayta urinib ko‘ring.";}
  finally{submit.disabled=false;submit.textContent="Buyurtmani tasdiqlash →";}
  return;
 }
 const order={id:"AK-"+Date.now().toString().slice(-6),name:document.querySelector("#customerName").value,phone:document.querySelector("#customerPhone").value,address:document.querySelector("#customerAddress").value,items:orderItems.map(p=>({name:p.name,qty:cart[p.id],price:p.price})),total:orderItems.reduce((sum,p)=>sum+p.price*cart[p.id],0)+12000,status:"Yangi",created:new Date().toLocaleString("uz-UZ")};
 const orders=read("aliOrders",[]);orders.unshift(order);localStorage.setItem("aliOrders",JSON.stringify(orders));cart={};saveCart();e.target.reset();document.querySelector("#orderNotice").textContent="Demo rejim: buyurtma serverga yuborilmadi.";
};
renderProducts();renderCart();
