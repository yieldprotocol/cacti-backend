"""
This script will check if all widgets in the file and index have corresponding textual translation.
More info in README 'Steps to add new widget command'
"""

import re
from chat.display_widgets import parse_widgets_into_text
from index.widgets import backfill, get_client as weviate_get_client, TEXT_KEY
from utils import get_widget_index_name
from utils.common import WIDGETS


BATCH_SIZE = 20
CLASS_PROPERTIES = [TEXT_KEY]

RE_WIDGET_COMMAND = re.compile(r"<\|.*?\|>")
RE_PARAMS = re.compile(r"\{.*?\}")

def get_batch_with_offset(client, class_name, class_properties, batch_size, offset):
    query = client.query.get(class_name, class_properties).with_offset(offset).with_limit(batch_size)
    return query.do()

def read_widgets_from_index():
    index_name = get_widget_index_name()
    all_content = []
    offset = 0

    while True:
        results = get_batch_with_offset(weviate_get_client(), index_name, CLASS_PROPERTIES, BATCH_SIZE, offset)

        if len(results["data"]["Get"][index_name]) == 0:
            break

        for r in results["data"]["Get"][index_name]:
            all_content.append(r[TEXT_KEY])

        offset += BATCH_SIZE
    return all_content

def check_widgets_for_textual_translation(widgets, is_from_index):
    for w in widgets:
        matches = RE_WIDGET_COMMAND.findall(w)
        widget_command = matches[0]
        if 'display-' in widget_command:
            filled_widget_command = RE_PARAMS.sub('NA', widget_command)
            text = parse_widgets_into_text(filled_widget_command)
            error_type = 'Widget Index Error' if is_from_index else 'Widget File Error'
            if 'An unrecognized command' in text:
                raise Exception(f"{error_type}: textual translation missing in _widgetize_inner function in display_widget.py file for command: {widget_command}")  

def main():
    widgets_from_index = read_widgets_from_index()
    widgets_from_file = WIDGETS.split('---')

    check_widgets_for_textual_translation(widgets_from_index, True)
    check_widgets_for_textual_translation(widgets_from_file, False)


if __name__ == '__main__':
    main()
