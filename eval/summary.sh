#!/bin/bash

echo Variant1
ls qa_lido_eval_accuracy/*variant1*|xargs -I @ bash -c "cat @|jq .accuracy_responses"
echo Variant2
ls qa_lido_eval_accuracy/*variant2*|xargs -I @ bash -c "cat @|jq .accuracy_responses"
