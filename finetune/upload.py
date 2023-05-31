import os
import openai
openai.api_key = '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'#os.getenv("OPENAI_API_KEY")


def run():
    resp = openai.File.create(
        file=open("full_dataset.jsonl", "r"),
        purpose='fine-tune'
    )
    print(resp)


if __name__ == "__main__":
    run()
