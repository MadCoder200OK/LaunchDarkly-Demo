"""Keep the visual guide's source ranges and allowed links reliable."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = runpy.run_path(str(ROOT / 'scripts/update_readme.py'))


def test_readme_ranges_assets_and_links_are_current():
    source = (ROOT / 'README.md').read_text()
    blocks = DOCS['code_blocks'](ROOT)
    assert len(blocks) >= 30  # The complete feature index must not silently disappear.
    assert source == DOCS['refresh'](source, blocks)
    DOCS['validate_links'](source, ROOT)
    code_map = (ROOT / 'docs/code-map.md').read_text()
    assert code_map == DOCS['implementation_map'](blocks)
    DOCS['validate_links'](code_map, ROOT / 'docs')


def test_marker_parser_rejects_mismatched_boundaries(tmp_path):
    (tmp_path / 'dev.py').write_text('# DEMO START setup: Prepare the app.\npass\n# DEMO END other\n')
    with pytest.raises(ValueError, match='Unbalanced code marker'):
        DOCS['code_blocks'](tmp_path)


def test_readme_rejects_missing_assets_and_non_launchdarkly_links(tmp_path):
    for source in ['![missing](missing.jpg)', '[Other](https://example.com)',
                   '[Not docs](https://launchdarkly.com/pricing)']:
        with pytest.raises(ValueError):
            DOCS['validate_links'](source, tmp_path)
    DOCS['validate_links']('[Flag docs](https://launchdarkly.com/docs/home/flags/new)', tmp_path)
