# Conversation memory demo

- Date: 2026-09-20T20:21:32
- Script: `python -m src.task13_conversation_memory`
- top_k: 5, history window: 6 turns

## Turn 1

- **User:** How many words must I write for IELTS Writing Task 2?
- **Standalone query (retrieval):** How many words must I write for IELTS Writing Task 2?
- **Retrieval source:** hybrid; top sources: `news/ieltsadvantage-writing-task-2.md::chunk-32`, `news/ielts-article-10-tips-improve-your-ielts-writing-band-score.md::chunk-6`, `news/ieltsadvantage-writing-task-2.md::chunk-1`
- **Assistant:** Bạn phải viết ít nhất 250 từ cho IELTS Writing Task 2 [news/ieltsadvantage-writing-task-2.md::chunk-48].

## Turn 2

- **User:** And for Task 1?
- **Standalone query (retrieval):** And for IELTS Writing Task 1, how many words must I write?
- **Retrieval source:** hybrid; top sources: `news/ielts-article-10-tips-improve-your-ielts-writing-band-score.md::chunk-3`, `legal/ielts-academic-writing-sample-tasks.md::chunk-0`, `legal/ielts-general-training-writing-sample-tasks.md::chunk-6`
- **Assistant:** Bạn phải viết ít nhất 150 từ cho IELTS Writing Task 1 [news/ielts-article-10-tips-improve-your-ielts-writing-band-score.md::chunk-3].

## Turn 3

- **User:** Which one carries more weight in the final score?
- **Standalone query (retrieval):** Which one, IELTS Writing Task 1 or Task 2, carries more weight in the final score?
- **Retrieval source:** hybrid; top sources: `legal/ielts-writing-key-assessment-criteria.md::chunk-0`, `legal/ielts-general-training-writing-sample-tasks.md::chunk-11`, `legal/ielts-academic-writing-sample-tasks.md::chunk-10`
- **Assistant:** Task 2 carries more weight in the final score than Task 1 [legal/ielts-writing-key-assessment-criteria.md::chunk-0].

