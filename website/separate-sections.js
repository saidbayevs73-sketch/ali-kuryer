(function(){
"use strict";
const views=["home","catalog","restaurants","promotions","cart"];
const copy={
catalog:["Katalog","Kerakli mahsulotni toping — kategoriyalar bo‘yicha tanlang."],
restaurants:["Restoranlar","Sevimli taomlaringizni tanlang va buyurtma bering."],
promotions:["Maxsus takliflar","Ali Kuryer’dagi aksiyalar va yangi takliflar."],
cart:["Savatcha","Tanlagan mahsulotlaringizni tekshiring va buyurtmani rasmiylashtiring."]
};
const main=document.querySelector(".main-shell");
const heading=document.createElement("div");heading.className="ak-page-heading";heading.innerHTML="<h1></h1><p></p>";main.prepend(heading);
function setView(view,scroll=true){
 if(!views.includes(view))view="home";
 document.body.dataset.akView=view;
 const h=copy[view];
 heading.style.display=h?"block":"none";
 if(h){heading.querySelector("h1").textContent=h[0];heading.querySelector("p").textContent=h[1]}
 document.querySelectorAll(".ak-main-nav [data-view]").forEach(a=>a.classList.toggle("selected",a.dataset.view===view));
 if(scroll)window.scrollTo({top:0,behavior:"smooth"});
 history.replaceState(null,"",view==="home"?location.pathname:("#"+view));
}
document.querySelectorAll(".ak-main-nav [data-view]").forEach(a=>a.addEventListener("click",e=>{e.preventDefault();setView(a.dataset.view)}));
document.querySelectorAll(".quick-links a").forEach(a=>a.addEventListener("click",e=>{const href=a.getAttribute("href");const v=href==="#restaurants"?"restaurants":href==="#promotions"?"promotions":href==="#checkout"?"cart":"catalog";e.preventDefault();setView(v)}));
document.querySelectorAll(".hero-cta,.promo[data-quick-filter]").forEach(a=>a.addEventListener("click",()=>{setTimeout(()=>setView("catalog",false),0)}));
const cartBtn=document.querySelector("#cartJump");if(cartBtn)cartBtn.addEventListener("click",e=>{e.preventDefault();setView("cart")});
const fav=document.querySelector(".favorite-jump");if(fav)fav.addEventListener("click",()=>setView("catalog"));
const profile=document.querySelector("#loginBtn");if(profile)profile.addEventListener("click",()=>setView("home",false));
document.querySelectorAll(".bottom-nav [data-action]").forEach(a=>a.addEventListener("click",e=>{e.preventDefault();setView("home",false)}));
setView("home",false);
})();
