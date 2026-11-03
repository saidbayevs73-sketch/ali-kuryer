const products=[
{id:1,name:"Cheese Burger",price:32000,cat:"burger",emoji:"🍔",desc:"Pishloq, yangi sabzavot va maxsus sous",tag:"Mashhur"},
{id:2,name:"Double Burger",price:45000,cat:"burger",emoji:"🍔",desc:"Ikki kotletli to‘yimli burger",tag:""},
{id:3,name:"Margarita pitsa",price:55000,cat:"pizza",emoji:"🍕",desc:"Pomidor, mozzarella va rayhon",tag:""},
{id:4,name:"Pepperoni pitsa",price:65000,cat:"pizza",emoji:"🍕",desc:"Pepperoni va eritilgan pishloq",tag:""},
{id:5,name:"Kartoshka fri",price:18000,cat:"burger",emoji:"🍟",desc:"Qarsildoq kartoshka fri",tag:""},
{id:6,name:"Coca-Cola 0.5",price:10000,cat:"drink",emoji:"🥤",desc:"Sovuq gazlangan ichimlik",tag:""},
{id:7,name:"Mevali sharbat",price:12000,cat:"drink",emoji:"🧃",desc:"Mevali sharbat",tag:""},
{id:8,name:"Lavash",price:29000,cat:"burger",emoji:"🌯",desc:"Go‘sht va yangi sabzavotlar",tag:""},
{id:9,name:"Shirinlik",price:22000,cat:"other",emoji:"🧁",desc:"Yangi tayyorlangan desert",tag:"Yangi"},
{id:10,name:"Market to‘plami",price:35000,cat:"market",emoji:"🛍️",desc:"Kundalik kerakli mahsulotlar",tag:""}
];
let cart=JSON.parse(localStorage.getItem("aliCart")||"{}");
const money=n=>new Intl.NumberFormat("uz-UZ").format(n)+" so‘m";
const grid=document.querySelector("#foodGrid");
function renderProducts(filter="all",query=""){
 const list=products.filter(p=>(filter==="all"||p.cat===filter)&&((p.name+" "+p.desc).toLowerCase().includes(query.toLowerCase())));
 grid.innerHTML=list.length?list.map(p=>'<article class="food-card"><div class="food-picture"><span class="food-tag">'+(p.tag||"")+'</span>'+p.emoji+'</div><h3>'+p.name+'</h3><p>'+p.desc+'</p><div class="food-bottom"><b>'+money(p.price)+'</b><button class="add-btn" data-add="'+p.id+'" aria-label="Savatga qo‘shish">+</button></div></article>').join(""):'<div class="empty-results">Hech narsa topilmadi. Boshqa nom bilan qidirib ko‘ring.</div>';
 grid.querySelectorAll("[data-add]").forEach(b=>b.onclick=()=>{const id=b.dataset.add;cart[id]=(cart[id]||0)+1;save();});
}
function save(){localStorage.setItem("aliCart",JSON.stringify(cart));renderCart();}
function renderCart(){
 const entries=products.filter(p=>cart[p.id]);const count=entries.reduce((s,p)=>s+cart[p.id],0);const sum=entries.reduce((s,p)=>s+p.price*cart[p.id],0);
 document.querySelector("#cartCount").textContent=count;
 document.querySelector("#grandTotal").textContent=money(sum+(count?12000:0));
 document.querySelector("#cartItems").innerHTML=entries.length?entries.map(p=>'<div class="cart-line"><div class="cart-product"><span class="cart-emoji">'+p.emoji+'</span><span><b>'+p.name+'</b><br><small>'+money(p.price)+'</small></span></div><div class="qty-controls"><button data-minus="'+p.id+'">−</button><b>'+cart[p.id]+'</b><button data-plus="'+p.id+'">+</button></div></div>').join(""):'<div class="empty-cart"><span>🛍️</span><b>Savatingiz hozircha bo‘sh</b><span>Yoqtirgan taomingizni tanlang.</span></div>';
 document.querySelectorAll("[data-minus]").forEach(b=>b.onclick=()=>{const id=b.dataset.minus;cart[id]--;if(cart[id]<=0)delete cart[id];save();});
 document.querySelectorAll("[data-plus]").forEach(b=>b.onclick=()=>{const id=b.dataset.plus;cart[id]++;save();});
}
document.querySelectorAll(".category").forEach(b=>b.onclick=()=>{document.querySelectorAll(".category").forEach(x=>x.classList.remove("active"));b.classList.add("active");renderProducts(b.dataset.filter,document.querySelector("#searchInput").value);});
document.querySelector("#searchInput").addEventListener("input",e=>{const active=document.querySelector(".category.active");renderProducts(active?.dataset.filter||"all",e.target.value);});
document.querySelector("#cartJump").onclick=()=>document.querySelector("#checkout").scrollIntoView({behavior:"smooth"});
document.querySelector("#locationBtn").onclick=()=>alert("Manzil tanlash xaritasi keyingi integratsiya bosqichida ulanadi.");
document.querySelector("#orderForm").onsubmit=e=>{
 e.preventDefault();if(!Object.keys(cart).length){document.querySelector("#orderNotice").textContent="Avval savatga mahsulot qo‘shing.";return;}
 const order={id:"AK-"+Date.now().toString().slice(-6),name:document.querySelector("#customerName").value,phone:document.querySelector("#customerPhone").value,address:document.querySelector("#customerAddress").value,items:products.filter(p=>cart[p.id]).map(p=>({name:p.name,qty:cart[p.id],price:p.price})),total:products.reduce((s,p)=>s+p.price*(cart[p.id]||0),0)+12000,status:"Yangi",created:new Date().toLocaleString("uz-UZ")};
 const orders=JSON.parse(localStorage.getItem("aliOrders")||"[]");orders.unshift(order);localStorage.setItem("aliOrders",JSON.stringify(orders));cart={};save();e.target.reset();document.querySelector("#orderNotice").textContent="Demo buyurtma "+order.id+" saqlandi. Real operatorga yuborilmadi.";
};
renderProducts();renderCart();

if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));}
