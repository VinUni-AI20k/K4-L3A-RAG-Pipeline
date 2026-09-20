# Evaluation summary

## Run information

- evaluation_date: `2026-09-20`
- framework: `ragas 0.4.3`
- evaluator_model: `gpt-4o-mini (+ text-embedding-3-small for answer_relevancy)`
- generator_model: `openai/gpt-4o-mini`
- embedding_model: `BAAI/bge-m3`
- corpus_commit: `dd89acd`
- golden_dataset_size: `20`
- top_k: `5`
- score_threshold: `0.53`

## Overall scores

| Metric | Config A | Config B | Config C | Config D | Delta B−A | Delta C−A | Delta D−A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| faithfulness | 0.6833 | 0.7000 | 0.7536 | 0.8333 | +0.0167 | +0.0703 | +0.1500 |
| answer_relevancy | 0.6128 | 0.5802 | 0.6352 | 0.7506 | -0.0326 | +0.0224 | +0.1378 |
| context_recall | 0.7881 | 0.8476 | 0.8393 | 0.9101 | +0.0595 | +0.0512 | +0.1220 |
| context_precision | 0.7767 | 0.6160 | 0.8675 | 0.9049 | -0.1607 | +0.0908 | +0.1282 |
| **Average** | 0.7152 | 0.6860 | 0.7739 | 0.8497 | -0.0292 | +0.0587 | +0.1345 |

## Latency and refusals

| Config | Refusals | PageIndex fallback | Retrieval ms | Generation ms |
| --- | ---: | ---: | ---: | ---: |
| A (dense-only) | 5/20 | 0 | 867.7350 | 1425.8800 |
| B (hybrid + RRF) | 6/20 | 0 | 113.4450 | 1342.4800 |
| C (hybrid + RRF + rerank) | 4/20 | 0 | 5890.1950 | 1550.7950 |
| D (C + HyDE) | 2/20 | 0 | 7270.5650 | 1358.3600 |

## Per-question scores

| # | Config | Faithfulness | Relevance | Recall | Precision | Refusal | Question |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| g01 | A | 0.0000 | 1.0000 | 1.0000 | 0.8667 |  | What are the four criteria used to assess IELTS Writing Task 1? |
| g02 | A | 0.6667 | 0.9780 | 1.0000 | 1.0000 |  | What is the difference between the criteria for Task 1 and Task 2 in IELTS Writing? |
| g03 | A | 1.0000 | 0.8609 | 0.7500 | 1.0000 |  | Does Task 2 carry more weight than Task 1 in the IELTS Writing score? |
| g04 | A | 1.0000 | 0.7184 | 1.0000 | 1.0000 |  | Bài IELTS Writing Task 2 cần viết tối thiểu bao nhiêu từ? |
| g05 | A | 1.0000 | 0.9741 | 1.0000 | 1.0000 |  | How many words must I write for IELTS Writing Task 1? |
| g06 | A | 1.0000 | 0.6354 | 0.6667 | 1.0000 |  | Nên phân bổ thời gian như thế nào giữa Task 1 và Task 2 trong bài thi Writing? |
| g07 | A | 0.0000 | 0.0000 | 0.0000 | 0.3250 | yes | What does Band 7 require for Lexical Resource in Writing Task 2? |
| g08 | A | 1.0000 | 0.9552 | 1.0000 | 1.0000 |  | Describe the Task Response descriptor for Band 9 in Writing Task 2. |
| g09 | A | 0.0000 | 0.0000 | 0.6667 | 0.3667 | yes | Tiêu chí Coherence and Cohesion ở Band 6 của Writing Task 1 yêu cầu gì? |
| g10 | A | 0.0000 | 0.0000 | 0.2500 | 1.0000 | yes | What characterises Grammatical Range and Accuracy at Band 5 in Writing Task 2? |
| g11 | A | 1.0000 | 0.9100 | 1.0000 | 0.9500 |  | In Writing Task 1 at Band 8, what does Task Achievement require for the Academic test? |
| g12 | A | 1.0000 | 0.4260 | 1.0000 | 0.8875 |  | Bài viết Task 2 có 20 từ trở xuống sẽ được chấm band mấy? |
| g13 | A | 0.0000 | 0.0000 | 1.0000 | 0.0000 | yes | Compare Lexical Resource at Band 8 and Band 9 for Writing Task 1. |
| g14 | A | 1.0000 | 0.9826 | 1.0000 | 1.0000 |  | What does the Band 4 Task Achievement descriptor say about General Training letters? |
| g15 | A | 1.0000 | 0.7712 | 0.0000 | 1.0000 |  | Tiêu chí Task Response đánh giá những gì trong Writing Task 2? |
| g16 | A | 0.0000 | 0.0000 | 1.0000 | 0.0000 | yes | Can I use bullet points in my IELTS Writing answer? |
| g17 | A | 1.0000 | 0.9667 | 1.0000 | 0.8333 |  | What kind of task is Academic Writing Task 1? |
| g18 | A | 1.0000 | 0.5424 | 1.0000 | 0.8042 |  | Điểm Writing tổng được tính như thế nào từ bốn tiêu chí? |
| g19 | A | 1.0000 | 0.9667 | 0.4286 | 0.5000 |  | What are common mistakes candidates make in IELTS Writing Task 2? |
| g20 | A | 1.0000 | 0.5686 | 1.0000 | 1.0000 |  | Tại sao trả lời không đầy đủ câu hỏi lại làm giảm điểm Task 2? |
| g01 | B | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  | What are the four criteria used to assess IELTS Writing Task 1? |
| g02 | B | 1.0000 | 0.8628 | 1.0000 | 0.7000 |  | What is the difference between the criteria for Task 1 and Task 2 in IELTS Writing? |
| g03 | B | 1.0000 | 0.8398 | 0.7500 | 0.9500 |  | Does Task 2 carry more weight than Task 1 in the IELTS Writing score? |
| g04 | B | 1.0000 | 0.7184 | 1.0000 | 0.8667 |  | Bài IELTS Writing Task 2 cần viết tối thiểu bao nhiêu từ? |
| g05 | B | 1.0000 | 0.9741 | 1.0000 | 0.7000 |  | How many words must I write for IELTS Writing Task 1? |
| g06 | B | 1.0000 | 0.6088 | 1.0000 | 1.0000 |  | Nên phân bổ thời gian như thế nào giữa Task 1 và Task 2 trong bài thi Writing? |
| g07 | B | 0.0000 | 0.0000 | 0.7500 | 0.3333 | yes | What does Band 7 require for Lexical Resource in Writing Task 2? |
| g08 | B | 1.0000 | 0.9552 | 1.0000 | 0.5000 |  | Describe the Task Response descriptor for Band 9 in Writing Task 2. |
| g09 | B | 0.0000 | 0.0000 | 0.6667 | 0.5000 | yes | Tiêu chí Coherence and Cohesion ở Band 6 của Writing Task 1 yêu cầu gì? |
| g10 | B | 0.0000 | 0.0000 | 0.7500 | 0.7000 | yes | What characterises Grammatical Range and Accuracy at Band 5 in Writing Task 2? |
| g11 | B | 1.0000 | 0.9106 | 1.0000 | 0.8875 |  | In Writing Task 1 at Band 8, what does Task Achievement require for the Academic test? |
| g12 | B | 1.0000 | 0.4260 | 1.0000 | 0.8042 |  | Bài viết Task 2 có 20 từ trở xuống sẽ được chấm band mấy? |
| g13 | B | 0.0000 | 0.0000 | 0.0000 | 0.0000 | yes | Compare Lexical Resource at Band 8 and Band 9 for Writing Task 1. |
| g14 | B | 1.0000 | 0.9826 | 1.0000 | 0.7556 |  | What does the Band 4 Task Achievement descriptor say about General Training letters? |
| g15 | B | 1.0000 | 0.7712 | 0.7500 | 1.0000 |  | Tiêu chí Task Response đánh giá những gì trong Writing Task 2? |
| g16 | B | 0.0000 | 0.0000 | 1.0000 | 0.0000 | yes | Can I use bullet points in my IELTS Writing answer? |
| g17 | B | 1.0000 | 0.9667 | 1.0000 | 0.3333 |  | What kind of task is Academic Writing Task 1? |
| g18 | B | 0.0000 | 0.0000 | 1.0000 | 0.3333 | yes | Điểm Writing tổng được tính như thế nào từ bốn tiêu chí? |
| g19 | B | 1.0000 | 1.0000 | 0.2857 | 0.2000 |  | What are common mistakes candidates make in IELTS Writing Task 2? |
| g20 | B | 1.0000 | 0.5874 | 1.0000 | 0.7556 |  | Tại sao trả lời không đầy đủ câu hỏi lại làm giảm điểm Task 2? |
| g01 | C | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  | What are the four criteria used to assess IELTS Writing Task 1? |
| g02 | C | 1.0000 | 0.9776 | 1.0000 | 0.9167 |  | What is the difference between the criteria for Task 1 and Task 2 in IELTS Writing? |
| g03 | C | 1.0000 | 0.8853 | 0.7500 | 1.0000 |  | Does Task 2 carry more weight than Task 1 in the IELTS Writing score? |
| g04 | C | 1.0000 | 0.7184 | 1.0000 | 1.0000 |  | Bài IELTS Writing Task 2 cần viết tối thiểu bao nhiêu từ? |
| g05 | C | 1.0000 | 0.9741 | 1.0000 | 1.0000 |  | How many words must I write for IELTS Writing Task 1? |
| g06 | C | 1.0000 | 0.6354 | 1.0000 | 1.0000 |  | Nên phân bổ thời gian như thế nào giữa Task 1 và Task 2 trong bài thi Writing? |
| g07 | C | 0.0000 | 0.0000 | 0.7500 | 0.2000 | yes | What does Band 7 require for Lexical Resource in Writing Task 2? |
| g08 | C | 1.0000 | 0.4525 | 1.0000 | 1.0000 |  | Describe the Task Response descriptor for Band 9 in Writing Task 2. |
| g09 | C | 0.0000 | 0.0000 | 1.0000 | 0.8056 | yes | Tiêu chí Coherence and Cohesion ở Band 6 của Writing Task 1 yêu cầu gì? |
| g10 | C | 0.0000 | 0.0000 | 0.0000 | 0.4778 | yes | What characterises Grammatical Range and Accuracy at Band 5 in Writing Task 2? |
| g11 | C | 1.0000 | 0.9106 | 1.0000 | 1.0000 |  | In Writing Task 1 at Band 8, what does Task Achievement require for the Academic test? |
| g12 | C | 0.5000 | 0.4227 | 1.0000 | 0.9500 |  | Bài viết Task 2 có 20 từ trở xuống sẽ được chấm band mấy? |
| g13 | C | 0.0000 | 0.0000 | 1.0000 | 0.0000 | yes | Compare Lexical Resource at Band 8 and Band 9 for Writing Task 1. |
| g14 | C | 1.0000 | 0.9826 | 1.0000 | 1.0000 |  | What does the Band 4 Task Achievement descriptor say about General Training letters? |
| g15 | C | 1.0000 | 0.7712 | 0.0000 | 1.0000 |  | Tiêu chí Task Response đánh giá những gì trong Writing Task 2? |
| g16 | C | 1.0000 | 0.9464 | 1.0000 | 1.0000 |  | Can I use bullet points in my IELTS Writing answer? |
| g17 | C | 1.0000 | 0.9667 | 1.0000 | 1.0000 |  | What kind of task is Academic Writing Task 1? |
| g18 | C | 1.0000 | 0.4879 | 1.0000 | 1.0000 |  | Điểm Writing tổng được tính như thế nào từ bốn tiêu chí? |
| g19 | C | 0.5714 | 0.9952 | 0.2857 | 1.0000 |  | What are common mistakes candidates make in IELTS Writing Task 2? |
| g20 | C | 1.0000 | 0.5780 | 1.0000 | 1.0000 |  | Tại sao trả lời không đầy đủ câu hỏi lại làm giảm điểm Task 2? |
| g01 | D | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  | What are the four criteria used to assess IELTS Writing Task 1? |
| g02 | D | 0.6667 | 0.9294 | 1.0000 | 1.0000 |  | What is the difference between the criteria for Task 1 and Task 2 in IELTS Writing? |
| g03 | D | 1.0000 | 0.8853 | 0.7500 | 1.0000 |  | Does Task 2 carry more weight than Task 1 in the IELTS Writing score? |
| g04 | D | 1.0000 | 0.7184 | 1.0000 | 1.0000 |  | Bài IELTS Writing Task 2 cần viết tối thiểu bao nhiêu từ? |
| g05 | D | 1.0000 | 0.9741 | 1.0000 | 1.0000 |  | How many words must I write for IELTS Writing Task 1? |
| g06 | D | 1.0000 | 0.5788 | 1.0000 | 1.0000 |  | Nên phân bổ thời gian như thế nào giữa Task 1 và Task 2 trong bài thi Writing? |
| g07 | D | 0.0000 | 0.0000 | 1.0000 | 0.3250 | yes | What does Band 7 require for Lexical Resource in Writing Task 2? |
| g08 | D | 1.0000 | 0.9552 | 1.0000 | 0.8333 |  | Describe the Task Response descriptor for Band 9 in Writing Task 2. |
| g09 | D | 0.0000 | 0.0000 | 0.6667 | 0.7000 | yes | Tiêu chí Coherence and Cohesion ở Band 6 của Writing Task 1 yêu cầu gì? |
| g10 | D | 0.0000 | 0.9859 | 0.5000 | 0.7556 |  | What characterises Grammatical Range and Accuracy at Band 5 in Writing Task 2? |
| g11 | D | 1.0000 | 0.9237 | 1.0000 | 0.8333 |  | In Writing Task 1 at Band 8, what does Task Achievement require for the Academic test? |
| g12 | D | 1.0000 | 0.4227 | 1.0000 | 0.9500 |  | Bài viết Task 2 có 20 từ trở xuống sẽ được chấm band mấy? |
| g13 | D | 1.0000 | 0.8907 | 1.0000 | 0.7000 |  | Compare Lexical Resource at Band 8 and Band 9 for Writing Task 1. |
| g14 | D | 1.0000 | 0.9855 | 1.0000 | 1.0000 |  | What does the Band 4 Task Achievement descriptor say about General Training letters? |
| g15 | D | 1.0000 | 0.7712 | 1.0000 | 1.0000 |  | Tiêu chí Task Response đánh giá những gì trong Writing Task 2? |
| g16 | D | 1.0000 | 0.9202 | 1.0000 | 1.0000 |  | Can I use bullet points in my IELTS Writing answer? |
| g17 | D | 1.0000 | 0.9553 | 1.0000 | 1.0000 |  | What kind of task is Academic Writing Task 1? |
| g18 | D | 1.0000 | 0.5424 | 1.0000 | 1.0000 |  | Điểm Writing tổng được tính như thế nào từ bốn tiêu chí? |
| g19 | D | 1.0000 | 0.9952 | 0.2857 | 1.0000 |  | What are common mistakes candidates make in IELTS Writing Task 2? |
| g20 | D | 1.0000 | 0.5789 | 1.0000 | 1.0000 |  | Tại sao trả lời không đầy đủ câu hỏi lại làm giảm điểm Task 2? |
