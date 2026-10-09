/* Customer-facing additions. No private API keys appear in browser code. */
(() => {
  "use strict";
  const accountAPI = "https://ali-kuryer.onrender.com";
  const defaultBot = "https://t.me/AliKuryerYordamBot";
  let config = {bot_url: defaultBot, ai_available: false, google_client_id: ""};
  let me = null;
  const $ = (selector, context=document) => context.querySelector(selector);
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  };
  const humanError = (err) => err?.message || "Ulanishda muammo. Qaytadan urinib ko‘ring.";
  async function api(path, options={}) {
    const response = await fetch(accountAPI + path, options);
    let data = {};
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Xizmat hozircha ishlamayapti");
    return data;
  }
  async function loadConfig() {
    try {
      const next = await api("/api/customer-experience/config");
      if (next && typeof next === "object") config = {...config, ...next};
    } catch (_) { /* The restaurant site remains usable without auxiliary API. */ }
    const botURL = /^https:\/\/t\.me\/[A-Za-z0-9_]+(?:\?.*)?$/.test(config.bot_url) ? config.bot_url : defaultBot;
    for (const anchor of document.querySelectorAll(".ali-help-link")) anchor.href = botURL;
    setupGoogle();
    const status = $("#aliAiStatus");
    if (status) status.textContent = config.ai_available ?
      "Muhammadali — AI yordamchi faol. Karta va maxfiy ma’lumot yubormang." :
      "Muhammadali hozircha menyu bo‘yicha yordam beradi. Jonli AI ulanishi tayyorlanmoqda.";
  }

  function buildPartners() {
    const old = $(".partner-section");
    if (!old) return;
    const section = el("section", "partner-callouts");
    section.id = "hamkorlik";
    section.innerHTML = `
      <div class="partner-inner">
        <h2>Ali Kuryer bilan hamkorlik qiling</h2>
        <p class="partner-intro">Oshxonangizni platformaga qo‘shing yoki kuryer sifatida ishlash uchun ariza qoldiring. Bu yerda xodimlar kabineti ochiq joylashtirilmaydi.</p>
        <div class="partner-actions">
          <article class="partner-action">
            <div aria-hidden="true" style="font-size:35px">🏪</div>
            <h3>Restoran hamkorligi</h3>
            <p>Oshxona ma’lumotlarini yuboring. Hamkorlik shartlari alohida kelishiladi.</p>
            <button type="button" data-show-form="restaurant" aria-expanded="false">Restoran arizasi</button>
            <form class="app-form" id="application-restaurant" data-kind="restaurant">
              <label>Oshxona yoki mas’ul shaxs nomi<input name="full_name" required minlength="3" maxlength="120" autocomplete="name"></label>
              <label>Telefon raqam<input name="phone" required type="tel" placeholder="+998901234567" autocomplete="tel"></label>
              <label>Shahar / tuman<input name="city" required maxlength="100" placeholder="Namangan"></label>
              <label>Oshxona haqida<input name="detail" maxlength="1000" placeholder="Nomi, yo‘nalishi, manzili..."></label>
              <input name="website" autocomplete="off" tabindex="-1" aria-hidden="true" style="position:absolute;left:-9999px">
              <label class="checkline"><input name="privacy_accepted" type="checkbox" required> <span><a href="/legal/privacy.html" target="_blank" rel="noopener">Maxfiylik shartlari</a> bilan tanishdim va arizamdagi ma’lumotlarni qayta ishlashga roziman.</span></label>
              <button type="submit">Arizani yuborish</button>
              <p class="status" role="status" aria-live="polite"></p>
            </form>
          </article>
          <article class="partner-action">
            <div aria-hidden="true" style="font-size:35px">🛵</div>
            <h3>Kuryer bo‘lish</h3>
            <p>Telefoningiz, shahringiz va transport turini yozib, hamkorlikka murojaat yuboring.</p>
            <button type="button" data-show-form="courier" aria-expanded="false">Kuryer arizasi</button>
            <form class="app-form" id="application-courier" data-kind="courier">
              <label>Ism va familiya<input name="full_name" required minlength="3" maxlength="120" autocomplete="name"></label>
              <label>Telefon raqam<input name="phone" required type="tel" placeholder="+998901234567" autocomplete="tel"></label>
              <label>Shahar / tuman<input name="city" required maxlength="100" placeholder="Namangan"></label>
              <label>Transport turi<select name="detail" required><option value="">Tanlang</option><option value="Piyoda">Piyoda</option><option value="Velosiped">Velosiped</option><option value="Mototsikl">Mototsikl</option><option value="Avtomobil">Avtomobil</option></select></label>
              <input name="website" autocomplete="off" tabindex="-1" aria-hidden="true" style="position:absolute;left:-9999px">
              <label class="checkline"><input name="privacy_accepted" type="checkbox" required> <span><a href="/legal/privacy.html" target="_blank" rel="noopener">Maxfiylik shartlari</a> bilan tanishdim va arizamdagi ma’lumotlarni qayta ishlashga roziman.</span></label>
              <button type="submit">Arizani yuborish</button>
              <p class="status" role="status" aria-live="polite"></p>
            </form>
          </article>
        </div>
      </div>`;
    old.replaceWith(section);
    for (const button of section.querySelectorAll("[data-show-form]")) {
      button.addEventListener("click", () => {
        const form = $("#application-" + button.dataset.showForm);
        const open = form.classList.toggle("open");
        button.setAttribute("aria-expanded", String(open));
        if (open) $("input[name=full_name]", form)?.focus();
      });
    }
    for (const form of section.querySelectorAll("form")) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const b = $("button[type=submit]", form), status = $(".status", form), fd = new FormData(form);
        b.disabled = true; status.textContent = "Ariza yuborilmoqda...";
        try {
          await api("/api/partner-applications", {
            method: "POST", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
              kind: form.dataset.kind,
              full_name: fd.get("full_name"), phone: fd.get("phone"), city: fd.get("city"),
              detail: fd.get("detail") || "", website: fd.get("website") || "",
              privacy_accepted: fd.get("privacy_accepted") === "on"
            })
          });
          form.reset();
          status.textContent = "✅ Arizangiz qabul qilindi. Mas’ul xodim aloqaga chiqishi mumkin.";
        } catch (err) { status.textContent = "⚠ " + humanError(err); }
        finally { b.disabled = false; }
      });
    }
    const help = el("section", "public-help");
    help.innerHTML = `<div><h2>Yordam kerakmi?</h2><p>Buyurtma, kuryerlik va restoran hamkorligi bo‘yicha Telegram yordamchi botimizga yozing.</p></div><a class="ali-help-link" href="https://t.me/AliKuryerYordamBot" target="_blank" rel="noopener noreferrer">💬 Telegram yordamchi bot</a>`;
    section.after(help);
  }

  const state = {register:false};
  function buildLogin() {
    const header = $("header .header-buttons");
    if (header) {
      const b = el("button", "btn btn-black", "👤 Kirish");
      b.id = "customerLoginBtn";
      b.type = "button";
      b.addEventListener("click", showLogin);
      header.prepend(b);
    }
    const d = el("dialog", "customer-dialog");
    d.id = "customerDialog";
    d.innerHTML = `
      <button type="button" class="auth-close" aria-label="Yopish">×</button>
      <h2 id="customerDialogTitle">Mijoz kabineti</h2>
      <p>O‘z buyurtmalaringiz uchun mijoz hisobiga kiring.</p>
      <div class="auth-switch"><button type="button" data-auth="login" class="active">Kirish</button><button type="button" data-auth="register">Ro‘yxatdan o‘tish</button></div>
      <form id="customerAuthForm">
        <div id="registerNameWrap" hidden><label>Ism va familiya<input name="name" autocomplete="name" minlength="2" maxlength="100"></label></div>
        <label>Telefon raqam<input name="phone" type="tel" required placeholder="+998901234567" autocomplete="tel"></label>
        <label>Parol<input name="password" type="password" required minlength="8" maxlength="72" autocomplete="current-password"></label>
        <label class="checkline" id="authConsent" hidden><input type="checkbox" name="consent"> <span><a href="/legal/privacy.html" target="_blank" rel="noopener">Maxfiylik shartlari</a> bilan tanishdim.</span></label>
        <button type="submit" class="auth-submit">Kirish</button>
        <p class="status" role="status" aria-live="polite"></p>
      </form>
      <div class="auth-divider">yoki</div>
      <div id="googleSignInBox" class="google-container"></div>
      <p id="googleSetupMessage" class="google-setup">Google hisob orqali kirish sozlanmoqda.</p>
      <div id="customerProfile" hidden></div>`;
    document.body.appendChild(d);
    $(".auth-close",d).addEventListener("click",()=>d.close());
    for(const button of d.querySelectorAll("[data-auth]")) button.addEventListener("click",()=>setAuthMode(button.dataset.auth==="register"));
    $("#customerAuthForm").addEventListener("submit", submitAuth);
  }
  function setAuthMode(register) {
    state.register = register;
    $("#registerNameWrap").hidden = !register;
    $("#authConsent").hidden = !register;
    $("#customerAuthForm [name=name]").required = register;
    $("#customerAuthForm [name=consent]").required = register;
    $("#customerAuthForm [name=password]").autocomplete = register?"new-password":"current-password";
    $("#customerAuthForm .auth-submit").textContent = register ? "Ro‘yxatdan o‘tish" : "Kirish";
    $("#customerAuthForm .status").textContent = "";
    for (const b of document.querySelectorAll("[data-auth]")) b.classList.toggle("active",(b.dataset.auth==="register")===register);
  }
  function showLogin() {
    const d=$("#customerDialog");
    if (!d) return;
    if (me) {
      $("#customerAuthForm").hidden=true;
      $(".auth-switch",d).hidden=true;
      $(".auth-divider",d).hidden=true;
      $("#googleSignInBox").hidden=true;
      $("#googleSetupMessage").hidden=true;
      const profile=$("#customerProfile");
      profile.hidden=false;
      profile.replaceChildren(el("p", "", "Salom, " + (me.name||"Mijoz") + "!"));
      const logout=el("button","auth-submit","Chiqish");
      logout.type="button";
      logout.addEventListener("click",()=>{sessionStorage.removeItem("ali_customer_token");me=null;$("#customerLoginBtn").textContent="👤 Kirish";d.close();});
      profile.appendChild(logout);
    } else {
      $("#customerAuthForm").hidden=false;
      $(".auth-switch",d).hidden=false;
      $(".auth-divider",d).hidden=false;
      $("#googleSignInBox").hidden=false;
      $("#googleSetupMessage").hidden=false;
      $("#customerProfile").hidden=true;
    }
    d.showModal();
  }
  async function submitAuth(event) {
    event.preventDefault();
    const form=event.currentTarget;
    const fd=new FormData(form);
    const phone=String(fd.get("phone")||"").replace(/[\s-]/g,"");
    const password=String(fd.get("password")||"");
    const msg=$(".status",form);
    if (!/^\+998\d{9}$/.test(phone)) {msg.textContent="Telefonni +998901234567 shaklida kiriting.";return;}
    const button=$("button[type=submit]",form);
    button.disabled=true;msg.textContent="Tekshirilmoqda...";
    try {
      if (state.register) {
        await api("/api/auth/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
          name:String(fd.get("name")||"").trim(),phone,password
        })});
      }
      const result=await api("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,password})});
      await finishLogin(result.access_token);
      form.reset();
      $("#customerDialog").close();
    } catch(err) {msg.textContent=humanError(err);}
    finally {button.disabled=false;}
  }
  async function finishLogin(token) {
    const profile=await api("/api/auth/me",{headers:{"Authorization":"Bearer "+token}});
    if (profile.role!=="customer") throw new Error("Faqat mijoz hisobi bilan kirish mumkin");
    sessionStorage.setItem("ali_customer_token",token);
    me=profile;
    $("#customerLoginBtn").textContent="👤 "+(me.name||"Kabinet");
    const nameField=$("#customerName"), phoneField=$("#phone");
    if(nameField && !nameField.value && me.name) nameField.value=me.name;
    if(phoneField && !phoneField.value && me.phone) phoneField.value=me.phone;
  }
  async function restoreLogin() {
    const token=sessionStorage.getItem("ali_customer_token");
    if (!token) return;
    try {await finishLogin(token);} catch (_) {sessionStorage.removeItem("ali_customer_token");}
  }
  function setupGoogle() {
    if (!config.google_client_id || !$("#googleSignInBox")) return;
    $("#googleSetupMessage").textContent="Google orqali xavfsiz kirish";
    const script=document.createElement("script");
    script.src="https://accounts.google.com/gsi/client";
    script.async=true;
    script.onload=()=>{
      if(!window.google?.accounts?.id)return;
      google.accounts.id.initialize({
        client_id:config.google_client_id,
        callback:async ({credential})=>{
          const msg=$("#customerAuthForm .status");
          try{
            const data=await api("/api/auth/google",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credential})});
            await finishLogin(data.access_token);
            $("#customerDialog").close();
          }catch(e){msg.textContent=humanError(e);}
        }
      });
      google.accounts.id.renderButton($("#googleSignInBox"),{theme:"outline",size:"large",text:"signin_with",shape:"pill",width:290});
    };
    document.head.appendChild(script);
  }
  function buildAssistant() {
    const btn=$(".assistant-button");
    if(btn){btn.setAttribute("aria-label","Muhammadali yordamchisini ochish");btn.innerHTML='<span class="ali-orb" aria-hidden="true"><span class="ali-smile"></span></span>';}
    const header=$(".chat-header");
    if(header){
      const headline=$("strong",header);
      if(headline)headline.textContent="✨ Muhammadali — yordamchi";
      header.appendChild(el("div","ali-chip","Faqat taom va ovqatlanish. Kaloriya — taxminiy baho."));
    }
    const chat=$("#chat");
    if(chat){const status=el("div","ali-ai-status","Muhammadali yuklanmoqda...");status.id="aliAiStatus";chat.appendChild(status);}
    let selectedImage = null;
    const controls = el("div", "", "");
    controls.style.padding = "10px";
    controls.innerHTML = '<label>📷 Ovqat rasmi (JPEG/PNG/WebP, 2 MB gacha)<input id="aliFoodPhoto" type="file" accept="image/jpeg,image/png,image/webp"></label><label style="display:block"><input id="aliPhotoConsent" type="checkbox"> Rasmni AI xizmatiga tahlil uchun yuborishga roziman.</label><button id="aliPhotoRemove" type="button">Rasmni olib tashlash</button><p id="aliPhotoStatus" role="status"></p>';
    $(".chat-input")?.before(controls);
    $("#aliFoodPhoto").addEventListener("change", async event => {
      selectedImage = null;
      const file = event.target.files[0];
      $("#aliPhotoConsent").checked = false;
      if (!file) return;
      if (!["image/jpeg","image/png","image/webp"].includes(file.type) || file.size > 2000000) {
        $("#aliPhotoStatus").textContent = "JPEG/PNG/WebP rasm tanlang, hajmi 2 MB gacha.";
        event.target.value = ""; return;
      }
      try {
        selectedImage = await new Promise((resolve,reject) => {
          const reader = new FileReader(); reader.onload=()=>resolve(reader.result);
          reader.onerror=reject; reader.readAsDataURL(file);
        });
        $("#aliPhotoStatus").textContent = "Rasm tanlandi. Porsiya va tarkibni yozing. Kaloriya taxminiy bo‘ladi.";
      } catch (_) { $("#aliPhotoStatus").textContent="Rasm o‘qilmadi."; }
    });
    $("#aliPhotoRemove").addEventListener("click", () => {
      selectedImage=null; $("#aliFoodPhoto").value=""; $("#aliPhotoConsent").checked=false;
      $("#aliPhotoStatus").textContent="";
    });
    const original=window.askAli;
    window.askAli=async function(question) {
      const input=$("#aliInput");
      const q=String(question||input?.value||(selectedImage ? "Rasmdagi taomni baholang: porsiya va taxminiy kaloriya haqida ayting." : "")).trim();
      if (!q) return;
      const blocked = /(sayt|website|site|kod|code|yaratuv|yaratgan|kim yarat|kirish|login|parol|password|token|api|server|admin|prompt|system|ignore|сайт|парол)/i;
      if (blocked.test(q)) {
        $("#chatBody").appendChild(el("div","message","Muhammadali: Men faqat taom va ovqatlanish haqida yordam beraman."));
        return;
      }
      if (selectedImage && !$("#aliPhotoConsent").checked) {
        $("#aliPhotoStatus").textContent="Rasmni yuborishdan oldin rozilikni belgilang."; return;
      }
      if (!config.ai_available) {
        if (selectedImage) {$("#aliPhotoStatus").textContent="AI hali ulanmagan. Rasm hozir yuborilmadi.";return;}
        if(typeof original==="function")return original(q);return;
      }
      if(input)input.value="";
      const body=$("#chatBody");
      if(!body)return;
      const userBox=el("div","message");userBox.appendChild(el("strong","","Siz: "));userBox.appendChild(document.createTextNode(q));body.appendChild(userBox);
      const answerBox=el("div","message","Muhammadali javob yozmoqda…");body.appendChild(answerBox);body.scrollTop=body.scrollHeight;
      try {
        const answer=await api("/api/assistant/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q,image_data:selectedImage,image_consent:!!selectedImage && $("#aliPhotoConsent").checked})});
        answerBox.textContent="Muhammadali: "+answer.reply;
      } catch(_) {answerBox.textContent="AI vaqtincha javob bermadi. Telegram yordamchi botimizga yozishingiz mumkin: "+config.bot_url;}
      body.scrollTop=body.scrollHeight;
    };
  }
  function buildLegalLinks() {
    const footer=$("footer");
    if(!footer)return;
    const links=el("div","legal-links");
    links.innerHTML='<a href="/legal/offer.html">Ommaviy oferta</a><a href="/legal/privacy.html">Maxfiylik siyosati</a><a class="ali-help-link" href="https://t.me/AliKuryerYordamBot" target="_blank" rel="noopener noreferrer">Yordamchi bot</a><a href="#hamkorlik">Hamkorlik</a>';
    footer.appendChild(links);
  }
  buildPartners();
  buildLogin();
  buildAssistant();
  buildLegalLinks();
  loadConfig();
  restoreLogin();
})();