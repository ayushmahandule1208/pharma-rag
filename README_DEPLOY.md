# 🚀 PharmaRAG Deployment Guide (100% Free)

## Architecture

```
Frontend → Vercel (Free)
Backend  → Hugging Face Spaces (Free, 16GB RAM)
Vectors  → FAISS (in-memory, lightweight)
Models   → sentence-transformers (all-MiniLM-L6-v2)
```

---

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pharma-rag.git
git push -u origin main
```

---

## Step 2: Deploy Backend on Hugging Face Spaces

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Configure:
   - **Space name**: `pharma-rag-api`
   - **License**: MIT
   - **SDK**: `Docker`
   - **Hardware**: `CPU basic` (free)

4. Clone your new Space locally:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/pharma-rag-api
   cd pharma-rag-api
   ```

5. Copy your backend files:
   ```bash
   # Copy these files/folders:
   # - app/
   # - app.py
   # - requirements.txt
   # - Dockerfile
   # - data/ (empty folders)
   ```

6. Push to HF Spaces:
   ```bash
   git add .
   git commit -m "Deploy PharmaRAG API"
   git push
   ```

7. Wait 5-10 minutes for build

8. Your API is live at:
   ```
   https://YOUR_USERNAME-pharma-rag-api.hf.space
   ```

---

## Step 3: Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → Sign up free

2. Click **"Add New Project"** → Import GitHub repo

3. Configure:
   | Setting | Value |
   |---------|-------|
   | Framework | `Next.js` |
   | Root Directory | `frontend` |

4. Add Environment Variable:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://YOUR_USERNAME-pharma-rag-api.hf.space` |

5. Deploy!

---

## Step 4: (Optional) Add OpenAI API Key

For AI-generated responses instead of template responses:

1. Go to HF Spaces → Settings → Variables
2. Add secret:
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

---

## ✅ Done!

| Service | URL |
|---------|-----|
| Frontend | `https://your-app.vercel.app` |
| Backend | `https://YOUR_USERNAME-pharma-rag-api.hf.space` |
| API Docs | `https://YOUR_USERNAME-pharma-rag-api.hf.space/docs` |

---

## 🔧 Troubleshooting

### "Space is sleeping"
HF Spaces free tier sleeps after 48 hours of inactivity.
- First request takes ~30 seconds to wake up
- Use UptimeRobot to keep it awake (ping every 30 min)

### "Build failed"
- Check the build logs in HF Spaces
- Ensure Dockerfile and requirements.txt are correct

### "CORS error"
- The backend allows all origins by default
- Check browser console for the actual error

