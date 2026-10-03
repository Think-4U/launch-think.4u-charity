# Think4U Trust — Launch Page

A polished official launch page for Think4U Trust with a button-triggered launch animation, secure admin dashboard, and configurable branding.

---

## 🌐 How It Works

```
Visitor → launch.think4u.org → presses LAUNCH THINK4U
           → 10-second launch animation → success screen
           → 15-second countdown, or “Redirect now”
           → https://think4u.org
```

The page never redirects on load or when its optional launch-date countdown ends.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- pip

### 2. Clone / Navigate to the project

```bash
cd "e:\LAPTOP\launch think4u"
```

### 3. Create virtual environment and install dependencies

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env`:

```bash
# Windows:
copy .env.example .env

# macOS/Linux:
cp .env.example .env
```

Edit `.env` with your values (especially `SECRET_KEY`).

### 5. Set admin password

```bash
python scripts/hash_password.py
```

This prints a bcrypt hash. Copy it into `.env` as `ADMIN_PASSWORD_HASH`.

> **Default credentials** (for local testing only):  
> Username: `admin`  
> Password: `admin@Think4U#2027`  
> ⚠️ Change this before deploying to production!

### 6. Run the app

```bash
python app.py
```

Visit:
- **Launch page:** http://127.0.0.1:5000/
- **Admin login:** http://127.0.0.1:5000/admin/login
- **Admin dashboard:** http://127.0.0.1:5000/admin/dashboard (after login)

---

## ▲ Deploying to Vercel

Import this GitHub repository into Vercel and keep the project root as the Root Directory. Vercel detects the Flask app in `app.py`; `vercel.json` includes the Jinja templates and public images in its Python Function bundle. The site logo and favicon are served from `public/`.

Add these Environment Variables in Vercel Project Settings for Production (and Preview if needed):

- `SECRET_KEY`: a long random secret used to sign admin sessions.
- `ADMIN_USERNAME`: the administrator login name.
- `ADMIN_PASSWORD_HASH`: generate with `python scripts/hash_password.py` and paste the bcrypt hash.
- `SESSION_COOKIE_SECURE`: `true`.

The launch page runs without extra services. Vercel Functions have ephemeral writable storage: admin changes written to `/tmp/think4u-launch-config.json` can be lost between function instances or deployments. For admin configuration that must persist, connect a durable external database or object store before relying on dashboard edits. The in-memory login and launch rate limits also reset with function instances, so use an edge/WAF rate limit for deployment-wide enforcement.

---

## 🔐 Admin Setup

### Changing the Admin Password

1. Run `python scripts/hash_password.py`
2. Enter your new password when prompted
3. Copy the output hash into `.env`:
   ```
   ADMIN_PASSWORD_HASH=$2b$12$...
   ```
4. Restart the app (or redeploy)

### Changing the Admin Username

In `.env`:
```
ADMIN_USERNAME=your_username
```

---

## 📅 Configuring Launch Date & Time

1. Log in at `/admin/login`
2. Go to **Launch Settings** in the dashboard
3. Set:
   - **Launch Date** (YYYY-MM-DD format)
   - **Launch Time** (24-hour format, e.g., `09:00`)
   - **Timezone** (e.g., `Asia/Kolkata`)
4. Click **Save Launch Settings**

The countdown on the public page updates immediately.

---

## 🚀 Launch interaction

The launch button must be enabled in the admin dashboard. On click, the app authorizes a one-use launch token, plays a 10-second animation, then shows a success message with a 15-second countdown and a **Redirect now** link. The countdown finishing or visiting the page never starts a redirect.

---

## 🗂 Project Structure

```
launch think4u/
├── app.py                    # Flask app — routes, auth, API
├── config.py                 # Config loader/saver
├── requirements.txt
├── .env                      # Secrets (DO NOT COMMIT)
├── .env.example              # Template for .env
├── .gitignore
├── Procfile                  # For Heroku/Render deployment
├── runtime.txt               # Python version
├── data/
│   └── launch_config.json    # Admin-saved configuration (auto-created)
├── public/
│   └── images/               # Vercel-served logo and favicon
│       ├── logo-white.png
│       └── favicon.ico
├── templates/
│   ├── launch.html           # Public launch page
│   └── admin/
│       ├── login.html        # Admin login
│       └── dashboard.html    # Admin dashboard
└── scripts/
    └── hash_password.py      # Password hash generator
```

---

## 🖼 Adding Your Logo

Place your logo file at:
```
public/images/logo-white.png
```

Or upload to any hosting (e.g., Supabase storage) and update the **Logo URL** field in the admin dashboard under **Branding**.

The admin dashboard lets you set:
- Logo URL
- Favicon URL
- Primary colour (dark red `#1f0606`)
- Accent colour (gold `#d58d4b`)

---

## 🌐 Deployment Instructions

### Option A: Render.com (Recommended — Free Tier Available)

1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your GitHub/GitLab repo
3. Settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. Add all environment variables from `.env` in the Render dashboard under **Environment**
5. Deploy!

> **Important:** On Render, use a persistent disk or external storage (e.g., Supabase) for `data/launch_config.json`, as the filesystem resets on each deploy. Alternatively, set `DATA_PATH` environment variable to a mounted disk path.

### Option B: Railway

1. Create project → Deploy from GitHub
2. Add environment variables
3. Railway auto-detects `Procfile`

### Option C: Heroku

```bash
heroku create think4u-launch
heroku config:set SECRET_KEY="your-secret" ADMIN_USERNAME="admin" ADMIN_PASSWORD_HASH="$2b$..."
git push heroku main
```

> Same note about persistent filesystem applies.

---

## 🌍 DNS / Subdomain Configuration

To serve from `launch.think4u.org`:

### Cloudflare (recommended)

1. Log in to Cloudflare → your `think4u.org` zone
2. Go to **DNS** → Add record:
   ```
   Type:  CNAME
   Name:  launch
   Target: your-app.onrender.com  (or your deployment URL)
   Proxy: ✅ Proxied (orange cloud)
   ```
3. In your deployment platform, add `launch.think4u.org` as a **Custom Domain**
4. Cloudflare handles HTTPS automatically

### Other DNS providers

Add a CNAME record:
```
launch.think4u.org  →  your-app.onrender.com
```

---

## 🔒 Security Notes

| Feature | Implementation |
|---|---|
| Admin password | bcrypt hashed, never stored in plaintext |
| Secrets | Environment variables only, never in code |
| CSRF protection | Session token on all POST forms |
| Rate limiting | 5 attempts / 15-min lockout (in-memory) |
| Security headers | X-Frame-Options, X-Content-Type, Referrer-Policy |
| Session | HTTPOnly, SameSite=Lax, Secure in production |
| Launch action | Short-lived, one-use token and request throttling |
| Redirect destination | Fixed and validated as `https://think4u.org` |
| Response headers | Content Security Policy, frame, MIME, referrer, and permissions policies |

---

## ⚙️ Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | Flask session secret (min 32 chars) |
| `ADMIN_USERNAME` | ✅ | `admin` | Admin login username |
| `ADMIN_PASSWORD_HASH` | ✅ | — | bcrypt hash from `hash_password.py` |
| `FLASK_DEBUG` | — | `false` | Enable debug mode (never use in prod) |
| `FLASK_HOST` | — | `127.0.0.1` | Bind host |
| `FLASK_PORT` | — | `5000` | Bind port |
| `SESSION_COOKIE_SECURE` | — | `false` | Set `true` on HTTPS |
| `SESSION_COOKIE_SAMESITE` | — | `Lax` | CSRF protection level |

---

## ✅ Testing Checklist

- [ ] Public page loads at `/`
- [ ] Countdown ticks correctly (verify UTC target)
- [ ] Countdown pauses / corrects on tab switch
- [ ] Mobile responsive (test at 375px, 768px, 1440px)
- [ ] Admin login rejects wrong password
- [ ] Admin login locks after 5 failed attempts
- [ ] Admin save updates config
- [ ] Admin preview shows live page
- [ ] Launch button can be disabled in the admin dashboard
- [ ] A launch token cannot be replayed
- [ ] Visitors can manually choose Redirect now
- [ ] SEO meta tags visible in page source
- [ ] OG image tag set correctly
- [ ] Social media links open correctly
- [ ] Contact email is a valid mailto: link
- [ ] Logo loads (or fallback hides gracefully)
- [ ] Favicon displays in browser tab
- [ ] No console JS errors
- [ ] `.env` is NOT committed to git (check `.gitignore`)

---

## 📞 Support

For issues or questions, contact the Think4U Trust technical team at `info@think4u.org`.
