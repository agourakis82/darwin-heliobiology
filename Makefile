# Nucleo em Sounio (sio/) e seus oraculos. Ver README "Nucleo em Sounio" e docs/SIO_CORE_SPEC.md.
#
#   make toolchains    instala os toolchains pinados em ~/.local/opt (gate/install_toolchains.sh)
#   make sio-test      souc check + testes .sio + gate do gemeo + referencias F#/Futhark + provas F*
#   make corroborate   relatorio Python x Sounio (nunca falha; nao e juiz)
#   make bench         tempos Sounio x F# x Futhark no OMNI2 completo
#   make lean-single   divergencias Madaros x lean_single (relatorio)
#
# SOUNIO_DIR  = clone do Sounio-lang/sounio no commit de gate/toolchains.env (default ../work/sounio-ref)
SOUNIO_DIR ?= $(abspath ../work/sounio-ref)
export SOUNIO_DIR
PYTHON ?= python3

.PHONY: toolchains omni-dat sio-check sio-run sio-twin sio-foreign sio-fstar sio-inventory sio-test corroborate bench lean-single

toolchains:
	bash gate/install_toolchains.sh

omni-dat:
	bash gate/prepare.sh

sio-check:
	bash gate/sio_check.sh

sio-run:
	bash gate/sio_tests.sh

sio-twin:
	bash gate/twin_gate.sh

sio-foreign:
	bash gate/foreign_gate.sh

sio-fstar:
	bash gate/fstar_gate.sh

sio-inventory:
	bash gate/inventory_check.sh

# Gate completo do nucleo Sounio. Python NAO participa (nem calculo, nem veredito).
sio-test: sio-check sio-run sio-twin sio-foreign sio-fstar sio-inventory
	@echo "SIO_TEST_OK: souc check + testes .sio + gemeo + F#/Futhark + F* + inventario"

# Relatorio apenas: nunca e hard-fail.
corroborate: sio-twin
	-PYTHONPATH=src $(PYTHON) tests/corroboration/run.py

bench: sio-twin
	bash gate/bench.sh

lean-single:
	bash gate/lean_single.sh
