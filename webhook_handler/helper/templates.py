COMMENT_TEMPLATE = """Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:
- passes, and
- fails in the codebase before the PR.

```python
%s
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `%s` file before running it.

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
If you have any suggestions, questions, or simply want to learn more, feel free to contact us at konstantinos.kitsios@uzh.ch and mcastelluccio@mozilla.com.
"""


def get_instruction_template(repo_name: str) -> str:
    return (
        "Your task:\n"
        f"You are a software tester at {repo_name}.\n"
        "1. Write exactly one Rust test that uses the standard Rust testing framework.\n"
        "2. Your test must fail on the code before the patch, and pass after, hence "
        "the test will verify that the patch resolves the issue.\n"
        "3. The test must be self-contained and to-the-point.\n"
        "5. Return only the Rust code (no comments or explanations).\n\n"
    )
