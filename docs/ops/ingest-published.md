# Published Corpus Ingestion

Import articles from a JSON file into the Published corpus tables (`sources`, `articles`).

## JSON Format (array of objects)
```
{
  "title": "Article Title",
  "content": "Full content...",
  "ts": "2024-05-09T09:00:00Z" | 1715245200,
  "author": "Author Name",
  "url": "https://domain/path",
  "tags": ["ai", "governance"],
  "meta": {"any": "thing"},
  "source": {"domain": "domain", "authority_score": 0.7}
}
```

If `source.domain` is omitted, the importer derives the domain from `url` and
assigns `--default-authority` (default 0.0).

## Command
```
python -m mcg_agent.ingest.published_loader --path path/to/articles.json --default-authority 0.3
```

