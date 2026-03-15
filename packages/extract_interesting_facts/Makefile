check:
	uv run python -c "from pathlib import Path; spec = Path('docs/module-spec.md'); assert spec.is_file(), 'docs/module-spec.md is required'; text = spec.read_text(encoding='utf-8'); assert 'Module Spec: extract_interesting_facts' in text, 'spec header is missing'"
