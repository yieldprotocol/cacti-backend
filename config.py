import registry

default_config = dict(
    type="system.System",
    chat=dict(
        type="chat.widget_search.WidgetSearchChat",
        doc_index=dict(
            type="index.weaviate.WeaviateIndex",
            index_name="IndexV1",
            text_key="content",
            extra_keys=["url"],
        ),
        widget_index=dict(
            type="index.weaviate.WeaviateIndex",
            index_name="WidgetV1",
            text_key="content",
        ),
        show_thinking=True,
    ),
)


def initialize(cfg):
    if isinstance(cfg, dict):
        # recursively initialize objects
        _cfg = {k: initialize(v) for k, v in cfg.items()}
        if 'type' in _cfg and not _cfg.get('_streaming'):
            _type = _cfg.pop('type')
            _cls = registry.get_class(_type)
            print(f'Initializing instance of type: {_type}')
            return _cls(**_cfg)
        return _cfg
    elif isinstance(cfg, list):
        # recursively initialize items in list
        _cfg = [initialize(v) for v in cfg]
        return _cfg

    return cfg


def initialize_streaming(cfg, new_token_handler):
    if isinstance(cfg, dict):
        # recursively initialize objects
        _cfg = {k: initialize_streaming(v, new_token_handler) for k, v in cfg.items()}
        if 'type' in _cfg and _cfg.get('_streaming'):
            _type = _cfg.pop('type')
            _cls = registry.get_class(_type)
            print(f'Initializing instance of type: {_type}')
            return _cls(new_token_handler=new_token_handler, **_cfg)
        return _cfg
    elif isinstance(cfg, list):
        # recursively initialize items in list
        _cfg = [initialize_streaming(v, new_token_handler) for v in cfg]
        return _cfg

    return cfg



def initialize_system(config):
    return initialize(config)
