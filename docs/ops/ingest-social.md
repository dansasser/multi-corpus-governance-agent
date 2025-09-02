# Social Corpus Ingestion

Import social posts from a JSON file into the Social corpus tables (`posts`, `comments`).

## JSON Format (array of objects)
```
{
  "platform": "twitter",
  "content": "Post text",
  "ts": "2024-08-07T13:05:00Z" | 1723035900,
  "url": "https://...",
  "hashtags": ["tag1", "tag2"],
  "mentions": ["@user"],
  "engagement": 42,
  "meta": {"any": "thing"},
  "comments": [
    {"author": "x", "content": "y", "ts": "2024-08-07T13:06:00Z", "engagement": 1}
  ]
}
```

## Command
```
python -m mcg_agent.ingest.social_loader --path path/to/posts.json --platform twitter
```

