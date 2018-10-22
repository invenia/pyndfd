import warnings


def deprecate_func(old_name, new_function):
    def df(*args, **kwargs):
        warnings.warn(
            "'{}' is not a Pep8 compliant function name, use '{}' instead".format(
                old_name, new_function.__name__
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return new_function(*args, **kwargs)

    return df
