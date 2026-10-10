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
    setupTelegramReadiness();
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

  const state = {register:false, smsReady:false, smsChecked:false, usernameReady:false, usernameSelected:false, usernameRegister:false};
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
          <p id="aliSmsAvailability" class="muted" role="status" aria-live="polite">
            SMS xizmati tekshirilmoqda. Tasdiqlash ishlamasa kod yuborilgan deb hisoblamang.
          </p>
          <p class="muted" style="margin:6px 0"><a class="ali-help-link" href="https://t.me/AliKuryerYordamBot"
            target="_blank" rel="noopener noreferrer">Ro‘yxatdan o‘tishda yordam: operatorga yozish ↗</a></p>
          <button type="button" id="authSmsSend" class="btn btn-black" disabled>📩 SMS-kod olish</button>
          <label>SMS tasdiqlash kodi<input name="otp_code" type="text" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" placeholder="000000"></label>
          <p class="muted">SMS kodi kelmasa, 60 soniyadan keyin qayta so‘rang.</p>
        </div>
        <label class="checkline" id="authConsent" hidden><input type="checkbox" name="consent"> <span><a href="/legal/privacy.html" target="_blank" rel="noopener">Maxfiylik shartlari</a> bilan tanishdim.</span></label>
        <button type="submit" class="auth-submit">Kirish</button>
        <p class="status" role="status" aria-live="polite"></p>
      </form>
      <div class="auth-divider">yoki</div>
      <section id="telegramLoginArea" class="ali-telegram-login" aria-label="Telegram bilan tasdiqlash">
        <button id="aliTelegramLogin" type="button" class="ali-telegram-btn" disabled>
          Telegram orqali tasdiqlash
        </button>
        <p id="aliTelegramStatus" class="ali-telegram-hint" role="status">
          Telegram tasdiqlash xizmati tekshirilmoqda...
        </p>
      </section>
      <section id="aliUsernameArea" class="ali-username-account" hidden>
        <button id="aliUsernameOpen" class="ali-username-open" type="button">
          Login nomi va parol bilan kirish yoki ro‘yxatdan o‘tish
        </button>
        <form id="aliUsernameForm" hidden>
          <div class="auth-switch">
            <button type="button" id="aliUsernameSignIn" class="active">Kirish</button>
            <button type="button" id="aliUsernameSignUp">Ro‘yxatdan o‘tish</button>
          </div>
          <label id="aliUsernameDisplayNameWrap" hidden>Ismingiz
            <input type="text" name="display_name" autocomplete="name" minlength="2" maxlength="100"></label>
          <label>Login nomi
            <input type="text" name="username" autocomplete="username" minlength="3" maxlength="32"
              pattern="[a-zA-Z][a-zA-Z0-9_.]{2,31}" required placeholder="masalan: ali_mijoz"></label>
          <label>Parol
            <input type="password" name="password" minlength="10" maxlength="72" autocomplete="current-password" required></label>
          <label id="aliUsernamePrivacy" class="checkline" hidden>
            <input type="checkbox" name="accepted_privacy">
            <span><a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer">
             Maxfiylik shartlari</a>ga roziman.</span>
          </label>
          <p class="muted">Bu kirish telefon raqami tasdiqlanganini anglatmaydi.
            Telefonni Telegram yoki SMS orqali alohida tasdiqlash kerak.</p>
          <button type="submit" class="auth-submit">Login nomi bilan kirish</button>
          <p class="status" role="status" aria-live="polite"></p>
          <button type="button" id="aliUsernameBack" class="ali-username-back">
            Telefon raqami orqali kirishga qaytish</button>
        </form>
        <p id="aliUsernameUnavailable" class="muted" hidden>
          Login nomi va parol bilan yangi kabinet yaratish doimiy ma’lumotlar bazasi
          ulangandan keyin yoqiladi. Hozir mavjud hisob bilan kiring.
        </p>
      </section>
      <div id="googleSignInBox" class="google-container"></div>
      <p id="googleSetupMessage" class="google-setup">Google hisob orqali kirish sozlanmoqda.</p>
      <div id="customerProfile" hidden></div>`;
    document.body.appendChild(d);
    $(".auth-close",d).addEventListener("click",()=>d.close());
    for(const button of d.querySelectorAll("[data-auth]")) button.addEventListener("click",()=>setAuthMode(button.dataset.auth==="register"));
    $("#customerAuthForm").addEventListener("submit", submitAuth);
    $("#authSmsSend").addEventListener("click", requestRegisterSms);
    $("#aliTelegramLogin").addEventListener("click", startTelegramLogin);
    $("#aliUsernameOpen").addEventListener("click",()=>openUsernameMode());
    $("#aliUsernameBack").addEventListener("click",()=>closeUsernameMode());
    $("#aliUsernameSignIn").addEventListener("click",()=>setUsernameRegister(false));
    $("#aliUsernameSignUp").addEventListener("click",()=>setUsernameRegister(true));
    $("#aliUsernameForm").addEventListener("submit",submitUsernameAccount);
    loadAuthOptions();
  }

  async function loadAuthOptions() {
    let ready=false, usernameReady=false;
    try {
      const options=await api("/api/auth/options");
      ready=options?.sms_registration === true;
      usernameReady=options?.username_signup === true;
    }catch(_){
      // An unavailable readiness endpoint must not make SMS appear to work.
      ready=false;
    }
    state.smsReady=ready;
    state.smsChecked=true;
    state.usernameReady=usernameReady;
    const area=$("#aliUsernameArea"),open=$("#aliUsernameOpen");
    if(area)area.hidden=false;
    if(open){
      open.disabled=!usernameReady;
      open.textContent=usernameReady
        ? "Login nomi va parol bilan kabinetga kirish / yaratish"
        : "Login nomi va parol — tayyorlanmoqda";
    }
    const notice=$("#aliUsernameUnavailable");
    if(notice)notice.hidden=usernameReady;
    setAuthMode(state.register);
    const send=$("#customerProfile .customer-sms-verify button");
    if(send)send.disabled=!ready;
  }


  function setUsernameRegister(register){
    state.usernameRegister=register;
    const form=$("#aliUsernameForm");
    if(!form)return;
    $("#aliUsernameDisplayNameWrap").hidden=!register;
    $("#aliUsernamePrivacy").hidden=!register;
    form.elements.display_name.required=register;
    form.elements.accepted_privacy.required=register;
    form.elements.password.minLength=register?10:1;
    form.elements.password.autocomplete=register?"new-password":"current-password";
    form.querySelector("button[type=submit]").textContent=register
      ?"Kabinet yaratish":"Login nomi bilan kirish";
    $("#aliUsernameSignIn").classList.toggle("active",!register);
    $("#aliUsernameSignUp").classList.toggle("active",register);
    form.querySelector(".status").textContent="";
  }
  function openUsernameMode(){
    if(!state.usernameReady)return;
    state.usernameSelected=true;
    $("#customerAuthForm").hidden=true;
    $("#customerDialog .auth-switch").hidden=true;
    $("#telegramLoginArea").hidden=true;
    $("#googleSignInBox").hidden=true;
    $("#googleSetupMessage").hidden=true;
    $("#aliUsernameOpen").hidden=true;
    $("#aliUsernameForm").hidden=false;
    setUsernameRegister(false);
  }
  function closeUsernameMode(){
    state.usernameSelected=false;
    $("#customerAuthForm").hidden=false;
    $("#customerDialog .auth-switch").hidden=false;
    $("#telegramLoginArea").hidden=false;
    $("#googleSignInBox").hidden=false;
    $("#googleSetupMessage").hidden=false;
    $("#aliUsernameOpen").hidden=false;
    $("#aliUsernameForm").hidden=true;
    setAuthMode(state.register);
  }
  async function submitUsernameAccount(event){
    event.preventDefault();
    const form=event.currentTarget,msg=form.querySelector(".status");
    if(!state.usernameReady){
      msg.textContent="Doimiy hisoblar bazasi ulanmaguncha ro‘yxatdan o‘tish mumkin emas.";
      return;
    }
    const values=new FormData(form);
    const username=String(values.get("username")||"").trim().toLowerCase();
    const password=String(values.get("password")||"");
    const button=form.querySelector("button[type=submit]");
    button.disabled=true;msg.textContent="Hisob tekshirilmoqda...";
    try{
      if(state.usernameRegister){
        await api("/api/auth/username/register",{
          method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            name:String(values.get("display_name")||"").trim(),
            username,password,accepted_privacy:values.get("accepted_privacy")==="on"
          })
        });
      }
      const answer=await api("/api/auth/username/login",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username,password})
      });
      await finishLogin(answer.access_token);
      form.reset();
      $("#customerDialog").close();
    }catch(error){
      msg.textContent=humanError(error);
    }finally{button.disabled=false;}
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
    const submit=$("#customerAuthForm .auth-submit");
    submit.textContent = register ? "Ro‘yxatdan o‘tish" : "Kirish";
    submit.disabled = Boolean(register && !state.smsReady);
    const smsButton=$("#authSmsSend");
    if(smsButton)smsButton.disabled=!state.smsReady;
    const smsInfo=$("#aliSmsAvailability");
    if(smsInfo)smsInfo.textContent=state.smsReady
      ? "Telefoningizga 6 xonali SMS kodi yuboriladi. Kod 5 daqiqa amal qiladi."
      : state.smsChecked
        ? "Hozir SMS tasdiqlash faol emas. Avval ro‘yxatdan o‘tgan bo‘lsangiz «Kirish»ni tanlang. Boshqa kirish usullari yuqoridagi oynada ko‘rsatiladi."
        : "SMS tasdiqlash holati tekshirilmoqda...";
    $("#customerAuthForm .status").textContent = register && !state.smsReady
      ? "Yangi mijoz ro‘yxati SMS sozlanmaguncha to‘xtatilgan. Telefon kodi yuborilmagan."
      : "";
    for (const b of document.querySelectorAll("[data-auth]")) b.classList.toggle("active",(b.dataset.auth==="register")===register);
  }
  function showLogin() {
    const d=$("#customerDialog");
    if (!d) return;
    if (me) {
      $("#aliUsernameArea").hidden=true;
      $("#customerAuthForm").hidden=true;
      $(".auth-switch",d).hidden=true;
      $(".auth-divider",d).hidden=true;
      $("#telegramLoginArea").hidden=true;
      $("#googleSignInBox").hidden=true;
      $("#googleSetupMessage").hidden=true;
      const profile=$("#customerProfile");
      profile.hidden=false;
      profile.replaceChildren();
      const intro=el("div","ali-profile-heading");
      intro.appendChild(el("h3","","Xush kelibsiz, "+(me.name||"Mijoz")+"!"));
      intro.appendChild(el("p","muted","Shaxsiy kabinet · "+(me.phone||"Telefon tasdiqlanmagan")));
      profile.appendChild(intro);
      const shortcuts=el("div","ali-profile-shortcuts");
      const action=(text,callback)=>{
        const b=el("button","ali-profile-shortcut",text);
        b.type="button";b.addEventListener("click",()=>{
          d.close();
          callback();
        });
        shortcuts.appendChild(b);
      };
      action("📦 Buyurtmalarim",()=>window.openAliOrders?.());
      action("♡ Sevimli taomlarim",()=>{
        const btn=document.getElementById("favoriteFilter");
        if(btn&&!btn.classList.contains("active"))btn.click();
        document.getElementById("foodGrid")?.scrollIntoView({behavior:"smooth"});
      });
      action("📍 Yetkazish manzilim",()=>window.getLocation?.());
      profile.appendChild(shortcuts);
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
      const send=el("button","btn btn-black","SMS-kod olish");
      send.type="button";send.disabled=!state.smsReady;
      const confirm=el("button","btn btn-black","Raqamni tasdiqlash");confirm.type="button";
      const h={"Authorization":"Bearer "+sessionStorage.getItem("ali_customer_token")};
      function verifiedScreen() {verification.replaceChildren(el("p","","✅ Telefon raqamingiz tasdiqlangan."));}
      verification.append(vStatus,vPhone,send,vCode,confirm);
      if(!state.smsReady){send.hidden=true;vCode.hidden=true;confirm.hidden=true;}
      profile.appendChild(verification);
      api("/api/auth/phone/status",{headers:h}).then(data=>{
        if(data.verified) verifiedScreen();
        else vStatus.textContent=state.smsReady
          ? "⚠ Telefon raqamini SMS orqali tasdiqlang."
          : "SMS tasdiqlash hozircha mavjud emas. Kod so‘ramang.";
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
      $("#aliUsernameArea").hidden=false;
      if(state.usernameSelected)closeUsernameMode();
      $("#customerAuthForm").hidden=false;
      $(".auth-switch",d).hidden=false;
      $(".auth-divider",d).hidden=false;
      $("#telegramLoginArea").hidden=false;
      $("#googleSignInBox").hidden=false;
      $("#googleSetupMessage").hidden=false;
      $("#customerProfile").hidden=true;
    }
    d.showModal();
  }
  async function requestRegisterSms() {
    if(!state.smsReady){
      const msg=$("#customerAuthForm .status");
      if(msg)msg.textContent="SMS tasdiqlash hozircha mavjud emas. Kod yuborilmadi.";
      return;
    }
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
      if (state.register && !state.smsReady) {
        throw new Error("SMS tasdiqlash hali ishga tushmagan. Kod yuborilmagan.");
      }
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

  // Telegram OIDC authorization-code + PKCE, bound to the originating browser.
  // No Telegram bot token, API secret, or SMS OTP is exposed in frontend JavaScript.
  const telegramPending="ali_telegram_pending_device";
  const telegramPendingAt="ali_telegram_pending_at";
  function randomTelegramDeviceSecret() {
    const bytes=new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes))
      .replace(/\+/g,"-").replace(/\//g,"_").replace(/=/g,"");
  }
  async function setupTelegramReadiness() {
    const button=$("#aliTelegramLogin"),hint=$("#aliTelegramStatus");
    if(!button||!hint)return;
    button.disabled=true;
    try {
      const response=await api("/api/auth/telegram/status");
      button.disabled=!response.available;
      hint.textContent=response.available
        ?"Telegram hisobingiz orqali tasdiqlash uchun bosing. Telefon raqamini ulashishga rozilik kerak."
        :"Telegram tasdiqlash hozircha yoqilmagan. Ro‘yxatdan o‘tish uchun SMS kodni tanlang.";
    }catch(_){
      button.disabled=true;
      hint.textContent="Telegram tasdiqlashni tekshirib bo‘lmadi. Hozircha SMS orqali ro‘yxatdan o‘ting.";
    }
  }
  async function startTelegramLogin(){
    const button=$("#aliTelegramLogin"),hint=$("#aliTelegramStatus");
    if(!button||button.disabled)return;
    if(!window.crypto?.getRandomValues){
      hint.textContent="Xavfsiz brauzer kerak. HTTPS orqali oching.";
      return;
    }
    button.disabled=true;
    try {
      const secret=randomTelegramDeviceSecret();
      const response=await api("/api/auth/telegram/start",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({device_secret:secret,channel:"web"})
      });
      const authURL=new URL(response.authorization_url);
      if(authURL.protocol!=="https:"||authURL.hostname!=="oauth.telegram.org"
         ||authURL.pathname!=="/auth")throw new Error("Telegram manzili noto‘g‘ri.");
      sessionStorage.setItem(telegramPending,secret);
      sessionStorage.setItem(telegramPendingAt,String(Date.now()));
      location.assign(authURL.href);
    }catch(error){
      hint.textContent=humanError(error)+
        " Telegram hali ulanmagan bo‘lsa, SMS tasdiqlashni tanlang.";
      button.disabled=false;
    }
  }
  async function finishTelegramBrowserLogin(){
    const fragment=new URLSearchParams(location.hash.replace(/^#/,""));
    const ticket=fragment.get("ali-telegram-ticket");
    if(!ticket)return;
    // Immediately strip short-lived ticket from visible navigation/address bar.
    history.replaceState(null,"",location.pathname+location.search);
    const secret=sessionStorage.getItem(telegramPending);
    const created=Number(sessionStorage.getItem(telegramPendingAt)||0);
    sessionStorage.removeItem(telegramPending);
    sessionStorage.removeItem(telegramPendingAt);
    const dialog=$("#customerDialog"),hint=$("#aliTelegramStatus");
    if(!/^[A-Za-z0-9_-]{43}$/.test(ticket)
      ||!/^[A-Za-z0-9_-]{43}$/.test(secret||"")
      ||!created || Date.now()-created>6*60*1000){
      if(hint)hint.textContent="Telegram tasdiqlash vaqti tugagan. Qaytadan boshlang.";
      if(dialog&&!dialog.open)dialog.showModal();
      return;
    }
    try {
      const result=await api("/api/auth/telegram/finish",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ticket,device_secret:secret})
      });
      await finishLogin(result.access_token);
      if(dialog?.open)dialog.close();
      // We never log or display ticket, token or Telegram identity.
      const label=$("#customerLoginBtn");
      if(label)label.setAttribute("title","Telegram orqali tasdiqlangan mijoz");
    }catch(error){
      if(hint)hint.textContent="Telegram kirishi yakunlanmadi: "+humanError(error);
      if(dialog&&!dialog.open)dialog.showModal();
    }
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
      // Phone cameras often generate 12+ megapixel photos. Resize locally:
      // avoid upload errors, remove EXIF/coordinates and reduce mobile data use.
      photoInput.addEventListener("change",async()=>{
        const file=photoInput.files?.[0];
        if(!file){clearPhoto();return;}
        if(!["image/jpeg","image/png","image/webp","image/heic","image/heif"].includes(file.type)
           || file.size>16_000_000){
          clearPhoto();
          window.alert("JPG/PNG/WEBP rasm (yoki telefon qo‘llaydigan HEIC), 16 MB gacha tanlang.");
          return;
        }
        uploadBtn.disabled=true;
        help.textContent="Surat tayyorlanmoqda...";
        let photoURL;
        try {
          photoURL=URL.createObjectURL(file);
          const photo=new Image();
          await new Promise((resolve,reject)=>{
            photo.onload=resolve;
            photo.onerror=()=>reject(new Error("Telefoningiz bu rasm formatini ocholmadi. JPG tanlang."));
            photo.src=photoURL;
          });
          const width=photo.naturalWidth, height=photo.naturalHeight;
          if(width<16 || height<16)throw new Error("Rasm juda kichik.");
          const scale=Math.min(1,1280/Math.max(width,height));
          const canvas=document.createElement("canvas");
          canvas.width=Math.max(16,Math.round(width*scale));
          canvas.height=Math.max(16,Math.round(height*scale));
          const ctx=canvas.getContext("2d");
          if(!ctx)throw new Error("Rasmni tayyorlab bo‘lmadi.");
          ctx.fillStyle="#ffffff";ctx.fillRect(0,0,canvas.width,canvas.height);
          ctx.drawImage(photo,0,0,canvas.width,canvas.height);
          let result=canvas.toDataURL("image/jpeg",.78);
          if(result.length>5_000_000)result=canvas.toDataURL("image/jpeg",.55);
          if(result.length>5_000_000)throw new Error("Rasm hajmi hali katta. Boshqa rasm tanlang.");
          attachedPhoto=result.substring(result.indexOf(",")+1);
          const thumb=el("img","ali-photo-thumb");
          thumb.alt="Tanlangan taom surati";thumb.src=result;
          const remove=el("button","ali-photo-remove","✕ Olib tashlash");
          remove.type="button";remove.addEventListener("click",clearPhoto);
          preview.replaceChildren(thumb,el("span","","Surat tayyor"),remove);
          preview.hidden=false;
          if(!$("#aliInput")?.value.trim())$("#aliInput").value="Rasmdagi taomning taxminiy kaloriyasi qancha?";
        }catch(err){clearPhoto();window.alert(err.message||"Rasmni tayyorlab bo‘lmadi.");}
        finally {
          if(photoURL)URL.revokeObjectURL(photoURL);
          uploadBtn.disabled=false;
          help.textContent="Surat AI xizmatiga tahlil uchun yuboriladi, saqlanmaydi. Kaloriya faqat taxminiy.";
        }
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
  if(location.hash.includes("ali-telegram-ticket=")) finishTelegramBrowserLogin();
  else restoreLogin();
})();