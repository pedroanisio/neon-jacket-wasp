PYTHON := .venv/bin/python
SCHEMA := schema/silhouette_v4.schema.json
MODEL  := lib/model.py

.PHONY: schema lint format typecheck check

schema: $(SCHEMA)

$(SCHEMA): $(MODEL)
	@PYTHONPATH=. $(PYTHON) -c "\
	import json; from lib.model import SilhouetteV4; from pathlib import Path; \
	s = SilhouetteV4.model_json_schema(by_alias=True); \
	s['\$$comment'] = 'GENERATED FILE — do not edit. Source of truth: lib/model.py. Regenerate: make schema'; \
	Path('$(SCHEMA)').write_text(json.dumps(s, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')"
	@echo "Generated $(SCHEMA)"

lint:
	$(PYTHON) -m ruff check lib/

format:
	$(PYTHON) -m ruff format lib/

typecheck:
	$(PYTHON) -m mypy lib/

check: lint typecheck
