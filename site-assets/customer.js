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
    if (status) status.textContent =
      "Muhammadali taom, buyurtma va manzil bo‘yicha yordam beradi. AI xizmati vaqtincha uzilsa umumiy ma’lumot beriladi. Karta va kodlaringizni yubormang.";
  }

  function buildPartners() {
    const old = $(".partner-section");
    if (!old) return;
    const section = el("section", "partner-callouts");
    section.id = "hamkorlik";
    section.innerHTML = `
      <div class="partner-inner">
        <h2>Ali Kuryer bilan hamkorlik qiling</h2>
        <p class="partner-intro">Oshxonangizni platformaga qo‘shing yoki kuryer sifatida ishlash uchun ariza qoldiring.</p>
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
        <div id="authOtpWrap" hidden>
          <p class="muted">Telefoningizga 6 xonali SMS kodi yuboriladi. Kod 5 daqiqa amal qiladi.</p>
          <button type="button" id="authSmsSend" class="btn btn-black">📩 SMS-kod olish</button>
          <label>SMS tasdiqlash kodi<input name="otp_code" type="text" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" placeholder="000000"></label>
          <p class="muted">SMS kodi kelmasa, 60 soniyadan keyin qayta so‘rang.</p>
        </div>
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
    $("#authSmsSend").addEventListener("click", requestRegisterSms);
  }
  function setAuthMode(register) {
    state.register = register;
    $("#registerNameWrap").hidden = !register;
    $("#authConsent").hidden = !register;
    $("#authOtpWrap").hidden = !register;
    $("#customerAuthForm [name=otp_code]").required = register;
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
      // Previously registered accounts and Google users can verify ownership.
      const verification=el("div","customer-sms-verify");
      const vStatus=el("p","status","Telefon tasdiqlanishini tekshiramiz...");
      const vPhone=document.createElement("input");
      vPhone.type="tel";vPhone.placeholder="+998901234567";vPhone.value=me.phone||"";
      vPhone.setAttribute("aria-label","Tasdiqlanadigan telefon");
      const vCode=document.createElement("input");
      vCode.inputMode="numeric";vCode.maxLength=6;
      vCode.autocomplete="one-time-code";
      vCode.placeholder="6 xonali SMS kodi";
      vCode.setAttribute("aria-label","SMS tasdiqlash kodi");
      const send=el("button","btn btn-black","SMS-kod olish");send.type="button";
      const confirm=el("button","btn btn-black","Raqamni tasdiqlash");confirm.type="button";
      const h={"Authorization":"Bearer "+sessionStorage.getItem("ali_customer_token")};
      function verifiedScreen() {verification.replaceChildren(el("p","","✅ Telefoningiz SMS orqali tasdiqlangan."));}
      verification.append(vStatus,vPhone,send,vCode,confirm);
      profile.appendChild(verification);
      api("/api/auth/phone/status",{headers:h}).then(data=>{
        if(data.verified) verifiedScreen();
        else vStatus.textContent="⚠ Telefon raqamini SMS orqali tasdiqlang.";
      }).catch(()=>{vStatus.textContent="Telefon holatini tekshirib bo‘lmadi."});
      send.onclick=async()=>{
        send.disabled=true;
        try {
          await api("/api/auth/phone/request",{
            method:"POST",headers:{"Content-Type":"application/json",...h},
            body:JSON.stringify({phone:vPhone.value.trim()})
          });
          vStatus.textContent="SMS so‘raldi. Kodni kiriting.";
        }catch(e){vStatus.textContent=humanError(e)}
        finally{send.disabled=false}
      };
      confirm.onclick=async()=>{
        confirm.disabled=true;
        try{
          await api("/api/auth/phone/confirm",{
            method:"POST",headers:{"Content-Type":"application/json",...h},
            body:JSON.stringify({phone:vPhone.value.trim(),otp_code:vCode.value.trim()})
          });
          me.phone=vPhone.value.trim();
          verifiedScreen();
        }catch(e){vStatus.textContent=humanError(e)}
        finally{confirm.disabled=false}
      };
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
  async function requestRegisterSms() {
    const input=$("#customerAuthForm [name=phone]");
    const phone=String(input?.value||"").replace(/[\s-]/g,"");
    const message=$("#customerAuthForm .status");
    if(!/^\+998\d{9}$/.test(phone)){
      message.textContent="Telefonni +998901234567 shaklida kiriting.";
      return;
    }
    const button=$("#authSmsSend");
    button.disabled=true;
    message.textContent="SMS so‘ralmoqda...";
    try {
      await api("/api/auth/otp/request",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone})
      });
      message.textContent="SMS kodini tekshiring. 5 daqiqa ichida kiriting.";
    } catch(err) {
      message.textContent=humanError(err);
    } finally {
      button.disabled=false;
    }
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
          name:String(fd.get("name")||"").trim(),phone,password,
          otp_code:String(fd.get("otp_code")||"").trim()
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
      header.appendChild(el("div","ali-chip","Savolingizga javob va taom tanlashda ko‘mak"));
    }
    const chat=$("#chat");
    if(chat){
      const status=el("div","ali-ai-status","Muhammadali yuklanmoqda...");
      status.id="aliAiStatus";chat.appendChild(status);
      const close=el("button","ali-chat-close","×");
      close.type="button";
      close.setAttribute("aria-label","Muhammadali oynasini yopish");
      close.addEventListener("click",()=>{chat.style.display="none";});
      if(header)header.appendChild(close);
      window.toggleAli=()=>{chat.style.display=chat.style.display==="flex"?"none":"flex";};
    }
    // Ready prompts remain visible in the chat, even without AI.
    const quick=$("#chatBody .quick");
    const botLink=()=>/^https:\/\/t\.me\/[A-Za-z0-9_]{5,32}$/.test(config.bot_url)
      ?config.bot_url:defaultBot;
    if(quick){
      for(const [label,question] of [
        ["🍽 3 xil menyu","Menga 3 xil oilaviy kechki ovqat menyusi tavsiya qil."],
        ["📦 Buyurtma holati","Buyurtmam holatini qanday kuzataman?"],
        ["📍 Manzil","Yetkazish manzilini qanday belgilayman?"]
      ]){
        const button=el("button","",label);
        button.type="button";
        button.addEventListener("click",()=>window.askAli(question));
        quick.appendChild(button);
      }
      const photoPrompt=el("button","","📷 Surat kaloriyasi");
      photoPrompt.type="button";
      photoPrompt.addEventListener("click",()=>{
        const text=$("#aliInput");
        if(text)text.value="Rasmdagi taomning taxminiy kaloriyasi qancha?";
        $("#aliPhotoInput")?.click();
      });
      quick.appendChild(photoPrompt);
      const operator=el("a","ali-help-link ali-quick-operator","👩‍💻 Operatorga ulanish");
      operator.href=botLink();
      operator.target="_blank";operator.rel="noopener noreferrer";
      quick.appendChild(operator);
    }
    let attachedPhoto=null;
    let sending=false;
    const chatInput=$("#chat .chat-input");
    if(chat && chatInput){
      const toolbar=el("div","ali-photo-toolbar");
      const uploadBtn=el("button","ali-photo-trigger","📷 Rasm qo‘shish");
      uploadBtn.type="button";
      const photoInput=el("input","ali-photo-file");
      photoInput.id="aliPhotoInput";
      photoInput.type="file";
      photoInput.accept="image/jpeg,image/png,image/webp";
      photoInput.setAttribute("aria-label","Taom rasmini tanlash");
      photoInput.hidden=true;
      uploadBtn.addEventListener("click",()=>photoInput.click());
      const preview=el("div","ali-photo-preview");
      preview.hidden=true;
      const help=el("span","ali-photo-help",
        "Surat AI xizmatiga tahlil uchun yuboriladi, saqlanmaydi. Kaloriya faqat taxminiy.");
      toolbar.append(uploadBtn,photoInput,help,preview);
      chat.insertBefore(toolbar,chatInput);
      const clearPhoto=()=>{
        attachedPhoto=null;
        photoInput.value="";
        preview.replaceChildren();
        preview.hidden=true;
      };
      photoInput.addEventListener("change",()=>{
        const file=photoInput.files?.[0];
        if(!file){clearPhoto();return;}
        if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>4_000_000){
          clearPhoto();
          window.alert("JPEG, PNG yoki WEBP rasm tanlang (4 MB dan kichik).");
          return;
        }
        const reader=new FileReader();
        reader.onerror=()=>{clearPhoto();window.alert("Rasmni o‘qib bo‘lmadi.");};
        reader.onload=()=>{
          if(typeof reader.result!=="string"||!reader.result.startsWith("data:image/")){
            clearPhoto();return;
          }
          attachedPhoto=reader.result.slice(reader.result.indexOf(",")+1);
          const thumb=el("img","ali-photo-thumb");
          thumb.alt="Tanlangan taom surati";thumb.src=reader.result;
          const remove=el("button","ali-photo-remove","✕ Olib tashlash");
          remove.type="button";remove.addEventListener("click",clearPhoto);
          preview.replaceChildren(thumb,el("span","","Surat tayyor"),remove);
          preview.hidden=false;
          if(!$("#aliInput")?.value.trim())$("#aliInput").value="Rasmdagi taomning taxminiy kaloriyasi qancha?";
        };
        reader.readAsDataURL(file);
      });
      window.aliClearPhoto=clearPhoto;
    }
    window.askAli=async function(question) {
      if(sending)return;
      const input=$("#aliInput");
      const q=String(question||input?.value||"").trim();
      if (!q)return;
      const body=$("#chatBody");
      if(!body)return;
      const userBox=el("div","message");
      userBox.appendChild(el("strong","","Siz: "));
      userBox.appendChild(document.createTextNode(q));
      if(attachedPhoto){
        const img=el("span","ali-photo-sent","📷 Rasm ilova qilindi");
        userBox.appendChild(img);
      }
      body.appendChild(userBox);
      if(/operator|jonli yordam|odam bilan|inson bilan/i.test(q)){
        const info=el("div","message","Sizni operator bilan bog‘lanish uchun Telegram yordam botiga yo‘naltiramiz.");
        const link=el("a","ali-operator-open","Operator chatini ochish ↗");
        link.href=botLink();link.target="_blank";link.rel="noopener noreferrer";
        info.appendChild(link);body.appendChild(info);
        body.scrollTop=body.scrollHeight;
        // Open synchronously during the user's click; the visible link covers blocked popups.
        window.open(botLink(),"_blank","noopener,noreferrer");
        return;
      }
      const fileToSend=attachedPhoto;
      if(input)input.value="";
      const answerBox=el("div","message","Muhammadali javob yozmoqda…");
      body.appendChild(answerBox);body.scrollTop=body.scrollHeight;
      sending=true;
      const sendBtn=$("#chat .chat-input button");
      if(sendBtn)sendBtn.disabled=true;
      try {
        const payload={message:q};
        if(fileToSend)payload.image_base64=fileToSend;
        const answer=await api("/api/assistant/chat",{
          method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify(payload)
        });
        answerBox.textContent="Muhammadali"+(answer.mode==="basic"?" (ma’lumot rejimi)":"")+": "+answer.reply;
        if(answer.action==="open_operator"){
          const link=el("a","ali-operator-open","Operator bilan yozish ↗");
          link.href=/^https:\/\/t\.me\/[A-Za-z0-9_]{5,32}$/.test(answer.operator_url)
            ?answer.operator_url:botLink();
          link.target="_blank";link.rel="noopener noreferrer";
          answerBox.appendChild(link);
        }
        window.aliClearPhoto?.();
      } catch(error) {
        answerBox.textContent=humanError(error)+" Operator: "+botLink();
        // Keep the photo selected so the customer can retry without reuploading.
      } finally {
        sending=false;
        if(sendBtn)sendBtn.disabled=false;
        body.scrollTop=body.scrollHeight;
      }
    };
  }
  function buildLegalLinks() {
    const footer=$("footer");
    if(!footer)return;
    const links=el("div","legal-links");
    links.innerHTML='<a href="/legal/offer.html">Ommaviy oferta</a><a href="/legal/privacy.html">Maxfiylik siyosati</a><a class="ali-help-link" href="https://t.me/AliKuryerYordamBot" target="_blank" rel="noopener noreferrer">Yordamchi bot</a><a href="#hamkorlik">Hamkorlik</a>';
    footer.appendChild(links);
  }

  // Match the five main Android customer tabs on narrow screens.
  function buildMobileNavigation() {
    const dock = el("nav", "ali-mobile-nav");
    dock.setAttribute("aria-label", "Mijoz uchun bosh menyu");
    const tabs = [
      {name:"Asosiy", icon:"⌂", action:()=>window.scrollTo({top:0,behavior:"smooth"})},
      {name:"Qidiruv", icon:"⌕", action:()=>{const s=$("#search");s?.scrollIntoView({behavior:"smooth",block:"center"});s?.focus({preventScroll:true})}},
      {name:"Buyurtmalar", icon:"▤", action:openCustomerOrders},
      {name:"Savat", icon:"▣", action:()=>window.openCart?.()},
      {name:"Profil", icon:"◯", action:showLogin},
    ];
    for(const [index,tab] of tabs.entries()){
      const btn=el("button","",tab.name);
      btn.type="button";
      btn.replaceChildren(el("span","ali-nav-icon",tab.icon),el("span","",tab.name));
      btn.setAttribute("aria-label",tab.name);
      if(index===0)btn.setAttribute("aria-current","page");
      btn.addEventListener("click",()=>{
        for(const other of dock.querySelectorAll("button"))other.removeAttribute("aria-current");
        btn.setAttribute("aria-current","page");
        tab.action();
      });
      dock.appendChild(btn);
    }
    document.body.appendChild(dock);
    const orderDialog=el("dialog","customer-dialog");
    orderDialog.id="aliOrderDialog";
    orderDialog.innerHTML='<button type="button" class="auth-close" aria-label="Yopish">×</button><h2>Buyurtmalarim</h2><p>Buyurtmalar va ularning holatini shu yerda ko‘rishingiz mumkin.</p><div id="aliOrderList" role="status" aria-live="polite"></div>';
    document.body.appendChild(orderDialog);
    $(".auth-close",orderDialog).addEventListener("click",()=>orderDialog.close());
  }
  async function openCustomerOrders() {
    if(window.openAliOrders){return window.openAliOrders()}
    if(!me){showLogin();return}
    const dialog=$("#aliOrderDialog"),box=$("#aliOrderList");
    if(!dialog||!box)return;
    box.replaceChildren(el("p","muted","Buyurtmalar yuklanmoqda…"));
    dialog.showModal();
    try{
      const token=sessionStorage.getItem("ali_customer_token");
      const orders=await api("/api/v1/orders/my",{headers:{"Authorization":"Bearer "+token}});
      box.replaceChildren();
      if(!orders.length){box.appendChild(el("p","muted","Hozircha buyurtmalaringiz yo‘q."));return}
      for(const order of orders){
        const item=el("article","ali-order-preview");
        item.appendChild(el("strong","","Buyurtma №"+order.id));
        item.appendChild(el("p","muted","Holati: "+String(order.status||"Noma’lum")));
        item.appendChild(el("b","",Number(order.total||0).toLocaleString("uz-UZ")+" so‘m"));
        box.appendChild(item);
      }
    }catch(e){
      box.replaceChildren(el("p","status",humanError(e)));
    }
  }

  buildPartners();
  buildLogin();
  buildMobileNavigation();
  buildAssistant();
  buildLegalLinks();
  loadConfig();
  restoreLogin();
})();