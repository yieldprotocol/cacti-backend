import os
import env
from index.widgets import backfill, get_client as weviate_get_client
from utils import get_widget_index_name

def main():
    print("Checking if widget index needs to be updated...")
    schema = weviate_get_client().schema.get()
    classes = schema['classes']
    saved_index_names = [c['class'] for c in classes]
    
    curr_index_name = get_widget_index_name()
    widget_index_exists = curr_index_name in saved_index_names

    if env.is_local():
        if widget_index_exists:
            backfill(delete_first=True)
        else:
            backfill(delete_first=False)
        print(f"Widget index updated, env: {env.get_env()}, index_name: {curr_index_name}")
    else:
        if not widget_index_exists:
            backfill(delete_first=False)
            print(f"Widget index updated, env: {env.get_env()}, index_name: {curr_index_name}")
        else:
            print(f"Widget index already exists, no update performed, env: {env.get_env()}, index_name: {curr_index_name}")


if __name__ == "__main__":          
    main()

