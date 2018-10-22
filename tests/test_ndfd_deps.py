from pyndfd.ndfd_defs import ndfd_defs


def test_ndfd_defs():
    defs = ndfd_defs()

    assert type(defs) == dict
    assert "vars" in defs
    assert "wx" in defs
    assert "wwa" in defs
    assert "grids" in defs
