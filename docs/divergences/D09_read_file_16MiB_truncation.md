# D09 — `read_file` do lean_single trunca em silêncio em 16 MiB (16 777 216 bytes)

```bash
head -c 20096256 /dev/zero | tr '\0' 'a' > /tmp/big.dat      # 20 096 256 bytes
cat > /tmp/rf.sio <<'SIO'
fn main() -> i32 with IO {
    let s = read_file("/tmp/big.dat")
    print_int(str_len(s))
    print("\n")
    return 0
}
SIO
bin/souc run /tmp/rf.sio                                       # Madaros: 20096256
SOUNIO_SOUC_ENGINE=lean_single bin/souc run /tmp/rf.sio        # lean_single: 16777216 (sem erro, rc 0)
```

Consequência medida no gate: o OMNI2 2020-2025 (20 096 256 bytes, 52 608 linhas) é lido com 43 919
linhas sob lean_single: `calib` devolve `n_records 43919` em vez de `52608` e todos os quantis mudam.
