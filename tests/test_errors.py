def test_404_renders_friendly_page(client):
    rv = client.get("/this-route-definitely-does-not-exist")
    assert rv.status_code == 404
    assert b"Not Found" in rv.data
    assert b"Back to dashboard" in rv.data
