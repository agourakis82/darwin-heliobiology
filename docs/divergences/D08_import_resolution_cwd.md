# D08 — lean_single resolve `use` relativo ao CWD; Madaros, relativo ao arquivo de entrada

Reproduz (nenhum arquivo extra além dos 3 abaixo, em um diretório `imp/`):

```
imp/a.sio        pub fn one() -> i64 { 1 }
imp/sub/b.sio    use a::{one}
                 pub fn two() -> i64 { one() + 1 }
imp/main.sio     use a::{one}
                 use sub::b::{two}
                 fn main() -> i32 with IO { print_int(one() + two()); print("\n"); return 0 }
```

```bash
cd / && bin/souc run /tmp/imp/main.sio                              # Madaros: imprime 3
cd / && SOUNIO_SOUC_ENGINE=lean_single bin/souc run /tmp/imp/main.sio
#   error[E224]: unreadable import: self-hosted/a.sio
cd /tmp/imp && SOUNIO_SOUC_ENGINE=lean_single bin/souc run main.sio # lean_single: imprime 3
```
