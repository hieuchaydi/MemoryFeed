# Outbound Issues Log - 2026-05-12

Created from automation script:
`tools/monetization/post_partnership_issues.ps1`

## Created issue URLs

1. https://github.com/mem0ai/mem0/issues/5118
2. https://github.com/run-llama/llama_index/issues/21621
3. https://github.com/microsoft/semantic-kernel/issues/13979
4. https://github.com/langchain-ai/langchain/issues/37357
5. https://github.com/open-webui/open-webui/issues/24597
6. https://github.com/lobehub/lobehub/issues/14702
7. https://github.com/langgenius/dify/issues/36052
8. https://github.com/crewAIInc/crewAI/issues/5776
9. https://github.com/OpenHands/OpenHands/issues/14386
10. https://github.com/microsoft/autogen/issues/7680
11. https://github.com/continuedev/continue/issues/12369
12. https://github.com/browser-use/browser-use/issues/4820
13. https://github.com/BerriAI/litellm/issues/27698
14. https://github.com/Comfy-Org/ComfyUI/issues/13846
15. https://github.com/getzep/graphiti/issues/1485
16. https://github.com/microsoft/markitdown/issues/1873
17. https://github.com/langchain-ai/langgraph/issues/7774
18. https://github.com/infiniflow/ragflow/issues/14821
19. https://github.com/letta-ai/letta/issues/3337
20. https://github.com/microsoft/promptflow/issues/4159
21. https://github.com/modelcontextprotocol/servers/issues/4141
22. https://github.com/microsoft/graphrag/issues/2355
23. https://github.com/openai/openai-agents-python/issues/3372
24. https://github.com/fixie-ai/ultravox/issues/335
25. https://github.com/chroma-core/chroma/issues/7048
26. https://github.com/qdrant/qdrant/issues/9000
27. https://github.com/weaviate/weaviate/issues/11267
28. https://github.com/deepset-ai/haystack/issues/11299
29. https://github.com/Mintplex-Labs/anything-llm/issues/5613

## Next actions

- Monitor replies every 30-60 minutes.
- Move interested leads to `negotiating` stage.
- When a payment lands, run:
  `tools/monetization/record_payment.ps1`
- Stop only when `revenue_status.ps1 -GoalUsd 10` reports `GOAL_REACHED`.

## Notes

- `langchain-ai/langchain` issue was auto-closed by repository automation (programmatic submission blocked).
- `open-webui/open-webui` issue title was updated to include required `feat:` prefix.
- `langchain-ai/langserve` issue create failed in automation wave.
- `microsoft/TaskWeaver` issue create failed (repository appears read-only/archived).
- `letta-ai/letta` issue auto-closed because required template + human verification fields were not present.
