# ClinicalTrials MCP Server

This is a Python implementation of the clincial trials MCP server, providing tools to search and retrieve clinical trial data from ClinicalTrials.gov.

## Tools

1.  `search_studies`: Search for clinical trials with various filters.
2.  `get_study_details`: Get detailed information about a specific clinical trial.
3.  `search_by_location`: Find clinical trials by geographic location.
4.  `search_by_condition`: Search for clinical trials focusing on specific medical conditions.
5.  `get_trial_statistics`: Get aggregate statistics about clinical trials.
6.  `search_by_sponsor`: Search clinical trials by sponsor or organization.
7.  `search_by_intervention`: Search clinical trials by intervention or treatment type.
8.  `get_recruiting_studies`: Get currently recruiting clinical trials.
9.  `search_by_date_range`: Search clinical trials by start or completion date range.
10. `get_studies_with_results`: Find completed clinical trials that have published results.
11. `search_rare_diseases`: Search clinical trials for rare diseases and orphan conditions.
12. `get_pediatric_studies`: Find clinical trials designed for children and adolescents.
13. `get_similar_studies`: Find clinical trials similar to a specific study.
14. `search_by_primary_outcome`: Search clinical trials by primary outcome measures.
15. `search_by_eligibility_criteria`: Advanced search based on eligibility criteria.
16. `get_study_timeline`: Get timeline information for studies.
17. `search_international_studies`: Find multi-country international clinical trials.
18. `get_version`: Get API and data version information.
19. `get_data_model_fields`: Returns study data model fields.
20. `get_search_areas`: Returns Search Docs and their Search Areas.
21. `get_enums`: Returns enumeration types and their values.
22. `get_study_size_stats`: Returns statistics of study JSON sizes.
23. `get_field_values_stats`: Returns value statistics of the study leaf fields.
24. `get_field_size_stats`: Returns sizes of list/array fields.

## API Limits

The ClinicalTrials.gov API enforces a rate limit of **100 requests per 60 seconds** per connection. This MCP server automatically handles these limits by:
- Tracking request timestamps
- Pausing execution when the limit is reached
- Resuming automatically once the window resets

This ensures compliance with the API's throttling policies without user intervention.

## Usage

### Using uv (Recommended)

```bash
uv run main.py
```

### Installation

```bash
pip install -r requirements.txt
python main.py
```

### How to test/check it

```bash
npx @modelcontextprotocol/inspector uv run main.py
```

This will:
- Start your server.
- Start a local web server (usually at http://localhost:5173).
- Open a browser window where you can click buttons to run your tools (
search_studies, etc.) and see the responses nicely formatted.