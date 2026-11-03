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
{id:18,name:"Shokolad",price:17000,cat:"sweet",emoji:"🍫",desc:"Shirinlik",tag:""}
];
let cart=JSON.parse(localStorage.getItem("aliCart")||"{}");
let favorites=JSON.parse(localStorage.getItem("aliFavorites")||"[]");
const money=n=>new Intl.NumberFormat("uz-UZ").format(n)+" so‘m";
const grid=document.querySelector("#foodGrid");
let activeFilter="all";
function renderProducts(filter=activeFilter,query=""){
 activeFilter=filter;
 const list=products.filter(p=>(filter==="all"||p.cat===filter)&&((p.name+" "+p.desc).toLowerCase().includes(query.toLowerCase())));
 const titleMap={all:"Mashhur mahsulotlar",food:"Taomlar",fruit:"Meva va sabzavotlar",grocery:"Oziq-ovqat",home:"Uy-ro‘zg‘or mahsulotlari",pharmacy:"Dorixona va gigiyena",drink:"Ichimliklar",sweet:"Shirinliklar"};
 document.querySelector("#catalogTitle").textContent=titleMap[filter]||"Mahsulotlar";
 grid.innerHTML=list.length?list.map(p=>'<article class="food-card"><div class="food-picture cat-'+p.cat+'"><span class="food-tag">'+(p.tag||"")+'</span><span class="product-emoji">'+p.emoji+'</span><button class="favorite-toggle" data-fav="'+p.id+'" aria-label="Sevimlilarga qo‘shish">'+(favorites.includes(p.id)?"♥":"♡")+'</button></div><h3>'+p.name+'</h3><p>'+p.desc+'</p><div class="food-bottom"><b>'+money(p.price)+'</b><button class="add-btn" data-add="'+p.id+'" aria-label="Savatga qo‘shish">+</button></div></article>').join(""):'<div class="empty-results">Mahsulot topilmadi. Boshqa nom bilan qidirib ko‘ring.</div>';
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
document.querySelector("#locationBtn").onclick=()=>alert("Manzil tanlash xaritasi keyingi integratsiya bosqichida ulanadi.");
document.querySelector("#orderForm").onsubmit=e=>{
 e.preventDefault();if(!Object.keys(cart).length){document.querySelector("#orderNotice").textContent="Avval savatga mahsulot qo‘shing.";return;}
 const order={id:"AK-"+Date.now().toString().slice(-6),name:document.querySelector("#customerName").value,phone:document.querySelector("#customerPhone").value,address:document.querySelector("#customerAddress").value,items:products.filter(p=>cart[p.id]).map(p=>({name:p.name,qty:cart[p.id],price:p.price})),total:products.reduce((s,p)=>s+p.price*(cart[p.id]||0),0)+12000,status:"Yangi",created:new Date().toLocaleString("uz-UZ")};
 const orders=JSON.parse(localStorage.getItem("aliOrders")||"[]");orders.unshift(order);localStorage.setItem("aliOrders",JSON.stringify(orders));cart={};save();e.target.reset();document.querySelector("#orderNotice").textContent="Demo buyurtma "+order.id+" saqlandi. Real operatorga yuborilmadi.";
};
renderProducts();renderCart();
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));}
