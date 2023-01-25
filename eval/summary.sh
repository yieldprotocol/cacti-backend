#!/bin/bash

echo Variant1 Accuracy
ls qa_lido_eval_accuracy/*variant1*|xargs -I @ bash -c "cat @|jq .accuracy_responses"
echo Variant2 Accuracy
ls qa_lido_eval_accuracy/*variant2*|xargs -I @ bash -c "cat @|jq .accuracy_responses"


echo Variant1 Personality
ls qa_lido_eval_personality/*variant1*|xargs -I @ bash -c "cat @|jq .personality_responses"
echo Variant2 Personality
ls qa_lido_eval_personality/*variant2*|xargs -I @ bash -c "cat @|jq .personality_responses"
