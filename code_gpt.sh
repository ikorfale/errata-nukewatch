#!/bin/bash
# second blind coder (other model family): one update per call, same instructions as data/blind_prompt_r2.txt
cd "$(dirname "$0")"
for n in $(seq 355 375); do
  o=data/coder_gpt/u$n.json; [ -s $o ] && continue
  q="$(sed -n '3,$p' data/blind_prompt_r2.txt | sed 's/for all 12/for this one update/; s/For EACH update/For this update/')
Use the key \"$n\".

UPDATE $n TEXT:
$(cat data/txt/u$n.txt)"
  "${OA:-oa}" ask "$q" --model gpt-5 > $o 2>>data/coder_gpt/err.log
  echo "$n rc=$?" >> data/coder_gpt/progress.log
done
echo done >> data/coder_gpt/progress.log
