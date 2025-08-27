import json
import os

from bot_runner import BotRunner
from config import Config
from django.test import TestCase


def _get_payload(rel_path: str) -> dict:
    abs_path = os.path.join(os.path.dirname(__file__), rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload


#
# RUN With: python manage.py test webhook_handler.test.tests_rust-code-analysis.<testname>
#
class TestGeneration605(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_605.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation605(self):
        generation_completed = self.runner.execute_runner()
        self.assertTrue(generation_completed)
        pass


class TestGeneration616(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_616.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation616(self):
        generation_completed = self.runner.execute_runner()
        self.assertTrue(generation_completed)
        pass


class TestGeneration620(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_620.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation620(self):
        generation_completed = self.runner.execute_runner()
        self.assertTrue(generation_completed)
        pass
