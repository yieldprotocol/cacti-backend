# Chat System Evaluation Guide
This documentation provides information on how to evaluate the Cacti chat system. The system uses widget commands, which are functions designed to answer specific user questions. 

\
**Note**: 
- Before starting the evaluation, you must provide the system *chat config* you want to evaluate. Pls specify your desired chat config [here](https://github.com/yieldprotocol/cacti-backend/blob/a495d32d1263d0950d8c3271f21b6768bf546c5a/finetune/validate.py#L605).
- As the eval gets completed the input-output pairs with the chat prediction will be saved in a CSV file. 

\
There are 3 techniques used for evaluation:

## 1. Hardcoded Evaluation
This technique uses hardcoded input-output pairs covering all existing widget commands the system supports.

### Adding New Widget Commands
If you wish to evaluate new widget commands added to the chat knowledge base, you'll need to hardcode the test samples (input-output pairs) as demonstrated in this [flow](https://github.com/yieldprotocol/cacti-backend/blob/a495d32d1263d0950d8c3271f21b6768bf546c5a/finetune/validate.py#L213).

### Running Hardcoded Evaluation
To run the hardcoded evaluation, use the following command:

```sh
python -m eval.validate --eval_type 1
```


## 2. Automated Evaluation
This method employs an AI agent (GPT-4) to frame the input-output pairs for evaluating the Cacti chat system. From creating the test samples to performing the valuation, this pipeline is fully automated.

### Specifying Widget Commands
If you prefer to conduct the evaluation on a specific set of widget commands, pls specify them in the `finetune/eval_widgets.txt` file. 

### Running Automated Evaluation
Run the automated evaluation using the following command:

```sh
python -m eval.validate --eval_type 2 --num_widgets 5
```

`--num_widgets` denotes the number of widget commands to use at once to produce a sequence of input-output test pairs. 


## 3. Human Annotated Evaluation Samples
For this evaluation type, you can use a set of human annotated samples.

### Creating Test Evaluation Samples
This evaluation requires a CSV file containing the input-output pairs for the Cacti chat system to be tested. Please follow the sample CSV file format provided [here](https://github.com/yieldprotocol/cacti-backend/blob/dev/eval/example_test_file.csv). When creating your custom test file, ensure to use the same column names as those in the sample CSV file.

### Running Evaluation on Human Annotated Samples
To run the evaluation using your custom test file, use the following command:

```sh
python -m eval.validate --eval_type 3 --test_file <your_test_file.csv>
``` 