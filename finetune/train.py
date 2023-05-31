import os
import openai

openai.api_key = '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'


# curl -H "Authorization: Bearer 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"  https://api.openai.com/v1/files

def run():
    filename = "file-y3kX4FYGd8BQpzoRQgHihHgd"
    filename = "file-ZrBtRlLgiusUmrCgSxeow68Q"
    filename = 'file-Hp0kOsfJKeYTUhUDbI6CCx5Y'
    filename = 'file-H2wJvdLpeaDomXBL7OCH7fmF'
    resp = openai.FineTune.create(
        model='davinci',
        suffix='task_info',
        training_file=filename,
    )
    print(resp)


def ls():
    resp = openai.FineTune.list()
    print(resp)


if __name__ == "__main__":
    # run()
    ls()
