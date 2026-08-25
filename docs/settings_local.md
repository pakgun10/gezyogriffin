

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

Menjalankan aplikasi:
```bash
/home/pgun/apps/gezyogriffin/run-isolated.sh run
```
Perintah iitu berjalan foreground; biarkan terminal tetap terbuka.


Untuk  pemeriksaan konfigurasi, opsional:
```bash
/home/pgun/apps/gezyogriffin/run-isolated.sh doctor
```
Jika ingin cek konfigurasi provider terlebih dahulu, jalankan `doctor`. Namun pada versi sekarang, `doctor` kadang tidak otomatis membaca `.env`, sehingga bisa menampilkan token “missing” walaupun file state sudah terisi.

Jika bot sudah berjalan dan `.env` diubah, lakukan restart proses bot, bukan menjalankan banyak instance bersamaan.

Setelah mengubah `.env`, jalankan restart aman ini di terminal:

```bash
APP_DIR=/home/pgun/apps/gezyogriffin

BOT_PID=$(ps -eo pid=,args= | awk '$0 ~ /\/home\/pgun\/apps\/gezyogriffin\/\.venv\/bin\/opengriffin run$/ {print $1; exit}')

if [ -n "$BOT_PID" ]; then
  kill -TERM "$BOT_PID"
  sleep 2
fi

cd "$APP_DIR"
setsid -f ./run-isolated.sh run >> "$APP_DIR/state/opengriffin.log" 2>&1

sleep 3
ps -eo pid,ppid,etime,args | grep 'opengriffin run' | grep -v grep
tail -n 20 "$APP_DIR/state/opengriffin.log"
```

Gunakan `run-isolated.sh`, bukan menjalankan `opengriffin run` langsung, agar `HOME` dan state terisolasi tetap benar.

### Gambar Telegram

Bot meneruskan foto Telegram (maksimum 8 MB) sebagai input vision ke provider
OpenAI-compatible yang dikonfigurasi, termasuk 9router. Di grup, foto hanya
dijawab jika dikirim dengan mention bot atau sebagai reply ke pesan bot. Anda
juga dapat membalas foto pengguna dengan mention bot; foto yang direply akan
ikut diteruskan ke model.

Untuk provider custom/9router, bot menyimpan konteks teks enam percakapan
terakhir per chat. Gambar terakhir disimpan hanya di memori proses selama 30
menit untuk mendukung pertanyaan lanjutan; `/reset` menghapus konteks tersebut.


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
