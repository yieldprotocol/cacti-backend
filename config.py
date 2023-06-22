import registry

# start everything from this page
#  5 types of indexes used for info/doc retrieval and question - answering
widget_index = dict(
    type="index.weaviate.WeaviateIndex",
    index_name="WidgetV12",
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

# config is mirroring a json
default_config = dict(
    type="system.System",
    # chat=dict(
    #     type="chat.basic_agent.BasicAgentChat", # type of chat agent
    #     tools=[
    #         dict(
    #             type="tools.index_widget.IndexWidgetTool",
    #             _streaming=True,  # if specified, this is lazily constructed in chat to support streaming
    #             name="WidgetIndexAnswer",
    #             index=widget_index,
    #             top_k=10,
    #         ),
    #     ],
    #     model_name = "huggingface-llm"
    # )
    chat=dict(
        type='chat.rephrase_widget_search2.RephraseWidgetSearchChat',
        widget_index=widget_index,
        top_k=4,
        model_name = "huggingface-llm",
        evaluate_widgets=True
    )
)


def initialize(cfg): # initialize the config of the chat model
    if isinstance(cfg, dict):
        # recursively initialize objects
        _cfg = {k: initialize(v) for k, v in cfg.items()}
        if 'type' in _cfg and not _cfg.get('_streaming'):
            _type = _cfg.pop('type')
            _cls = registry.get_class(_type) # registry maps the type to a class name
            print(f'Initializing instance of type: {_type}')
            return _cls(**_cfg)
        return _cfg
    elif isinstance(cfg, list):
        # recursively initialize items in list
        _cfg = [initialize(v) for v in cfg]
        return _cfg

    return cfg


def initialize_streaming(cfg, new_token_handler): # dedicated to streaming service
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