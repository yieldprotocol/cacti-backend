import registry


widget_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="WidgetV11",
    text_key="content",
)
app_info_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="AppInfoV1",
    text_key="question",
    extra_keys=["answer", "suggested_follow_ups"],
)
scraped_sites_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="IndexV1",
    text_key="content",
    extra_keys=["url"],
)
api_docs_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="APIDocsV1",
    text_key="description",
    extra_keys=["spec"],
)

crypto_tokens_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="CryptoTokensV1",
    text_key="canonical_id",
    extra_keys=["name", "symbol"],
)


default_config = dict(
    type="system.System",
    chat=dict(
        type="chat.basic_agent.BasicAgentChat",
        tools=[
            dict(
                type="tools.index_widget.IndexWidgetTool",
                _streaming=True,  # if specified, this is lazily constructed in chat to support streaming
                name="WidgetIndexAnswer",
                index=widget_index,
                top_k=10,
            ),
        ],
    )
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