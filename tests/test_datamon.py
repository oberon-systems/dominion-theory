from pathlib import Path

from datamon import ROOT, changed, digest, relative, selected


def test_data_of_the_repository_is_kept_and_code_hidden_folders_and_runs_are_not() -> None:
    assert relative(ROOT / 'src' / 'alpha.yaml') == 'src/alpha.yaml'
    assert relative(str(ROOT / 'docs')) == 'docs'
    assert relative(ROOT / 'src' / 'alpha.py') is None
    assert relative(ROOT / '.venv' / 'alpha.yaml') is None
    assert relative(ROOT / 'lives' / 'alpha' / 'report.txt') is None
    assert relative(ROOT.parent / 'alpha.yaml') is None
    assert relative(3) is None


def test_a_file_is_known_by_its_content_a_folder_by_its_names_and_a_gone_one_by_nothing(tmp_path: Path) -> None:
    (tmp_path / 'beta').mkdir()
    (tmp_path / 'beta' / 'alpha.yaml').write_text('a: 1\n')
    before = (digest('beta', tmp_path), digest('beta/alpha.yaml', tmp_path))

    (tmp_path / 'beta' / 'alpha.yaml').write_text('a: 2\n')
    assert digest('beta', tmp_path) == before[0]
    assert digest('beta/alpha.yaml', tmp_path) != before[1]
    (tmp_path / 'beta' / 'gamma.yaml').write_text('')
    assert digest('beta', tmp_path) != before[0]
    assert digest('delta', tmp_path) == ''


def test_a_module_runs_when_what_it_read_changed_or_it_has_no_record_yet(tmp_path: Path) -> None:
    (tmp_path / 'alpha.ftl').write_text('one')
    (tmp_path / 'beta.yaml').write_text('two')
    record = {
        'tests/a.py': {'alpha.ftl': digest('alpha.ftl', tmp_path)},
        'tests/b.py': {'beta.yaml': digest('beta.yaml', tmp_path)},
        'tests/c.py': {},
    }
    modules = ('tests/a.py', 'tests/b.py', 'tests/c.py', 'tests/d.py')

    assert selected(modules, record, tmp_path) == {'tests/d.py'}
    (tmp_path / 'alpha.ftl').write_text('three')
    assert changed(record, tmp_path) == {'tests/a.py'}
    assert selected(modules, record, tmp_path) == {'tests/a.py', 'tests/d.py'}
    assert selected(modules, None, tmp_path) == set(modules)
