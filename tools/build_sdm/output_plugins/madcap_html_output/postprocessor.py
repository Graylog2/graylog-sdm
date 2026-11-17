import re


class DocumentPostprocessor:
    '''
    Runs enabled HTML postprocessing transformations in a defined order:
    1. Strip leading whitespace in multiline block tags
    2. Remove trailing whitespace after ending tags
    3. Collapse multiple newline breaks
    4. Apply docs-specific formatting (e.g., code tag adjustments)

    Each step is optional based on flags set at initialization.
    '''
    def __init__(
        self,
        lstrip_multiline_block: bool = True,
        rstrip_ending_tags: bool = True,
        apply_docs_formatting: bool = True,
        remove_newlines: bool = True
    ):

        self.lstrip_multiline_block: bool = lstrip_multiline_block
        self.rstrip_ending_tags: bool = rstrip_ending_tags
        self.remove_newlines: bool = remove_newlines
        self.apply_docs_formatting: bool = apply_docs_formatting

    @staticmethod
    def _lstrip_multiline_block(html: str, tag_name: str = 'MadCap:codeSnippetBody') -> str:
        '''
        Removes leading whitespace from all lines inside the specified block tag.

        Args:
            html (str): The full HTML render result.
            tag_name (str): HTML tag containing multiline text to lstrip.

        Returns:
            str: Modified HTML with stripped block content.
        '''

        pattern = re.compile(
            rf'(<{tag_name}[^>]*>)(.*?)(</{tag_name}>)',
            re.DOTALL
        )

        def strip(match: re.Match[str]):
            open_tag, content, close_tag = match.groups()
            lines = content.splitlines()

            if not lines:
                return match.group(0)

            trimmed_content = '\n'.join(line.lstrip() for line in lines)
            return f'{open_tag}{trimmed_content}{close_tag}'

        return pattern.sub(strip, html)

    @staticmethod
    def _rstrip_ending_tags(html: str) -> str:
        '''
        Removes any trailing whitespace after ending tags.

        Args:
            html (str): The full HTML render result.

        Returns:
            str: Modified HTML with trailing whitespace removed.
        '''

        pattern = re.compile(
            r'(</[^>]*>\s+)\n',
            re.DOTALL
        )

        def strip(match: re.Match[str]):
            return match[1].rstrip() + '\n'

        return pattern.sub(strip, html)

    @staticmethod
    def _remove_newlines(html: str) -> str:
        '''
        Removes newlines between ending and starting tags.

        Args:
            html (str): The full HTML render result.

        Returns:
            str: Modified HTML with newlines removed.
        '''

        pattern = re.compile(
            r'(</[^>]*>)(\s*\n\s*\n\s*)(<[^>]*>)',
            re.DOTALL
        )

        def remove(match: re.Match[str]):
            close_tag, content, open_tag = match.groups()

            trimmed_content = re.sub(r'^\s*\n\s*\n', '\n', content)
            return f'{close_tag}{trimmed_content}{open_tag}'

        return pattern.sub(remove, html)

    @staticmethod
    def _apply_docs_formatting(html: str) -> str:
        '''
        Applies various formatting requirements posed by the docs team.

        Args:
            html (str): The full HTML render result.

        Returns:
            str: Modified HTML with docs formatting applied.
        '''

        # Move </td> to next line when contains a <code> element

        pattern = re.compile(
            r'^(\s+)(<td [^>]+>[^<]*<code [^>]+>[^<]*</code>) *</td> *$',
            re.MULTILINE
        )

        def apply(match: re.Match[str]):
            leading_space, row_content = match.groups()
            return f'{leading_space}{row_content}\n{leading_space}</td>'

        return pattern.sub(apply, html)

    def clean(self, html: str) -> str:
        if self.lstrip_multiline_block:
            for tag in ('MadCap:codeSnippetBody',):  # Add more tags here if needed
                html = self._lstrip_multiline_block(html, tag)

        if self.rstrip_ending_tags:
            html = self._rstrip_ending_tags(html)

        if self.remove_newlines:
            html = self._remove_newlines(html)

        if self.apply_docs_formatting:
            html = self._apply_docs_formatting(html)

        return html
