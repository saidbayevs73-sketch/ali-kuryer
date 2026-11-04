import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.0/firebase-app.js";
import {
  getAuth, GoogleAuthProvider, signInWithRedirect, getRedirectResult,
  onAuthStateChanged, signOut
} from "https://www.gstatic.com/firebasejs/11.6.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyB-McrwqzgQh3j-0Ve5vjkb0rgF6ZlDE1g",
  authDomain: "ali-kuryer-9d6bb.firebaseapp.com",
  projectId: "ali-kuryer-9d6bb",
  storageBucket: "ali-kuryer-9d6bb.firebasestorage.app",
  messagingSenderId: "1088566467185",
  appId: "1:1088566467185:android:76b488bc28e630d5abd9d0"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: "select_account" });

function showUser(user) {
  const panel = document.getElementById("accountPanel");
  const button = document.getElementById("loginBtn");
  if (button) button.innerHTML = "♙ <span>" + (user.displayName || "Kabinet").replace(/[<>&"]/g, "") + "</span>";
  if (!panel) return;
  panel.hidden = false;
  panel.innerHTML = "";
  const card = document.createElement("div");
  card.style.cssText = "padding:20px;border:1px solid #eee;border-radius:18px;background:#fff;margin:14px 0";
  const title = document.createElement("h2"); title.textContent = "Mening hisobim";
  const name = document.createElement("p"); name.textContent = user.displayName || "Google foydalanuvchisi";
  const email = document.createElement("p"); email.textContent = user.email || "";
  const status = document.createElement("small"); status.textContent = "Google hisobi ulandi";
  const logout = document.createElement("button"); logout.type = "button"; logout.textContent = "Hisobdan chiqish";
  logout.style.cssText = "margin-top:12px;padding:11px 16px;border:0;border-radius:10px;background:#d91432;color:white;font-weight:700";
  logout.addEventListener("click", async () => { try { await signOut(auth); location.reload(); } catch(e) { alert("Chiqishda xatolik: "+e.message); } });
  card.append(title,name,email,status,logout); panel.appendChild(card);
}
function friendlyError(error) {
  const map = {
    "auth/unauthorized-domain": "Bu sayt domeni Firebase’da ruxsat etilmagan. Firebase Console → Authentication → Settings → Authorized domains bo‘limiga ali-kuryer-web.onrender.com domenini qo‘shing.",
    "auth/operation-not-allowed": "Firebase’da Google kirish provayderi yoqilmagan.",
    "auth/network-request-failed": "Internet aloqasini tekshirib, qayta urinib ko‘ring."
  };
  alert(map[error?.code] || ("Google orqali kirish amalga oshmadi: " + (error?.message || "Noma’lum xatolik")));
}
getRedirectResult(auth).then(result => { if (result?.user) showUser(result.user); }).catch(friendlyError);
onAuthStateChanged(auth, user => { if (user) showUser(user); });

document.addEventListener("click", async event => {
  const button = event.target?.closest?.("#loginBtn,[data-google-login]");
  if (!button) return;
  event.preventDefault(); event.stopPropagation();
  if (event.stopImmediatePropagation) event.stopImmediatePropagation();
  if (window.AliKuryerNative?.signInWithGoogle) { window.AliKuryerNative.signInWithGoogle(); return; }
  if (auth.currentUser) { showUser(auth.currentUser); return; }
  try { await signInWithRedirect(auth, provider); }
  catch (error) { friendlyError(error); }
}, true);

window.AliKuryerWebAuth = { auth, signOut };
