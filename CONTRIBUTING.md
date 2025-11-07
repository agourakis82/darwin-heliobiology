# Contribuição — darwin-heliobiology

## Workflow
1. Abra issue descrevendo hipótese / feature.
2. Crie branch `feature/<issue-id>-descricao`.
3. Siga o manifesto (arquitetura sagrada, separação de domínios, testes).
4. Rode `poetry run black`, `ruff`, `mypy`, `pytest`.
5. Atualize `CHANGELOG.md`, docs e carimbo editorial.
6. Abra PR com template padrão (What/Why/Changes/Tests/Risks/Checklist).

## Padrões
- Python 3.11, Poetry.
- Testes ≥85% coverage.
- Docstrings com timestamps e contexto (ver README.exocortex).
- Nenhuma dependência proprietária; apenas dados públicos.

## Contato
Crie issue ou PR mencionando @agourakis82.
