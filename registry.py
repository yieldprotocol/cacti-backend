_registry = {}


def register_class(cls):
    global _registry
    key = f'{cls.__module__}.{cls.__name__}'
    assert key not in _registry, f'duplicate key: {key}'
    _registry[key] = cls
    print(f'Added to class registry: {key}')
    return cls


def get_class(name):
    global _registry
    assert name in _registry, f'could not find registered class with name: {name}'
    return _registry[name]
