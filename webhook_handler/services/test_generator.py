import logging
from pathlib import Path

from webhook_handler.constants import PROMPT_COMBINATIONS_GEN
from webhook_handler.helper import git_diff, templates
from webhook_handler.models import LLM, PipelineInputs, PullRequestData
from webhook_handler.services import Config
from webhook_handler.services.cst_builder import CSTBuilder
from webhook_handler.services.docker_service import DockerService
from webhook_handler.services.gh_service import GitHubService
from webhook_handler.services.llm_handler import LLMHandler

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Runs a full pipeline to generate a test using a LLM and then verifying its correctness.
    """

    def __init__(
        self,
        config: Config,
        data: PipelineInputs,
        post_comment: bool,
        gh_service: GitHubService,
        cst_builder: CSTBuilder,
        docker_service: DockerService,
        llm_handler: LLMHandler,
        i_attempt: int,
        model: LLM,
    ):
        self._config = config
        self._pipeline_inputs = data
        self._pr_data = data.pr_data
        self._pr_diff_ctx = data.pr_diff_ctx
        self._prompt_combinations = PROMPT_COMBINATIONS_GEN
        self._post_comment = post_comment
        self._comment_template = templates.COMMENT_TEMPLATE
        self._gh_service = gh_service
        self._cst_builder = cst_builder
        self._docker_service = docker_service
        self._llm_handler = llm_handler
        self._i_attempt = i_attempt
        self._model = model

    def generate(self) -> bool:
        """
        Runs the pipeline to generate a fail-to-pass test.

        Returns:
            bool: True if a fail-to-pass test has been generated, False otherwise
        """

        # logger.marker("Attempt %d with model %s" % (self._i_attempt + 1, self._model))
        # logger.marker("=============== Test Generation Started ==============")

        # include_golden_code = bool(self._prompt_combinations["include_golden_code"][self._i_attempt])
        # sliced = bool(self._prompt_combinations["sliced"][self._i_attempt])
        # include_pr_summary = bool(self._prompt_combinations["include_pr_summary"][self._i_attempt])
        # include_predicted_test_file = bool(self._prompt_combinations["include_predicted_test_file"][self._i_attempt])

        prompt = self._llm_handler.build_prompt(
            # include_golden_code,
            # sliced,
            # include_pr_summary,
            # include_predicted_test_file,
            # self._pipeline_inputs.test_filename,
            # self._pipeline_inputs.test_file_content_sliced,
            # self._pipeline_inputs.available_packages,
            # self._pipeline_inputs.available_relative_imports
        )

        if len(prompt) >= 1048576:  # gpt4o limit
            logger.critical("Prompt exceeds limits, skipping...")
            raise Exception("Prompt is too long.")

        assert self._config.output_dir is not None
        generation_dir = Path(self._config.output_dir, "generation")
        (generation_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        # if self._mock_response is None:
        # logger.info("Querying LLM...")
        print("Querying LLM...")
        response = self._llm_handler.query_model(
            prompt, model=self._model, temperature=0.0
        )
        if not response:
            # logger.critical("Failed to query model")
            raise Exception("Failed to query model")

        # logger.success("LLM response received")
        print("LLM response received")
        (generation_dir / "raw_model_response.txt").write_text(
            response, encoding="utf-8"
        )
        new_test = self._llm_handler.postprocess_response(response)
        # else:
        #     new_test = self._mock_response

        (generation_dir / "generated_test.txt").write_text(new_test, encoding="utf-8")
        new_test = new_test.replace(
            "src/", ""
        )  # temporary replacement to run in lib-legacy

        if self._pipeline_inputs.test_file_content:
            new_test_file_content = self._cst_builder.append_function(
                self._pipeline_inputs.test_file_content, new_test
            )
        else:
            new_test_file_content = new_test

        model_test_patch = (
            git_diff.unified_diff(
                self._pipeline_inputs.test_file_content,
                new_test_file_content,
                fromfile=self._pipeline_inputs.test_filename,
                tofile=self._pipeline_inputs.test_filename,
            )
            + "\n\n"
        )

        test_file_diff = PullRequestFileDiff(
            self._pipeline_inputs.test_filename,
            self._pipeline_inputs.test_file_content,
            new_test_file_content,
        )

        test_to_run = self._cst_builder.extract_changed_tests(test_file_diff)

        # logger.marker("Running test in pre-PR codebase...")
        test_passed_before, stdout_before = self._docker_service.run_test_in_container(
            model_test_patch, test_to_run, test_file_diff.name
        )
        (generation_dir / "before.txt").write_text(stdout_before, encoding="utf-8")
        new_test_file = (
            f"#{self._pipeline_inputs.test_filename}\n{new_test_file_content}"
            if self._pipeline_inputs.test_file_content
            else f"#{self._pipeline_inputs.test_filename}\n{new_test}"
        )
        (generation_dir / "new_test_file_content.js").write_text(
            new_test_file, encoding="utf-8"
        )

        if test_passed_before:
            print("No Fail-to-Pass test generated")
            # logger.fail("No Fail-to-Pass test generated")
            # logger.marker("=============== Test Generation Finished =============")
            return False

        # logger.marker("Running test in post-PR codebase...")
        print("Running test in post-PR codebase...")
        test_passed_after, stdout_after = self._docker_service.run_test_in_container(
            model_test_patch,
            test_to_run,
            test_file_diff.name,
            golden_code_patch=self._pr_diff_ctx.golden_code_patch,
        )
        (generation_dir / "after.txt").write_text(stdout_after, encoding="utf-8")

        if not test_passed_before and test_passed_after:
            # logger.success("Fail-to-Pass test generated")
            print("Fail-to-Pass test generated")
            # comment = self._comment_template % (
            #     (generation_dir / "generated_test.txt").read_text(encoding="utf-8"),
            #     self._pipeline_inputs.test_filename
            # )
            # if self._post_comment:
            #     status_code, response_data = self._gh_service.add_comment_to_pr(comment)
            #     if status_code == 201:
            #         logger.success("Comment added successfully:\n\n%s" % comment)
            #     else:
            #         logger.fail(f"Failed to add comment: {status_code}", response_data)
            # else:
            #     logger.success("Suggested test for PR:\n\n%s" % comment)
            print("================= Test Generation Finished ==============")
            # logger.marker("=============== Test Generation Finished =============")
            return True
        else:
            print("No Fail-to-Pass test generated")
            print("================= Test Generation Finished ==============")
            # logger.fail("No Fail-to-Pass test generated")
            # logger.marker("=============== Test Generation Finished =============")
            return False
