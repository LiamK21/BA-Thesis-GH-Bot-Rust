import re

from config import Config
from groq import Groq
from models.llm_enum import LLM
from openai import OpenAI


class LLMHandler:
    """
    Used to interact with LLMs.
    """

    def __init__(self, config: Config) -> None:
        self._openai_client = OpenAI(api_key=config.openai_key)
        self._groq_client = Groq(api_key=config.groq_key)

    def build_prompt(self, payload: dict) -> str:
        """
        Builds the prompt to be sent to the LLM.
        """
        return "This is a test prompt."

    def query_model(self, prompt: str, model: LLM, temperature: float = 0.0) -> str:
        """
        Query a model and return its results.

        Parameters:
            prompt (str): Prompt to ask for
            model (LLM): Model to use
            temperature (float, optional): Temperature to use. Defaults to 0.0

        Returns:
            str: Response from model
        """

        try:
            if model == LLM.GPT4o:
                response = self._openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.GPTo3_MINI:  # does not accept temperature
                response = self._openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.LLAMA:
                completion = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=700,
                    temperature=temperature,
                )
                result = completion.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.DEEPSEEK:
                response = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an experienced software tester specializing in developing regression tests. Follow the user's instructions for generating a regression test. The output format is STRICT: do all your reasoning in the beginning, but the end of your output should ONLY contain javascript code, i.e., NO natural language after the code.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            else:
                return ""
        except:
            return ""

    def postprocess_response(self, response: str) -> str:
        """
        Postprocess the response from the LLM.

        Parameters:
            response (str): Response from the LLM

        Returns:
            str: Postprocessed response
        """
        cleaned_test = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        cleaned_test = cleaned_test.replace("```rust", "")
        cleaned_test = cleaned_test.replace("```", "")
        cleaned_test = cleaned_test.lstrip("\n")
        cleaned_test = self._clean_descriptions(cleaned_test)
        return self._adjust_function_indentation(cleaned_test)

    @staticmethod
    def _clean_descriptions(function_code: str) -> str:
        """
        Cleans the call expression descriptions used in the generated test by removing every non-letter character and multiple whitespaces.

        Parameters:
            function_code (str): Function code to clean

        Returns:
            str: Cleaned function code
        """

        pattern = re.compile(
            r"\b(?P<ttype>describe|it)\(\s*"  # match describe( or it(
            r'(?P<quote>[\'"])\s*'  # capture opening quote
            r"(?P<name>.*?)"  # capture the raw name
            r"(?P=quote)\s*,",  # match the same closing quote, then comma
            flags=re.DOTALL,
        )

        def clean_test_name(match):
            test_type = match.group("ttype")
            q = match.group("quote")
            name = match.group("name")
            # strip out anything but A–Z or a–z
            cleaned = re.sub(r"[^A-Za-z ]", "", name)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return f"{test_type}({q}{cleaned}{q},"

        return pattern.sub(clean_test_name, function_code)

    @staticmethod
    def _adjust_function_indentation(function_code: str) -> str:
        """
        Adjusts the indentation of a rust function so that the function definition
        has no leading spaces, and the internal code indentation is adjusted accordingly.

        Parameters:
            function_code (str): The Javascript function

        Returns:
            str: The adjusted function code
        """

        lines = function_code.splitlines()

        if not lines:
            return ""

        # find the leading spaces of the first non-empty line
        first_non_empty_line = next(line for line in lines if line.strip())
        leading_spaces = len(first_non_empty_line) - len(first_non_empty_line.lstrip())

        return "\n".join(
            [line[leading_spaces:] if line.strip() else "" for line in lines]
        )
