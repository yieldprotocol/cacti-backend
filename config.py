import registry

config = dict(
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
        if 'type' in _cfg:
            _type = _cfg.pop('type')
            _cls = registry.get_class(_type)
            return _cls(**_cfg)
        return _cfg

    return cfg


def initialized_system():
    return initialize(config)
