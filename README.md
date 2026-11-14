# MP3 Movie API

This project is a FastAPI application that stores a movie collection in SQLite and returns it through a REST API. `main.py` defines the endpoints, and the `src/` package contains the Pydantic models (`models.py`), the SQLite setup (`database.py`), the `MovieStorage` class (`storage.py`), the `MovieCache` class (`cache.py`), the request logging middleware (`middleware.py`), and the logging setup (`utils.py`). `POST /upload` accepts a CSV file with exactly the four columns `title`, `release_year`, `rating`, and `genre`, and replaces all stored movies in one SQLite transaction. Because the movies are saved in `data/movies.db`, they are still there after the server restarts, and `GET /movies` and `GET /movies/search` read them back with SQL queries. `POST /movies/process` loads the stored movies, validates and cleans them with the MP1 functions in `data_pipeline/`, and saves the cleaned rows back to SQLite. Responses from `GET /movies` are cached in FakeRedis for 90 seconds, with one key for each `limit` value, while `GET /movies/search` is not cached. After a successful upload or processing request, the whole cache is cleared, so the next `GET /movies` reads the new data from SQLite.

## Start the API

From the repository root, with the virtual environment active:

```bash
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Run the Tests

```bash
python -m pytest tests -v
```

## Sample Processing Request

After uploading `fixtures/sample_movies.csv` with `POST /upload`, send this body to `POST /movies/process`:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected result:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```

The two duplicate rows (Movie B and Movie D) and the two low-rating outliers (Movie Q and Movie R) are removed, so 20 rows become 16.
