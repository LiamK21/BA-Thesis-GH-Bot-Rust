import json
import os

from django.test import TestCase

from webhook_handler.bot_runner import BotRunner
from webhook_handler.constants import USED_MODELS, get_total_attempts
from webhook_handler.services import Config


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
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation605(self):
        self.config.setup_pr_related_dirs(
            self.pr_id, self.owner, self.repo, self.payload
        )
        generation_completed = False
        total_attempts = get_total_attempts()
        # This approach is only temporary until prompt combinations are defined
        for model in USED_MODELS:
            for curr_attempt in range(total_attempts):
                if generation_completed:
                    break
                self.config.setup_output_dir(curr_attempt, model)
                generation_completed = self.runner.execute_runner(curr_attempt, model)
            if generation_completed:
                break

        self.assertTrue(generation_completed)


class TestGeneration616(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_616.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation616(self):
        self.config.setup_pr_related_dirs(
            self.pr_id, self.owner, self.repo, self.payload
        )
        generation_completed = False
        total_attempts = get_total_attempts()
        # This approach is only temporary until prompt combinations are defined
        for model in USED_MODELS:
            for curr_attempt in range(total_attempts):
                if generation_completed:
                    break
                self.config.setup_output_dir(curr_attempt, model)
                generation_completed = self.runner.execute_runner(curr_attempt, model)
            if generation_completed:
                break

        self.assertTrue(generation_completed)


class TestGeneration620(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_620.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation620(self):
        self.config.setup_pr_related_dirs(
            self.pr_id, self.owner, self.repo, self.payload
        )
        generation_completed = False
        total_attempts = get_total_attempts()
        # This approach is only temporary until prompt combinations are defined
        for model in USED_MODELS:
            for curr_attempt in range(total_attempts):
                if generation_completed:
                    break
                self.config.setup_output_dir(curr_attempt, model)
                generation_completed = self.runner.execute_runner(curr_attempt, model)
            if generation_completed:
                break

        self.assertTrue(generation_completed)
