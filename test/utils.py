
def parametrized(arg_list, values):
    def parametrized(fn):
        def parametrized(*args, **kwargs):
            __name__ = fn.__name__
            for value_set in values:
                arg = dict(zip(arg_list, value_set))
                fn(*args, **arg)
        return parametrized
    return parametrized