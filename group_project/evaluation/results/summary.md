# Evaluation summary

## Run information

- evaluation_date: `2026-09-20`
- framework: `ragas 0.4.3`
- evaluator_model: `gpt-4o-mini (+ text-embedding-3-small for answer_relevancy)`
- generator_model: `openai/gpt-4o-mini`
- embedding_model: `BAAI/bge-m3`
- corpus_commit: `0fb3190`
- golden_dataset_size: `20`
- top_k: `5`
- score_threshold: `0.53`

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| faithfulness | 0.6833 | 0.7000 | +0.0167 |
| answer_relevancy | 0.6128 | 0.5802 | -0.0326 |
| context_recall | 0.7881 | 0.8476 | +0.0595 |
| context_precision | 0.7767 | 0.6160 | -0.1607 |
| **Average** | 0.7152 | 0.6860 | -0.0292 |

## Latency and refusals

| Config | Refusals | PageIndex fallback | Retrieval ms | Generation ms |
| --- | ---: | ---: | ---: | ---: |
| A (dense-only) | 5/20 | 0 | 867.7350 | 1425.8800 |
| B (hybrid + RRF) | 6/20 | 0 | 113.4450 | 1342.4800 |

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
