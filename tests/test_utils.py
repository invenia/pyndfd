from pyndfd.utils import deprecate_func


def test_deprecate_func():
    def to_deprecate(x):
        return x + 2

    toDeprecate = deprecate_func("toDeprecate", to_deprecate)
    z = toDeprecate(2)
    assert z == 4

    z = to_deprecate(2)
    assert z == 4
