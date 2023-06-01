# TODO(scott): clean up

import collections
import dataclasses
import datetime
import json
import re
import uuid

from gpt_index.utils import ErrorToRetry, retry_on_exceptions_with_backoff

import chat
import chat.display_widgets
from database.models import db_session, FeedbackStatus, ChatMessage, ChatMessageFeedback
import index

import finetune.widget_llm

HISTORY_TOKEN_LIMIT = 1800

NO_WIDGET_TOKEN = '<WIDGET_NA>'

# <|some-command(...)|> => some-command
WIDGET_COMMAND_PATTERN = r'\<\|([\w_-]+)\(.*\)\|\>'


def _extract_widget_command(s):
    m = re.search(WIDGET_COMMAND_PATTERN, s)
    if m is None:
        return None
    return m.group(1)


def get_widgets(user_input, index_name):
    # hard-coded parameters based on the state of rephrase_widget_search2
    widget_index = index.weaviate.WeaviateIndex(text_key='content', index_name=index_name)
    top_k = 18

    widgets = retry_on_exceptions_with_backoff(
        lambda: widget_index.similarity_search(user_input, k=top_k),
        [ErrorToRetry(TypeError)],
    )
    return widgets


def format_widgets_for_prompt(widgets):
    widget_contents = [
        WidgetContent.from_string(widget.page_content)
        for widget in widgets
    ]
    return format_widget_contents_for_prompt(widget_contents)


def format_widget_contents_for_prompt(widget_contents):
    return '\n'.join([
        f'Widget: {widget_content.command_template}'
        for widget_content in widget_contents
    ])


class WidgetContent:

    def __init__(self, command_template):
        self.command_template = command_template

    @classmethod
    def from_string(cls, s):
        # Widget magic command: <|fetch-transactions({address},{last_n})|>
        # Description of widget: This widget is used when we need the transaction details in an account or wallet
        # Required parameters:
        # -{address}: address of the account or wallet to check the transactions of
        # -{last_n}: how many latest transactions the user wants to get.
        # Return value description:
        # -the transaction details
        s = s.strip()

        # iteratively parse sections
        # TODO: generalize this to other sections other than Widget magic command
        command_template_prefix = 'Widget magic command:'
        section_prefixes = [
            command_template_prefix,
            'Description of widget:',
            'Required parameters:',
            'Parameters:',
            'Return value description:',
        ]

        start_index_by_prefix = {}
        for prefix in section_prefixes:
            start_index = s.find(prefix)
            if start_index == -1:
                continue
            start_index_by_prefix[prefix] = start_index

        start_index_prefixes = sorted([
            (start_index, prefix) for prefix, start_index in start_index_by_prefix.items()
        ])

        content_by_prefix = {}
        for i, (start_index, prefix) in enumerate(start_index_prefixes):
            if i == len(start_index_prefixes) - 1:
                end_index = len(s)
            else:
                end_index, _ = start_index_prefixes[i + 1]

            content = s[start_index + len(prefix):end_index].strip()
            content_by_prefix[prefix] = content

        command_template = content_by_prefix[command_template_prefix]
        return cls(command_template)


@dataclasses.dataclass
class Datapoint:
    user_input: str
    history: str
    completion: str
    task_info: str


def render_datapoint(datapoint):
    prompt = f'<hist>{datapoint.history}<user>{datapoint.user_input}<task>{datapoint.task_info}<bot>'
    completion = f'{datapoint.completion}<eot>'
    return {
        'prompt': prompt,
        'completion': completion,
    }


class Session:

    def __init__(self, session_id, messages):
        assert len(messages) % 2 == 0
        self.session_id = session_id
        self.messages = messages

    def _extract_response_from_output(self, llm_output):
        response_prefix = '## Response: <|'
        response_idx = llm_output.find(response_prefix)
        if response_idx == -1:
            return None
        return llm_output[response_idx + len(response_prefix) - len('<|'):]

    def iter_datapoints(self):
        chat_history = chat.base.ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        for i in range(0, len(self.messages), 2):
            user_message, _ = self.messages[i]
            bot_message, feedback = self.messages[i + 1]

            user_input = user_message.payload
            history_string = chat_history.to_string(token_limit=HISTORY_TOKEN_LIMIT)

            # iteratively construct history
            chat_history.add_interaction(user_input, bot_message.payload)

            if feedback == FeedbackStatus.bad:
                print('skipping bad feedback')
                continue

            index_name = 'WidgetV8'
            widgets = get_widgets(user_input, index_name)
            widget_contents = [WidgetContent.from_string(widget.page_content) for widget in widgets]

            # use old format for backfilling the LLM output
            replay_task_info = '\n'.join([f'Widget: {widget.page_content}' for widget in widgets])

            # use pruned format for fine-tuning
            datapoint_task_info = format_widget_contents_for_prompt(widget_contents)

            llm_output = finetune.widget_llm.get_llm_output(user_input, replay_task_info, history_string)
            if llm_output is None:
                # this happens if there's an InvalidRequestError (e.g. token limit)
                response = None
            else:
                # extract the response section of the LLM output
                response = self._extract_response_from_output(llm_output)

            if response is None:
                widget_command = None
            else:
                # extract the unparameterized widget command
                widget_command = _extract_widget_command(response)

            filtered_widget_contents = None
            if widget_command is not None:
                filtered_widget_contents = [
                    widget_content for widget_content in widget_contents
                    if _extract_widget_command(widget_content.command_template) != widget_command
                ]
                # the outputted widget command was not in the original list of widgets
                # this can happen due to a corrupted or hallucinated output
                # in this case, disregard the widget output and classify as NO_WIDGET
                if len(filtered_widget_contents) != len(widget_contents) - 1:
                    widget_command = None

            if widget_command is None:
                completion = NO_WIDGET_TOKEN
            else:
                completion = response

            datapoint = Datapoint(
                user_input=user_input,
                history=history_string,
                completion=completion,
                task_info=datapoint_task_info,
            )
            yield datapoint

            # contra datapoint - exclude the proper widget command from the
            # widget task info and mark as NO_WIDGET
            if widget_command is None:
                continue

            contra_datapoint_task_info = format_widget_contents_for_prompt(filtered_widget_contents)
            contra_datapoint = Datapoint(
                user_input=user_input,
                history=history_string,
                completion=NO_WIDGET_TOKEN,
                task_info=contra_datapoint_task_info,
            )
            yield contra_datapoint

    @classmethod
    def from_messages(cls, session_id, all_messages):
        messages = [
            (message, feedback) for message, feedback in all_messages
            if message.actor in ('user', 'bot')
        ]

        # validate message flow integrity: user, bot, user, bot, etc
        for i, (message, _) in enumerate(messages):
            if i % 2 == 0:
                expected_actor = 'user'
            else:
                expected_actor = 'bot'
            if message.actor != expected_actor:
                return None

        # exclude the last user message as it has no response
        if len(messages) % 2 == 1:
            messages = messages[:-1]

        return cls(session_id, messages)


def _should_exclude_message(message):
    created_cutoff_dt = datetime.datetime(2023, 5, 30)
    if message.created > created_cutoff_dt:
        return True
    return False


def get_sessions():
    all_messages = db_session.query(
        ChatMessage,
        ChatMessageFeedback.feedback_status,
    ).outerjoin(
        ChatMessageFeedback,
        ChatMessage.id == ChatMessageFeedback.chat_message_id,
    ).order_by(
        ChatMessage.sequence_number,
        ChatMessage.created
    ).all()

    messages_by_session = collections.defaultdict(list)
    for message, feedback in all_messages:
        if _should_exclude_message(message):
            continue
        messages_by_session[str(message.chat_session_id)].append((message, feedback))

    sessions = []
    num_bad = 0
    for session_id, messages in messages_by_session.items():
        session = Session.from_messages(session_id, messages)

        # session doesn't follow expected user -> bot -> user -> ... flow
        if session is None:
            num_bad += 1
        else:
            sessions.append(session)
    print('%d / %d bad sessions' % (num_bad, len(messages_by_session)))
    return sessions


def get_datapoints(sessions):
    datapoints = []
    for i, session in enumerate(sessions):
        if i % 10 == 0:
            print(f'session {i} / {len(sessions)}')

        for datapoint in session.iter_datapoints():
            datapoints.append(datapoint)

    return datapoints


def save_datapoints(datapoints, file_path):
    # TODO: use jsonl library
    with open(file_path, 'w') as f:
        for datapoint in datapoints:
            d = render_datapoint(datapoint)
            print(json.dumps(d), file=f)


def main():
    dataset_file_path = 'full_dataset.jsonl'
    sessions = get_sessions()
    datapoints = get_datapoints(sessions)

    print('%d datapoints' % len(datapoints))
    save_datapoints(datapoints, dataset_file_path)
    return datapoints

# datapoints = main()
