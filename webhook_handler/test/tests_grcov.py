import json
import os
from datetime import datetime

from django.test import TestCase

from webhook_handler.bot_runner import BotRunner
from webhook_handler.constants import USED_MODELS, get_total_attempts
from webhook_handler.models import LLM
from webhook_handler.services.config import Config


def _get_payload(rel_path: str) -> dict:
    abs_path = os.path.join(os.path.dirname(__file__), rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload


#
# RUN With: python manage.py test webhook_handler.test.tests_grcov.<testname>
#
class TestGeneration1180(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/grcov/pr_1180.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        del self.payload
        del self.config
        del self.runner
        return super().tearDown()

    def test_generation1180(self):
        self.config.setup_pr_related_dirs(
            self.pr_id, self.owner, self.repo, self.payload
        )
        generation_completed = False
        total_attempts = get_total_attempts()
        # This approach is only temporary until prompt combinations are defined
        model = LLM.GPT4o
        # for model in USED_MODELS:
        # for curr_attempt in range(total_attempts):
        # if generation_completed:
        # break
        self.config.setup_output_dir(0, model)
        generation_completed = self.runner.execute_runner(0, model)
        # if generation_completed:
        #     break

        self.assertTrue(generation_completed)


class TestGeneration1362(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/grcov/pr_1362.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        self.pr_id = self.runner._pr_data.id
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation1362(self):
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


class TestGeneration1394(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/grcov/pr_1394.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        self.pr_id = self.runner._pr_data.id
        self.pr_id = self.runner._pr_data.id
        self.owner = self.runner._pr_data.owner
        self.repo = self.runner._pr_data.repo

    def tearDown(self) -> None:
        return super().tearDown()

    def test_generation1394(self):
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
