const products=[
{id:1,name:"Cheese Burger",price:32000,cat:"food",emoji:"🍔",desc:"Pishloq, yangi sabzavot va maxsus sous",tag:"Mashhur"},
{id:2,name:"Pepperoni pitsa",price:65000,cat:"food",emoji:"🍕",desc:"Pepperoni va eritilgan pishloq",tag:""},
{id:3,name:"Lavash",price:29000,cat:"food",emoji:"🌯",desc:"Go‘sht va yangi sabzavotlar",tag:""},
{id:4,name:"Olma",price:14000,cat:"fruit",emoji:"🍎",desc:"Yangi va saralangan olma · 1 kg",tag:"Yangi"},
{id:5,name:"Banan",price:22000,cat:"fruit",emoji:"🍌",desc:"Shirin banan · 1 kg",tag:""},
{id:6,name:"Pomidor",price:16000,cat:"fruit",emoji:"🍅",desc:"Saralangan pomidor · 1 kg",tag:""},
{id:7,name:"Sut 1 litr",price:14000,cat:"grocery",emoji:"🥛",desc:"Kundalik yangi sut",tag:""},
{id:8,name:"Tuxum 10 dona",price:18000,cat:"grocery",emoji:"🥚",desc:"Saralangan tuxum",tag:""},
{id:9,name:"Guruch 1 kg",price:19000,cat:"grocery",emoji:"🍚",desc:"Osh uchun guruch",tag:""},
{id:10,name:"Ichimlik suvi 1.5 l",price:7000,cat:"drink",emoji:"💧",desc:"Toza ichimlik suvi",tag:""},
{id:11,name:"Sharbat",price:16000,cat:"drink",emoji:"🧃",desc:"Mevali ichimlik",tag:""},
{id:12,name:"Kir yuvish vositasi",price:39000,cat:"home",emoji:"🧴",desc:"Uy-ro‘zg‘or uchun tozalash vositasi",tag:""},
{id:13,name:"Idish yuvish geli",price:18000,cat:"home",emoji:"🫧",desc:"Oshxona uchun kundalik vosita",tag:""},
{id:14,name:"Gigiyena salfetkalari",price:12000,cat:"pharmacy",emoji:"🧻",desc:"Shaxsiy gigiyena mahsuloti",tag:""},
{id:15,name:"Birinchi yordam bintlari",price:9000,cat:"pharmacy",emoji:"🩹",desc:"Uy aptechkasi uchun oddiy buyum",tag:""},
{id:16,name:"Qo‘l antiseptigi",price:15000,cat:"pharmacy",emoji:"🧴",desc:"Qo‘l gigiyenasi uchun",tag:""},
{id:17,name:"Keks",price:12000,cat:"sweet",emoji:"🧁",desc:"Yangi pishirilgan shirinlik",tag:""},
{id:18,name:"Shokolad",price:17000,cat:"sweet",emoji:"🍫",desc:"Shirinlik",tag:""},
{id:19,name:"Shampun",price:28000,cat:"beauty",emoji:"🧴",desc:"Soch parvarishi uchun",tag:""},
{id:20,name:"Yuz kremi",price:35000,cat:"beauty",emoji:"🧴",desc:"Kundalik parvarish vositasi",tag:""},
{id:21,name:"Quloqchin",price:85000,cat:"electronics",emoji:"🎧",desc:"Kundalik foydalanish uchun",tag:""},
{id:22,name:"Zaryad kabeli",price:25000,cat:"electronics",emoji:"🔌",desc:"Telefon uchun aksessuar",tag:""}
];
let cart=JSON.parse(localStorage.getItem("aliCart")||"{}");
let favorites=JSON.parse(localStorage.getItem("aliFavorites")||"[]");
const productPhotos={
1:"https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=700&q=85",
2:"https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=700&q=85",
3:"https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=700&q=85",
4:"https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=700&q=85",
5:"https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=700&q=85",
6:"https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=700&q=85",
7:"https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=700&q=85",
8:"https://images.unsplash.com/photo-1518569656558-1f25e69d93d7?auto=format&fit=crop&w=700&q=85",
9:"https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=700&q=85",
10:"https://images.unsplash.com/photo-1548839140-29a749e1cf4d?auto=format&fit=crop&w=700&q=85",
11:"https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=700&q=85",
19:"https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=700&q=85",
21:"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=700&q=85"
};
const money=n=>new Intl.NumberFormat("uz-UZ").format(n)+" so‘m";
const grid=document.querySelector("#foodGrid");
let activeFilter="all";
function renderProducts(filter=activeFilter,query=""){
 activeFilter=filter;
 const list=products.filter(p=>(filter==="all"||p.cat===filter)&&((p.name+" "+p.desc).toLowerCase().includes(query.toLowerCase())));
 const titleMap={all:"Mashhur mahsulotlar",food:"Taomlar",fruit:"Meva va sabzavotlar",grocery:"Oziq-ovqat",home:"Uy-ro‘zg‘or mahsulotlari",pharmacy:"Dorixona va gigiyena",drink:"Ichimliklar",sweet:"Shirinliklar",beauty:"Go‘zallik va parvarish",electronics:"Elektronika va aksessuar"};
 document.querySelector("#catalogTitle").textContent=titleMap[filter]||"Mahsulotlar";
 grid.innerHTML=list.length?list.map(p=>'<article class="food-card"><div class="food-picture cat-'+p.cat+'"><span class="food-tag">'+(p.tag||"")+'</span><img class="product-photo" src="'+(productPhotos[p.id]||"")+'" alt="'+p.name+'" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'grid\'"><span class="product-emoji" style="display:'+(productPhotos[p.id]?"none":"grid")+'">'+p.emoji+'</span><button class="favorite-toggle" data-fav="'+p.id+'" aria-label="Sevimlilarga qo‘shish">'+(favorites.includes(p.id)?"♥":"♡")+'</button></div><h3>'+p.name+'</h3><p>'+p.desc+'</p><div class="food-bottom"><b>'+money(p.price)+'</b><button class="add-btn" data-add="'+p.id+'" aria-label="Savatga qo‘shish">+</button></div></article>').join(""):'<div class="empty-results">Mahsulot topilmadi. Boshqa nom bilan qidirib ko‘ring.</div>';
 grid.querySelectorAll("[data-add]").forEach(b=>b.onclick=()=>{const id=b.dataset.add;cart[id]=(cart[id]||0)+1;save();});
 grid.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>{const id=Number(b.dataset.fav);favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];localStorage.setItem("aliFavorites",JSON.stringify(favorites));b.textContent=favorites.includes(id)?"♥":"♡";});
}
function save(){localStorage.setItem("aliCart",JSON.stringify(cart));renderCart();}
function renderCart(){
 const entries=products.filter(p=>cart[p.id]);const count=entries.reduce((s,p)=>s+cart[p.id],0);const sum=entries.reduce((s,p)=>s+p.price*cart[p.id],0);
 document.querySelector("#cartCount").textContent=count;
 document.querySelector("#grandTotal").textContent=money(sum+(count?12000:0));
 document.querySelector("#cartItems").innerHTML=entries.length?entries.map(p=>'<div class="cart-line"><div class="cart-product"><span class="cart-emoji">'+p.emoji+'</span><span><b>'+p.name+'</b><br><small>'+money(p.price)+'</small></span></div><div class="qty-controls"><button data-minus="'+p.id+'">−</button><b>'+cart[p.id]+'</b><button data-plus="'+p.id+'">+</button></div></div>').join(""):'<div class="empty-cart"><span>🛍️</span><b>Savatingiz hozircha bo‘sh</b><span>Yoqtirgan mahsulotingizni tanlang.</span></div>';
 document.querySelectorAll("[data-minus]").forEach(b=>b.onclick=()=>{const id=b.dataset.minus;cart[id]--;if(cart[id]<=0)delete cart[id];save();});
 document.querySelectorAll("[data-plus]").forEach(b=>b.onclick=()=>{const id=b.dataset.plus;cart[id]++;save();});
}
document.querySelectorAll(".category").forEach(b=>b.onclick=()=>{document.querySelectorAll(".category").forEach(x=>x.classList.remove("active"));b.classList.add("active");renderProducts(b.dataset.filter,document.querySelector("#searchInput").value);});
document.querySelectorAll("[data-store-filter]").forEach(b=>b.onclick=()=>{const filter=b.dataset.storeFilter;document.querySelectorAll(".category").forEach(x=>x.classList.toggle("active",x.dataset.filter===filter));renderProducts(filter,document.querySelector("#searchInput").value);});
document.querySelector("#searchInput").addEventListener("input",e=>{renderProducts(activeFilter,e.target.value);});
document.querySelector("#cartJump").onclick=()=>document.querySelector("#checkout").scrollIntoView({behavior:"smooth"});
document.querySelector(".search-jump")?.addEventListener("click",()=>document.querySelector("#searchInput").focus());
document.querySelector(".favorite-jump")?.addEventListener("click",()=>{renderProducts("all");document.querySelector("#catalog").scrollIntoView({behavior:"smooth"});});
const locationLabel=document.querySelector("#locationText");
const savedLocation=localStorage.getItem("aliLocationName");
if(savedLocation&&locationLabel)locationLabel.innerHTML=savedLocation+' <span class="chevron">⌄</span>';
async function detectDeliveryLocation(){
 const btn=document.querySelector("#locationBtn");
 if(!navigator.geolocation){alert("Brauzer joylashuvni aniqlashni qo‘llab-quvvatlamaydi. Manzilni qo‘lda kiriting.");return;}
 if(locationLabel)locationLabel.textContent="Joylashuv aniqlanmoqda...";
 navigator.geolocation.getCurrentPosition(async pos=>{
  const {latitude,longitude}=pos.coords;
  try{
   const response=await fetch("https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+encodeURIComponent(latitude)+"&lon="+encodeURIComponent(longitude)+"&zoom=14&accept-language=uz");
   if(!response.ok)throw new Error("Geokodlash xatosi");
   const data=await response.json();
   const a=data.address||{};
   const city=a.city||a.town||a.village||a.municipality||a.county||"Joylashuv aniqlandi";
   const district=a.suburb||a.city_district||a.neighbourhood||a.state_district||"";
   const country=a.country||"";
   const label=(district?district+", ":"")+city;
   if(locationLabel)locationLabel.innerHTML=label+' <span class="chevron">⌄</span>';
   localStorage.setItem("aliLocationName",label);
   localStorage.setItem("aliLocationCoords",JSON.stringify({latitude,longitude,country}));
   if(country&& !/uzbekistan|ўзбекистон|o‘zbekiston/i.test(country))alert("Siz O‘zbekiston hududidan tashqaridasiz. Hozircha xizmat O‘zbekiston bo‘ylab mo‘ljallangan.");
  }catch(err){
   const label="Joylashuv aniqlandi";
   if(locationLabel)locationLabel.innerHTML=label+' <span class="chevron">⌄</span>';
   localStorage.setItem("aliLocationName",label);
   localStorage.setItem("aliLocationCoords",JSON.stringify({latitude,longitude}));
  }
 },err=>{
  if(locationLabel)locationLabel.innerHTML='O‘zbekiston (avtomatik) <span class="chevron">⌄</span>';
  const messages={1:"Joylashuvga ruxsat berilmadi. Brauzer sozlamalaridan ruxsat bering.",2:"Joylashuv aniqlanmadi. GPS yoki internetni tekshiring.",3:"Joylashuvni aniqlash vaqti tugadi. Qayta urinib ko‘ring."};
  alert(messages[err.code]||"Joylashuvni aniqlab bo‘lmadi.");
 },{enableHighAccuracy:true,timeout:12000,maximumAge:300000});
}
document.querySelector("#locationBtn").onclick=detectDeliveryLocation;

document.querySelector("#orderForm").onsubmit=e=>{
 e.preventDefault();if(!Object.keys(cart).length){document.querySelector("#orderNotice").textContent="Avval savatga mahsulot qo‘shing.";return;}
 const order={id:"AK-"+Date.now().toString().slice(-6),name:document.querySelector("#customerName").value,phone:document.querySelector("#customerPhone").value,address:document.querySelector("#customerAddress").value,items:products.filter(p=>cart[p.id]).map(p=>({name:p.name,qty:cart[p.id],price:p.price})),total:products.reduce((s,p)=>s+p.price*(cart[p.id]||0),0)+12000,status:"Yangi",created:new Date().toLocaleString("uz-UZ")};
 const orders=JSON.parse(localStorage.getItem("aliOrders")||"[]");orders.unshift(order);localStorage.setItem("aliOrders",JSON.stringify(orders));cart={};save();e.target.reset();document.querySelector("#orderNotice").textContent="Demo buyurtma "+order.id+" saqlandi. Real operatorga yuborilmadi.";
};
renderProducts();renderCart();
if(!savedLocation){setTimeout(()=>detectDeliveryLocation(),700);}
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));}
