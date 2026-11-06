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
    assert report["cleaning_report"]["rows_after"] == 18

    response = client.get("/movies")

    assert response.json()["total_rows"] == 18


def test_get_movies_when_empty(client):
    response = client.get("/movies")

    assert response.status_code == 200
    assert response.json() == {"data": [], "total_rows": 0}
