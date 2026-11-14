import pytest
from src import MovieStorage
import main


def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 20
    assert body["columns"] == 4
    assert body["column_names"] == ["title", "release_year", "rating", "genre"]


def test_get_movies_with_limit(client, uploaded_movies):
    response = client.get("/movies", params={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 20
    assert [movie["title"] for movie in body["data"]] == ["Movie A", "Movie B"]


def test_search_movies(client, uploaded_movies):
    response = client.get(
        "/movies/search",
        params={"min_rating": 8.5, "limit": 2, "columns": ["title", "rating"]}
    )

    assert response.status_code == 200
    assert response.json() == [
        {"id": 4, "title": "Movie C", "rating": 9.0},
        {"id": 2, "title": "Movie B", "rating": 8.5},
    ]


def test_upload_replaces_collection(client, sample_csv_bytes):
    for _ in range(2):
        response = client.post(
            "/upload",
            files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")}
        )
        assert response.status_code == 200

    response = client.get("/movies")

    assert response.json()["total_rows"] == 20


def test_unsupported_file_extension(client):
    response = client.post(
        "/upload",
        files={"file": ("movies.txt", b"title\nMovie A\n", "text/plain")}
    )

    assert response.status_code == 400
    assert client.get("/health").status_code == 200


def test_process_and_retrieve(client, uploaded_movies, processing_body):
    response = client.post("/movies/process", json=processing_body)

    assert response.status_code == 200
    report = response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16

    response = client.get("/movies")

    assert response.json()["total_rows"] == 16


def test_get_movies_when_empty(client):
    response = client.get("/movies")

    assert response.status_code == 200
    assert response.json() == {"data": [], "total_rows": 0}


def test_movies_persist(client, test_storage, uploaded_movies):
    new_storage = MovieStorage(test_storage.db_path)
    movies = new_storage.get()

    assert new_storage.count_movies() == 20
    assert len(movies) == 20
    assert list(movies.columns) == ["title", "release_year", "rating", "genre"]
    assert movies["title"].tolist() == [
        "Movie A", "Movie B", "Movie B", "Movie C", "Movie D",
        "Movie D", "Movie E", "Movie F", "Movie G", "Movie H",
        "Movie I", "Movie J", "Movie K", "Movie L", "Movie M",
        "Movie N", "Movie O", "Movie P", "Movie Q", "Movie R",
    ]

    stored_rows = new_storage.select_columns(["title"], limit=100)
    response = client.get("/movies", params={"limit": 100})

    assert response.status_code == 200
    stored_ids = [row["id"] for row in stored_rows]
    api_ids = [movie["id"] for movie in response.json()["data"]]
    assert stored_ids == list(range(1, 21))
    assert api_ids == stored_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    response_100 = client.get("/movies", params={"limit": 100})
    response_1 = client.get("/movies", params={"limit": 1})

    assert response_100.status_code == 200
    assert response_1.status_code == 200
    assert main.cache.get(100) == response_100.json()
    assert main.cache.get(1) == response_1.json()

    repeat_response = client.get("/movies", params={"limit": 100})

    assert repeat_response.status_code == 200
    assert repeat_response.json() == response_100.json()

    process_response = client.post("/movies/process", json=processing_body)

    assert process_response.status_code == 200
    report = process_response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"] == {
        "rows_before": 20,
        "rows_after": 16,
        "rows_removed": 4,
        "columns_before": 4,
        "columns_after": 4,
        "columns_removed": 0,
    }
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    new_response = client.get("/movies", params={"limit": 100})

    assert new_response.status_code == 200
    body = new_response.json()
    assert body["total_rows"] == 16
    assert [movie["title"] for movie in body["data"]] == [
        "Movie A", "Movie B", "Movie C", "Movie D",
        "Movie E", "Movie F", "Movie G", "Movie H",
        "Movie I", "Movie J", "Movie K", "Movie L",
        "Movie M", "Movie N", "Movie O", "Movie P",
    ]
    assert [movie["id"] for movie in body["data"]] == list(range(1, 17))
    assert main.cache.get(100) == body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first_response = client.get("/movies", params={"limit": 100})

    assert first_response.status_code == 200
    first_body = first_response.json()

    def fail_if_called(*args, **kwargs):
        pytest.fail("The database should not be used on a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second_response = client.get("/movies", params={"limit": 100})

    assert second_response.status_code == 200
    assert second_response.json() == first_body
