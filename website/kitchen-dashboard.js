const api=window.ALI_KURYER_API_URL||"https://ali-kuryer-api.onrender.com";
const q=s=>document.querySelector(s);
async function apiCall(path,options={}){
 const user=window.AliKuryerStaff?.currentUser;
 if(!user)throw new Error("Kirish muddati tugagan. Qayta kiring.");
 const token=await user.getIdToken();
 const r=await fetch(api+path,{...options,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,...options.headers}});
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(data.message||data.error||"Server xatosi");
 return data;
}
function notice(s,bad=false){const el=q("#notice");el.textContent=s;el.dataset.state=bad?"error":"ok";}
async function loadKitchen(){
 try{
  const [profile,products,orders]=await Promise.all([
   apiCall("/api/v1/kitchen/profile"),apiCall("/api/v1/kitchen/products"),apiCall("/api/v1/kitchen/orders")
  ]);
  q("#kitchenProfileForm").hidden=!!profile.kitchen;
  q("#kitchenSummary").hidden=!profile.kitchen;
  if(profile.kitchen){q("#kitchenSummary").textContent=profile.kitchen.name+" · "+(profile.kitchen.active?"Faol":"Admin tasdig‘ini kutmoqda");}
  q("#dishList").replaceChildren();
  for(const p of products.products){
   const row=document.createElement("article");row.className="staff-row";
   const info=document.createElement("div");info.className="staff-info";
   const name=document.createElement("strong");name.textContent=p.name;
   const detail=document.createElement("small");detail.textContent=Number(p.price_uzs).toLocaleString("uz-UZ")+" so‘m · "+(p.available?"Mavjud":"Mavjud emas");
   info.append(name,detail);row.append(info);
   const toggle=document.createElement("button");toggle.type="button";toggle.textContent=p.available?"Mavjud emas qilish":"Mavjud qilish";
   toggle.onclick=async()=>{toggle.disabled=true;try{await apiCall("/api/v1/kitchen/products/"+p.id,{method:"PATCH",body:JSON.stringify({available:!p.available})});await loadKitchen();notice("Menyu yangilandi.");}catch(e){notice(e.message,true);toggle.disabled=false;}};
   const archive=document.createElement("button");archive.type="button";archive.textContent="Menyudan yashirish";
   archive.onclick=async()=>{archive.disabled=true;try{await apiCall("/api/v1/kitchen/products/"+p.id,{method:"DELETE"});await loadKitchen();notice("Taom menyudan yashirildi.");}catch(e){notice(e.message,true);archive.disabled=false;}};
   row.append(toggle,archive);q("#dishList").append(row);
  }
  q("#kitchenOrderList").replaceChildren();
  for(const o of orders.orders){
   const row=document.createElement("article");row.className="staff-row";
   const info=document.createElement("div");info.className="staff-info";
   const name=document.createElement("strong");name.textContent=o.public_code+" · "+o.customer_name;
   const detail=document.createElement("small");detail.textContent=o.delivery_address+" · "+o.status;
   info.append(name,detail);
   for(const item of (o.items||[])){const line=document.createElement("small");line.textContent=item.name+" × "+item.quantity;info.append(line);}
   row.append(info);
   const next={new:"accepted",accepted:"preparing",preparing:"ready"}[o.status];
   if(next){const b=document.createElement("button");b.type="button";b.textContent=({accepted:"Qabul qilish",preparing:"Tayyorlash",ready:"Tayyor"})[next];b.onclick=async()=>{b.disabled=true;try{await apiCall("/api/v1/kitchen/orders/"+o.id+"/status",{method:"PATCH",body:JSON.stringify({status:next})});await loadKitchen();notice("Buyurtma holati yangilandi.");}catch(e){notice(e.message,true);b.disabled=false;}};row.append(b);}
   q("#kitchenOrderList").append(row);
  }
 }catch(e){notice(e.message,true);}
}
q("#kitchenProfileForm")?.addEventListener("submit",async e=>{
 e.preventDefault();const b=q("#saveKitchenProfile");b.disabled=true;
 try{await apiCall("/api/v1/kitchen/profile",{method:"POST",body:JSON.stringify({name:q("#kName").value,phone:q("#kPhone").value,address:q("#kAddress").value,description:q("#kDescription").value})});await loadKitchen();notice("Oshxona profili yaratildi.");}
 catch(err){notice(err.message,true);}finally{b.disabled=false;}
});
q("#dishForm")?.addEventListener("submit",async e=>{
 e.preventDefault();const b=q("#saveDish");b.disabled=true;
 try{await apiCall("/api/v1/kitchen/products",{method:"POST",body:JSON.stringify({name:q("#dishName").value,description:q("#dishDescription").value,ingredients:q("#dishIngredients").value,price:Number(q("#dishPrice").value),available:true,photoSource:"upload"})});e.target.reset();await loadKitchen();notice("Taom menyuga qo‘shildi.");}
 catch(err){notice(err.message,true);}finally{b.disabled=false;}
});
q("#refreshKitchen")?.addEventListener("click",loadKitchen);
window.addEventListener("ali-kuryer-staff-ready",loadKitchen);
setInterval(()=>{if(window.AliKuryerStaff?.currentUser)loadKitchen();},15000);
