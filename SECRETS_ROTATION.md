# Secrets Rotation + Making the Repo Private

**Status: NOT DONE. Follow this end to end, in order.**

Why this exists: `docker-compose.yml` carried the live `POSTGRES_PASSWORD` and
`DJANGO_SECRET_KEY` in plaintext from commit `d92ae84` until the commit that
added this file. The repo has been **public** that whole time, so both values
must be treated as **compromised** - assume a stranger has them.

The decision taken was: **rotate the credentials, then make the repo private.**
Git history is NOT being rewritten, so the old values stay visible in history -
which is exactly why rotating them (making them worthless) is the step that
actually matters.

> Run everything in this document **on the server**, from
> `/home/mmilab/Desktop/Database/phytosynergy-project/`, unless a step says
> "on the laptop".

---

## The ordering trap - read before starting

Two steps break things if done in the wrong order:

1. **`.env` must exist on the server BEFORE you pull the compose change.**
   `docker-compose.yml` now reads secrets from `.env`. Pull it without `.env`
   in place and Compose refuses to start the stack. (It fails loudly rather
   than silently, by design - see the `:?` syntax in the file - but the site is
   still down until you fix it.) **Do Stage 1 and 2 before Stage 3.**

2. **The server needs a deploy key BEFORE the repo goes private.**
   A public repo can be pulled anonymously; a private one cannot. The server
   currently pulls over HTTPS with no credentials, so the moment you flip
   visibility, `git pull` on the server starts failing. **Do Stage 4 before
   Stage 5.** The laptop is unaffected - pushing already required
   authentication, so its existing credentials keep working.

---

## Stage 0 - Back up first

```bash
cd ~/Desktop/Database/phytosynergy-project
./scripts/backup_db.sh manual
```

You are about to change the database password. If anything goes sideways you
want a backup from *before* that.

---

## Stage 1 - Generate the new values

Generate them **on the server**, and keep the terminal open - you will paste
both into `.env` in Stage 2.

```bash
docker compose exec web python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(36).replace('-','').replace('_',''))"
```

```bash
docker compose exec web python -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64).replace('-','').replace('_',''))"
```

**Why alphanumeric and not Django's own `get_random_secret_key()`:** that helper
emits punctuation like `$ % # ( )`. Two things break on it here:

- Docker Compose treats `$` inside a `.env` value as a variable reference, so
  any `$` is silently mangled and the value that reaches Django is not the one
  you generated.
- `POSTGRES_PASSWORD` is embedded in `DATABASE_URL`, which is a URL. A password
  containing `@ : / ? #` or `%` breaks URL parsing and Django fails to connect
  with a misleading error.

Alphanumeric values sidestep both. A 36/64-character alphanumeric string has
far more entropy than needed; nothing is lost by excluding punctuation.

---

## Stage 2 - Change the database password, then write `.env`

The Postgres password lives **inside the database**. `POSTGRES_PASSWORD` in
compose only applies when the data volume is first initialised, so editing it
alone changes nothing on an existing database. You must `ALTER USER`.

Change it in Postgres (substitute your new value):

```bash
docker compose exec db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'NEW_POSTGRES_PASSWORD_HERE';"
```

Then create `.env` next to `docker-compose.yml`:

```bash
cp .env.example .env
nano .env
```

Paste both generated lines in, save, and lock the file down:

```bash
chmod 600 .env
```

Confirm it is ignored by git - this must print nothing:

```bash
git check-ignore -v .env && git status --short | grep -F '.env' ; echo "(no .env in status above = correct)"
```

---

## Stage 3 - Deploy the compose change

Only now pull the change that switches compose over to `.env`:

```bash
git pull origin main
docker compose config >/dev/null && echo "compose config OK - secrets resolved from .env"
```

`docker compose config` renders the file with substitution applied. If `.env`
is missing or a key is absent, it fails here with the message from the `:?`
default - which is much better than finding out when the site is down.

Then restart the stack so the new values take effect:

```bash
docker compose up -d
docker compose ps
docker compose logs --tail=50 web
```

**Expected consequences, both normal:**

- Everyone is signed out. `DJANGO_SECRET_KEY` signs session cookies, so
  rotating it invalidates every existing session and any outstanding
  password-reset link.
- If `web` cannot reach the database, the `ALTER USER` value and the `.env`
  value disagree. Recheck both; the backup from Stage 0 is your safety net.

Verify the site actually works before continuing - log in, load `/database/`.

---

## Stage 4 - Give the server a deploy key (BEFORE going private)

Generate a key **on the server**, with no passphrase so unattended deploys and
cron keep working:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/phytosynergy_deploy -N "" -C "phytosynergy-server-deploy"
cat ~/.ssh/phytosynergy_deploy.pub
```

Add the printed public key to GitHub:

> Repo -> **Settings** -> **Deploy keys** -> **Add deploy key**.
> Title: `phytosynergy server (read-only)`.
> **Leave "Allow write access" UNCHECKED.** The server only ever pulls; a
> read-only key means a compromised server cannot rewrite your repository.

Tell SSH which key to use for GitHub:

```bash
cat >> ~/.ssh/config <<'EOF'

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/phytosynergy_deploy
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

Point the server's remote at SSH instead of HTTPS:

```bash
cd ~/Desktop/Database/phytosynergy-project
git remote set-url origin git@github.com:argajitsarkr/phytosynergy-db-project.git
git remote -v
```

**Test it now, while the repo is still public.** This is the whole point of
doing Stage 4 first - if the key is wrong you find out while anonymous access
is still available as a fallback:

```bash
ssh -T git@github.com    # expect: "Hi argajitsarkr/phytosynergy-db-project! You've successfully authenticated..."
git fetch origin && echo "SSH fetch works - safe to make the repo private"
```

Do not proceed until that fetch succeeds.

---

## Stage 5 - Make the repository private

> GitHub UI: Repo -> **Settings** -> **General** -> scroll to
> **Danger Zone** -> **Change repository visibility** -> **Make private**.

---

## Stage 6 - Verify both machines still work

On the **server**:

```bash
cd ~/Desktop/Database/phytosynergy-project && git fetch origin && echo "SERVER OK"
```

On the **laptop** (`D:\Sites\Projects`):

```bash
git fetch origin && echo "LAPTOP FETCH OK"
```

The laptop uses HTTPS with stored credentials (Git Credential Manager on
Windows). Because you own the repo, those same credentials grant access to it
as a private repo, so nothing should change. If it *does* prompt, sign in
through the credential manager as usual - do not paste a token into a command
where it lands in shell history.

---

## After it is done

- Update the **Open items** list in `CLAUDE.md`: items 1 and 2 are closed.
- The old secrets remain in git history. They are now worthless, and with the
  repo private that history is no longer publicly readable. If you later decide
  you want them gone entirely, that is a `git-filter-repo` rewrite plus a
  force-push, which changes every commit SHA - a separate, deliberate exercise.
- The cloudflared credentials JSON was never committed (it is mounted from
  `/home/mmilab/.cloudflared/`), so it needs no rotation.

## If something breaks

| Symptom | Cause | Fix |
|---------|-------|-----|
| Compose errors mentioning `POSTGRES_PASSWORD is not set` | `.env` missing or incomplete | Recreate it from `.env.example` (Stage 2) |
| `web` cannot connect to the database | `ALTER USER` value != `.env` value | Re-run the `ALTER USER` with the exact `.env` value |
| Server `git pull` asks for a username/password | Repo is private and the remote is still HTTPS | Redo Stage 4 (`git remote set-url` to the SSH URL) |
| `ssh -T git@github.com` says "Permission denied" | Deploy key not added, or `~/.ssh/config` wrong | Recheck the pasted public key and `IdentityFile` path |
| Everyone signed out | Expected - `DJANGO_SECRET_KEY` rotated | Log in again |
