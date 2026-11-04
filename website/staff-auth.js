import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.0/firebase-app.js";
import {
  getAuth, GoogleAuthProvider, signInWithPopup,
  signInWithEmailAndPassword, signOut
} from "https://www.gstatic.com/firebasejs/11.6.0/firebase-auth.js";

// Keep this in sync with the Firebase Web app config (not the Android app config).
const firebaseConfig = window.ALI_KURYER_FIREBASE_CONFIG || {
  apiKey: "AIzaSyDU4Px8gQj8U4Cnany8DTC6_pOfkGUSWPA",
  authDomain: "ali-kuryer-9d6bb.firebaseapp.com",
  projectId: "ali-kuryer-9d6bb",
  storageBucket: "ali-kuryer-9d6bb.firebasestorage.app",
  messagingSenderId: "1088566467185",
  appId: "1:1088566467185:web:5b0ff537b0f09a27abd9d0",
  measurementId: "G-LZ46LKT8NJ"
};
const app=initializeApp(firebaseConfig);
const auth=getAuth(app);
const API=window.ALI_KURYER_API_URL||"https://ali-kuryer-api.onrender.com";
const $=s=>document.querySelector(s);
const portal=document.body.dataset.portal;
const message=(value,bad=false)=>{const el=$("#notice");if(el){el.textContent=value;el.dataset.state=bad?"error":"ok";}};
const request=async(path,options={})=>{
 const user=auth.currentUser;
 if(!user)throw new Error("Avval tizimga kiring.");
 const token=await user.getIdToken();
 const response=await fetch(API+path,{...options,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,...options.headers}});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(data.message||"Server bilan aloqa xatosi ("+response.status+").");
 return data;
};
const make=(tag,cls,text)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;return el;};

if(portal==="admin"){
 const googleButton=$("#googleLogin");
 const loginPanel=$("#loginPanel"),managePanel=$("#managePanel");
 googleButton?.addEventListener("click",async()=>{
  googleButton.disabled=true;message("Google hisobi tekshirilmoqda…");
  try{
   const provider=new GoogleAuthProvider();provider.setCustomParameters({prompt:"select_account"});
   await signInWithPopup(auth,provider);
   await refreshStaff();
   loginPanel.hidden=true;managePanel.hidden=false;message("Administrator sifatida kirdingiz.");
  }catch(error){await signOut(auth).catch(()=>{});message(error.message||"Admin kirishi amalga oshmadi.",true);}
  finally{googleButton.disabled=false;}
 });
 async function refreshStaff(){
  const data=await request("/api/v1/admin/staff");
  const list=$("#staffList");list.replaceChildren();
  if(!data.staff.length){list.append(make("p","muted","Hozircha xodimlar qo‘shilmagan."));return;}
  for(const person of data.staff){
   const row=make("article","staff-row");
   const info=make("div","staff-info");
   info.append(make("strong","",person.displayName||person.email),make("small","",person.email+" · "+(person.role==="courier"?"Kuryer":"Oshxona")));
   const state=make("span",person.disabled?"staff-state off":"staff-state",person.disabled?"Bloklangan":"Faol");
   const toggle=make("button","secondary-btn",person.disabled?"Faollashtirish":"Bloklash");
   toggle.type="button";toggle.addEventListener("click",async()=>{
    toggle.disabled=true;
    try{await request("/api/v1/admin/staff/"+encodeURIComponent(person.uid),{method:"PATCH",body:JSON.stringify({disabled:!person.disabled})});await refreshStaff();message("Xodim holati yangilandi.");}
    catch(error){message(error.message,true);toggle.disabled=false;}
   });
   row.append(info,state,toggle);list.append(row);
  }
 }
 $("#staffForm")?.addEventListener("submit",async event=>{
  event.preventDefault();const button=$("#createStaff");button.disabled=true;
  const payload={displayName:$("#staffName").value.trim(),email:$("#staffEmail").value.trim(),password:$("#staffPassword").value,role:$("#staffRole").value};
  try{await request("/api/v1/admin/staff",{method:"POST",body:JSON.stringify(payload)});event.target.reset();message("Xodim hisobi yaratildi. Login va parolni xodimga xavfsiz yetkazing.");await refreshStaff();}
  catch(error){message(error.message,true);}
  finally{button.disabled=false;}
 });
 $("#refreshStaff")?.addEventListener("click",()=>refreshStaff().catch(e=>message(e.message,true)));
 $("#logout")?.addEventListener("click",async()=>{await signOut(auth);managePanel.hidden=true;loginPanel.hidden=false;message("Hisobdan chiqdingiz.");});
}

if(portal==="courier"||portal==="kitchen"){
 const expected=portal;
 const login=$("#staffLogin");
 login?.addEventListener("submit",async event=>{
  event.preventDefault();const button=$("#loginSubmit");button.disabled=true;message("Kirish tekshirilmoqda…");
  try{
   await signInWithEmailAndPassword(auth,$("#staffEmail").value.trim(),$("#staffPassword").value);
   const me=await request("/api/v1/staff/me");
   if(me.role!==expected){await signOut(auth);throw new Error(expected==="courier"?"Bu hisob kuryer uchun emas.":"Bu hisob oshxona uchun emas.");}
   $("#loginPanel").hidden=true;$("#staffPanel").hidden=false;
   $("#staffName").textContent=me.displayName||me.email;
   $("#staffRole").textContent=expected==="courier"?"Kuryer kabineti":"Oshxona kabineti";
   message("Muvaffaqiyatli kirdingiz.");
  }catch(error){await signOut(auth).catch(()=>{});message(error.message||"Login yoki parol xato.",true);}
  finally{button.disabled=false;}
 });
 $("#logout")?.addEventListener("click",async()=>{await signOut(auth);$("#staffPanel").hidden=true;$("#loginPanel").hidden=false;$("#staffLogin").reset();message("Hisobdan chiqdingiz.");});
}
