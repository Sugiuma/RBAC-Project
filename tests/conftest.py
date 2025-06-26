import pytest

@pytest.fixture(scope="function")
def context(browser):
    return browser.new_context(record_video_dir="videos/")

@pytest.fixture(scope="function")
def page(context):
    return context.new_page()