
import re

def _extract_knowledge_from_results(search_results: list[dict], query: str) -> dict:
    """
    Extracts relevant knowledge from a list of search results based on the original query.
    Filters out less relevant results and consolidates snippets.

    Args:
        search_results: A list of dictionaries, each containing 'title', 'snippet', and 'link'.
        query: The original search query, used to prioritize and filter relevant information.

    Returns:
        A dictionary containing extracted knowledge, including a consolidated summary and relevant links.
    """
    if not search_results:
        return {"summary": "No search results to process.", "relevant_links": []}

    relevant_snippets = []
    relevant_links = []
    query_terms = set(query.lower().split())

    for result in search_results:
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        link = result.get("link", "")

        # Heuristic for relevance: check if query terms are in title or snippet
        is_relevant = any(term in title or term in snippet for term in query_terms)

        if is_relevant:
            relevant_snippets.append(result.get("snippet", ""))
            if link and link not in relevant_links:
                relevant_links.append(link)

    # Consolidate relevant snippets into a single summary
    consolidated_summary = " ".join(relevant_snippets)

    # Basic deduplication and cleanup (more advanced NLP could be used here)
    sentences = re.split(r'(?<=[.!?]) +', consolidated_summary)
    unique_sentences = []
    for s in sentences:
        if s not in unique_sentences and s.strip():
            unique_sentences.append(s.strip())
    
    final_summary = " ".join(unique_sentences)
    
    if not final_summary:
        final_summary = "No relevant information could be extracted from the search results."

    return {"summary": final_summary, "relevant_links": relevant_links}
