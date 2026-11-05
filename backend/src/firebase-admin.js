import { initializeApp, cert, getApps } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";

let authInstance;

function readServiceAccount() {
  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.private_key) parsed.private_key = parsed.private_key.replace(/\\n/g, "\n");
    return parsed;
  } catch (error) {
    console.error("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON:", error.message);
    return null;
  }
}

export function getFirebaseAdminAuth() {
  if (authInstance) return authInstance;
  const serviceAccount = readServiceAccount();
  if (!serviceAccount) return null;
  const app = getApps()[0] || initializeApp({ credential: cert(serviceAccount) });
  authInstance = getAuth(app);
  return authInstance;
}
