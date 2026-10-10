# Ali Kuryer Firebase SMS integratsiyasi (Android Mijoz)

Firebase project: `ali-kuryer`. Android package: `uz.alikuryer.customer`.
Uploaded mobile `google-services.json` is installed in customer-only asset source
set: `android/mijoz/app/src/mijoz/assets/google-services.json`.
This is a public **client configuration**, not a Firebase Admin service-account
key. Never upload Admin credentials to GitHub.

## Android implementation

`AliFirebasePhone.kt` initializes the Firebase app from the customer JSON and
uses Firebase Authentication's `PhoneAuthProvider` SMS verification,
automatic credential verification, or user-entered code. No SMS inbox permission
is requested. Only a Firebase-signed ID token is handed to our backend.

`POST /api/auth/firebase/phone-login` verifies that signature against Google
public certificates, *exactly* checks the expected Firebase project, checks
that the sign-in provider is `phone`, enforces fresh authentication and a
`+998` phone, and creates customer-only accounts. Staff accounts cannot be
claimed by phone-only login. Phone binding is persisted to DB.

## One-time Firebase console steps for real SMS delivery

1. Firebase Console > **Security > Authentication > Sign-in method**:
   enable **Phone**.
2. Authentication > **Settings > SMS region policy**: explicitly allow
   **Uzbekistan** (all regions are disallowed by default in new projects).
3. In Project settings > General > Your apps > Ali Kuryer Mijoz > SHA
   certificate fingerprints, add SHA-1 and SHA-256 fingerprints of the
   **exact APK signing certificate**.
4. This is a *testing APK signed by GitHub Actions debug key*, and the
   debug key is newly generated on each clean GitHub Actions runner.
   The test fingerprints are valid **only for that particular APK**:
   SHA-1: `C4:9E:D2:8D:47:CB:94:49:DB:41:A7:5C:AD:31:F5:EB:18:CE:87:1F`
   SHA-256: `FA:7F:FB:1C:82:B9:5A:08:60:EE:6D:30:1D:81:46:99:27:A9:F8:89:5D:F7:10:0C:44:28:6A:63:5C:B6:39:7A`
   For production, create, protect and back up a *stable release signing
   key*, configure CI signing securely, then register that signing
   certificate and the Google Play app-signing certificate if applicable.
   Do not commit the private keystore/password or reuse a public debug key.
5. Real Firebase Phone Authentication SMS is billed per message and
   requires the appropriate billing plan (Blaze). Obtain owner approval
   before enabling charges. Prefer Firebase fictitious test phone numbers
   for initial no-SMS tests.
6. Firebase Android Phone Auth can invoke Play Integrity or reCAPTCHA;
   both may require SHA fingerprints and browser app verification setup.
7. Configure Render `ali-kuryer` with:
   `FIREBASE_PROJECT_ID=ali-kuryer`
   `FIREBASE_PHONE_ENABLED=1`
   *ONLY AFTER* connecting `DATABASE_URL` to persistent PostgreSQL
   and confirming database schema and app integration. No service-account
   private key is needed for public-certificate **ID token verification**.
   Do not set the flag until database cutover is verified.
8. Send a test SMS to a controlled phone, enter it, verify the backend
   returns a signed customer JWT. Check existing-account and new-account
   cases. Do not claim Firebase SMS is live until end-to-end tested.

**Security note:** Firebase SMS verifies current possession of the number,
not the person's identity; SIM-swaps and recycled numbers remain possible.
Retain admin/staff role checks and additional security for sensitive actions.
