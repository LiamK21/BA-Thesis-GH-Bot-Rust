import io
import json
import re
import shlex
import tarfile
from pathlib import Path

import docker
from docker.errors import APIError, BuildError, ImageNotFound
from docker.models.containers import Container
from docker.models.images import Image

from webhook_handler.models import PullRequestData


class DockerService:
    """
    Used for Docker operations.
    """

    def __init__(self, project_root: Path, pr_data: PullRequestData) -> None:
        self._project_root = project_root
        self._pr_data = pr_data
        self._client = docker.from_env()

    def build_image(self, dockerfile_path: Path) -> None:
        """
        Build a Docker image from the Dockerfiles in the dockerfiles directory.
        """

        # try:
        #     docker_image = self._client.images.get(f"webhook_handler:latest")
        #     return
        # except ImageNotFound:
        #     print("Image not found. Building image...")
        # except APIError as e:
        #     print(f"Error while accessing Docker API: {e.explanation}")
        #     return

        # if not docker_image:

        print("Building Docker image...")

        build_args = {"commit_hash": self._pr_data.base_commit}
        repo_name = self._pr_data.repo.lower()
        dockerfile_path = Path("dockerfiles", f"Dockerfile_{repo_name}")
        print(f"Using Dockerfile at: {dockerfile_path.as_posix()}")
        print(f"With build args: {build_args}")
        print(f"Project root: {self._project_root.as_posix()}")
        tag = f"{self._pr_data.image_tag}:latest"
        print(f"Tagging image as: {tag}")
        try:
            self._client.images.build(
                path=self._project_root.as_posix(),
                tag=tag,
                dockerfile=dockerfile_path.as_posix(),
                buildargs=build_args,
                network_mode="host",
                rm=True,
            )
            build_succeeded = True
            print(f"Docker image '{self._pr_data.image_tag}' built successfully")
        except BuildError as e:
            log_lines = []
            # for chunk in e.build_log:
            #     if "stream" in chunk:
            #         log_lines.append(chunk["stream"].rstrip())
            # full_build_log = "\n".join(log_lines)
            print(f"Build failed for image '{tag}'")
            raise AssertionError("Docker build failed")
        except APIError as e:
            print(f"Docker API error: {e}")
            raise AssertionError("Docker API error")
        # finally:
        #     if not build_succeeded:
        #         print("Cleaning up leftover containers and dangling images...")
        #         for container in self._client.containers.list(all=True):
        #             img = container.image.tags or container.image.id
        #             if img == "<none>:<none>" or not container.image.tags:
        #                 try:
        #                     if container.status == "running":
        #                         container.stop()
        #                     container.remove()
        #                 except APIError as stop_err:
        #                     print(
        #                         f"Failed to remove container {container.id[:12]}: {stop_err}"
        #                     )
        #         try:
        #             dangling = self._client.images.list(filters={"dangling": True})
        #             for img in dangling:
        #                 try:
        #                     self._client.images.remove(image=img.id, force=True)
        #                 except APIError as img_err:
        #                     print(f"Failed to remove image {img.id[:12]}: {img_err}")
        #         except APIError as list_err:
        #             print(f"Error listing dangling images: {list_err}")

    def run_test_in_container(
        self,
        test_patch: str,
        tests_to_run: list,
        added_test_file: str,
        golden_code_patch: str = None,
    ) -> tuple[bool, str]:
        """
        Creates a container, applies the patch, runs the test, and returns the result.

        Parameters:
            test_patch (str): Patch to apply to the model test
            tests_to_run (list): List of tests to run
            added_test_file (str): Path to the file to add to the added tests
            golden_code_patch (str): Patch content for source code

        Returns:
            bool: True if the test has passed, False otherwise
            str: The output from running the test
        """

        try:
            print("Creating container...")
            container = self._client.containers.create(
                image=self._pr_data.image_tag,
                command="/bin/sh -c 'sleep infinity'",  # keep the container running
                tty=True,  # allocate a TTY for interactive use
                detach=True,
            )
            container.start()
            print(f"Container {container.short_id} started")

            # check if the test file is already in the container, add stub otherwise (new file)
            added_file_exists = container.exec_run(
                f"/bin/sh -c 'test -f /app/testbed/{added_test_file}'"
            )
            if added_file_exists.exit_code != 0:
                self._add_file_to_container(container, added_test_file)
                self._whitelist_stub(container, added_test_file.split("/")[-1])

            # check for gulpfile version (mjs or js)
            gulpfile_pointer = "gulpfile.mjs"
            gulpfile_exiss = container.exec_run(
                f"/bin/sh -c 'test -f /app/testbed/{gulpfile_pointer}'"
            )
            if gulpfile_exists.exit_code != 0:
                gulpfile_pointer = "gulpfile.js"
                old_gulpfile_exists = container.exec_run(
                    f"/bin/sh -c 'test -f /app/testbed/{gulpfile_pointer}'"
                )
                if old_gulpfile_exists.exit_code != 0:
                    print("No gulpfile found")
                    raise AssertionError("No gulpfile found")

            # add mock PDF if available
            if self._pdf_name and self._pdf_content:
                self._add_file_to_container(
                    container, f"test/pdfs/{self._pdf_name}", self._pdf_content
                )

            self._copy_and_apply_patch(
                container, patch_content=test_patch, patch_name="test_patch.diff"
            )
            if golden_code_patch is not None:
                self._copy_and_apply_patch(
                    container,
                    patch_content=golden_code_patch,
                    patch_name="golden_code_patch.diff",
                )
            stdout = self._run_test(container, gulpfile_pointer, tests_to_run)
            test_passed = self._evaluate_test(stdout)
            return test_passed, stdout
        finally:
            print("Stopping and removing container...")
            container.stop()
            container.remove()
            print("Container stopped and removed")

    @staticmethod
    def _add_file_to_container(
        container: Container, file_path: str, file_content: str | bytes = ""
    ) -> None:
        """
        Adds file to Docker container.

        Parameters:
            container (Container): Container to add file to
            file_path (str): Path to the file to add to the container
            file_content (str | bytes, optional): Content to add to the file
        """

        if isinstance(file_content, str):
            content = file_content.encode("utf-8")
        else:
            content = file_content

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            ti = tarfile.TarInfo(name=file_path)
            ti.size = len(file_content)
            tar.addfile(ti, io.BytesIO(content))
        tar_stream.seek(0)
        try:
            container.put_archive("/app/testbed", tar_stream.read())
            print(f"File {file_path} added to container successfully")
        except APIError as e:
            print(f"Docker API error: {e}")
            raise AssertionError("Docker API error")

    def _whitelist_stub(self, container: Container, file_name: str) -> None:
        """
        Adds the new file to the whitelist for it to be detectable by Jasmine.

        Parameters:
            container (Container): Container to modify whitelist in
            file_name (str): Name of the file to add to the whitelist
        """

        whitelist_path = "test/unit/clitests.json"
        read = container.exec_run(
            f"/bin/sh -c 'cd /app/testbed && cat {whitelist_path}'"
        )
        if read.exit_code != 0:
            print(f"Could not read clitests.json: {read.output.decode()}")
            raise AssertionError("Failed to whitelist stub")

        whitelist = json.loads(read.output.decode())
        if file_name not in whitelist["spec_files"]:
            whitelist["spec_files"].append(file_name)
            updated_whitelist = json.dumps(whitelist, indent=2) + "\n"
            self._add_file_to_container(container, whitelist_path, updated_whitelist)

    def _copy_and_apply_patch(
        self, container: Container, patch_content: str, patch_name: str
    ) -> None:
        """
        Copies file to container and applies patch.

        Parameters:
            container (Container): Container to apply patch
            patch_content (str): Patch to apply to the container
            patch_name (str): Name of the path file
        """

        self._add_file_to_container(container, patch_name, patch_content)

        # apply the patch inside the container
        apply_patch_cmd = f"/bin/sh -c 'cd /app/testbed && patch -p1 < {patch_name}'"
        exec_result = container.exec_run(apply_patch_cmd)

        if exec_result.exit_code != 0:
            print(f"Failed to apply patch: {exec_result.output.decode()}")
            raise AssertionError("Failed to apply patch")

        print(f"Patch file {patch_name} applied successfully")

    @staticmethod
    def _run_test(
        container: Container, gulpfile_pointer: str, tests_to_run: list
    ) -> str:
        """
        Runs tests in container.

        Parameters:
            container (Container): Container to run test
            gulpfile_pointer (str): Determines whether to use gulpfile.mjs or gulpfile.js
            tests_to_run (list): List of tests to run

        Returns:
            str: The test output
        """

        test_commands = []
        for desc in tests_to_run:
            inner = f"TEST_FILTER='{desc}' npx gulp --gulpfile {gulpfile_pointer} unittest-single"
            test_single = shlex.quote(inner)
            cmd = f"timeout 300 /bin/sh -c {test_single}"
            test_commands.append(cmd)

        joined_cmds = " && ".join(test_commands)

        cd_test = shlex.quote(f"cd /app/testbed && {joined_cmds}")

        full_test_command = "/bin/sh -c " f"{cd_test}"

        print("Running test command...")
        exec_result = container.exec_run(full_test_command, stdout=True, stderr=True)
        output = exec_result.output.decode()
        if exec_result.exit_code == 124:
            print("Test command killed by timeout")
        else:
            pattern = re.compile(
                r"^Ran\s+\d+\s+of\s+\d+\s+specs?\r?\n\d+\s+specs?,\s+\d+\s+failures?$",
                re.MULTILINE,
            )
            if pattern.search(output):
                print("Test command executed")
            else:
                print("Test command failed")

        return exec_result.output.decode()

    @staticmethod
    def _evaluate_test(stdout: str) -> bool:
        """
        Evaluates test output.

        Parameters:
            stdout (str): Output of test command

        Returns:
            bool: True if the test has passed, False otherwise
        """

        if re.search(r"\b0\s+specs\b", stdout):  # no tests were executed
            print("No tests were executed")
            test_passed = False
        else:
            match = re.search(
                r"\b(\d+)\s+failures?\b", stdout
            )  # extract the number of failures
            if match:
                num_failures = int(match.group(1))
                test_passed = True if num_failures == 0 else False
            else:
                print("Test could not be evaluated")
                return False

        (
            print(f"Test evaluated as passed")
            if test_passed
            else print(f"Test evaluated as failed")
        )
        return test_passed
