"""Tests for the friendly error pages in app/errors.py."""

from conftest import log_in


def test_404_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    page = response.get_data(as_text=True)
    assert "We couldn&#39;t find that page." in page
    assert "Error 404" in page


def test_404_for_missing_course_uses_the_same_page(client, make_user):
    log_in(client, make_user())
    response = client.get("/courses/999")
    assert response.status_code == 404
    assert "Go to your courses" in response.get_data(as_text=True)


def test_403_page_for_student_on_staff_page(client, make_user):
    log_in(client, make_user())
    response = client.get("/courses/new")
    assert response.status_code == 403
    assert "You can&#39;t do that here." in response.get_data(as_text=True)


def test_405_page_for_get_on_post_only_route(client, make_user):
    log_in(client, make_user())
    response = client.get("/auth/logout")
    assert response.status_code == 405
    assert "Error 405" in response.get_data(as_text=True)


def test_expired_form_gets_a_clear_message(app, client, make_user):
    app.config["WTF_CSRF_ENABLED"] = True  # TestConfig turns CSRF off; switch it back on here
    response = client.post("/auth/login", data={"email": "a@b.com", "password": "x"})
    assert response.status_code == 400
    assert "This form expired." in response.get_data(as_text=True)


def test_500_page_hides_the_error_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False  # in testing Flask re-raises errors by default

    @app.route("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    response = client.get("/boom")
    assert response.status_code == 500
    page = response.get_data(as_text=True)
    assert "Something went wrong on our side." in page
    assert "secret internal detail" not in page


def test_logged_out_error_page_offers_login(client):
    page = client.get("/no-such-page").get_data(as_text=True)
    assert 'href="/auth/login"' in page
