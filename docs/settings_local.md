

`/home/pgun/apps/gezyogriffin`

Yang dilakukan:

- Python `3.11.15` virtualenv dibuat di `.venv`
- Semua optional Python extras terpasang: 122 paket
- Ukuran virtualenv sekitar 976 MB
- State terisolasi di:
  - `/home/pgun/apps/gezyogriffin/state`
  - `/home/pgun/apps/gezyogriffin/home/.claude`
- 20 bundled skills disalin ke home terisolasi
- Port webhook diatur ke `18645`
- Port aplikasi lama tidak diubah
- Wrapper terisolasi tersedia di [run-isolated.sh](/home/pgun/apps/gezyogriffin/run-isolated.sh)
- Unit service tersedia di [opengriffin-local.service](/home/pgun/apps/gezyogriffin/opengriffin-local.service)

Validasi:

- `doctor` berhasil memuat Claude Agent SDK
- `100 passed, 2 skipped` untuk test repo
- Port `18645` masih kosong
- State tidak memakai `~/.claude` lama

Bot belum dijalankan karena credential belum tersedia. Tambahkan token Telegram dan API provider di:

`/home/pgun/apps/gezyogriffin/state/.env`

Untuk mencoba manual:

```bash
/home/pgun/apps/gezyogriffin/run-isolated.sh doctor
/home/pgun/apps/gezyogriffin/run-isolated.sh run
```

Service systemd sudah disiapkan, tetapi belum diaktifkan agar bot tidak gagal berulang tanpa credential.


Ya, ada dua komponen web yang berbeda:

1. Dashboard runtime

File:

[dashboard/server.py](/home/pgun/apps/gezyogriffin/src/opengriffin/dashboard/server.py)

Menyediakan dashboard lokal berisi:

- Skill graph
- Journal
- Usage/token panel
- API read-only seperti `/api/skills`, `/api/journal`, `/api/usage`

Dashboard ini tidak otomatis dijalankan oleh `opengriffin run`. Port default-nya `8765` dan hanya bind ke `127.0.0.1`.

Menjalankannya:

```bash
cd /home/pgun/apps/gezyogriffin
HOME=/home/pgun/apps/gezyogriffin/home \
OPENGRIFFIN_HOME=/home/pgun/apps/gezyogriffin/state \
.venv/bin/python -m opengriffin.dashboard.server
```

Lalu buka:

```text
http://127.0.0.1:8765
```

2. `apps/web`

Direktori [apps/web](/home/pgun/apps/gezyogriffin/apps/web) adalah landing/marketing website berbasis Next.js, bukan antarmuka chat agent.

Jadi saat ini OpenGriffin belum memiliki web chat UI penuh. Antarmuka utama tetap Telegram; dashboard hanya untuk observability. Webhook di port `18645` juga bukan halaman web, melainkan endpoint HTTP untuk menerima event eksternal.

Catatan: dashboard saat ini masih membaca state dari struktur `~/.opengriffin`, sehingga pada instalasi terisolasi kita mungkin perlu sedikit penyesuaian agar journal dan usage membaca `/home/pgun/apps/gezyogriffin/state` dengan benar.
