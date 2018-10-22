from pyndfd.utils import deprecate_func


def test_deprecate_func():
    def to_deprecate(x):
        return x + 2

    # Ignore the pep8 error here as this function name is set as camel case to
    # specifically point out the reason we are deprecating functions with that type of
    # function name
    toDeprecate = deprecate_func("toDeprecate", to_deprecate)  # noqa: N806
    z = toDeprecate(2)
    assert z == 4

    z = to_deprecate(2)
    assert z == 4
