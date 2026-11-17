import logging
import re

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
    Template,
    TemplateNotFound,
    TemplateSyntaxError,
    TemplateError
)
import markdown as md
from pathlib import Path
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, List

from base_output import OutputPlugin
from gim_schema.sub_fields import SubFieldRow, expand_sub_fields
from utils.file import write_file
from utils.sanitize import check_string, sanitize_string

from .markdown_ext import InlineCodeClassExtension
from .models import (
    MadcapHtmlOutputConfig,
    MadcapHtmlOutputPluginConfig,
    MadcapTopLevelConfig,
    SafeSubdir,
    TopLevelFieldSchemaSectionMetadata,
    TopLevelGimSectionMetadata,
)
from .postprocessor import DocumentPostprocessor


class MadcapHtmlOutput(OutputPlugin[MadcapHtmlOutputConfig]):
    enabled_by_default = False
    config_schema = MadcapHtmlOutputConfig
    top_level_config_schema = MadcapTopLevelConfig

    @classmethod
    def load_top_level_config(cls, raw_data: dict) -> Optional[MadcapTopLevelConfig]:
        try:
            return MadcapTopLevelConfig.parse_obj(raw_data)
        except ValidationError as e:
            cls().logger.error('Validation failed for top-level plugin config: %s', e.errors())
            return None

    @classmethod
    def load_plugin_config(cls, raw_dict):            # type: ignore[override]
        '''
        Validate a *top-level* MadCap output-plugin config file
        (type = "config_output_plugin").

        raw_dict is the TOML dict *exactly as parsed* by config_loader.
        '''
        raw_for_schema = {k: v for k, v in raw_dict.items() if k != 'type'}
        return cls.top_level_config_schema(**raw_for_schema)

    def __init__(self) -> None:
        '''
        Initialize the plugin and its logger.
        '''
        super().__init__()
        self.plugin_name: str = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        self.logger = logging.getLogger(self.plugin_name)
        self._env: Optional[Environment] = None

    def generate(
        self,
        gim_config: Dict,
        output_dir: Path,
        plugin_config: Optional[MadcapHtmlOutputConfig] = None
    ) -> None:
        '''
        Generate HTML documentation artifacts using Jinja2 templates for each
        category defined in the GIM configuration.
        '''
        plugin_config = self._resolve_plugin_config(plugin_config)

        try:
            self._initialize_jinja_environment()
            self._generate_top_level_pages(gim_config, output_dir)
            self._generate_category_pages(gim_config, output_dir)
            self._generate_field_schema_entity_pages(gim_config, output_dir, plugin_config)
        except Exception as e:
            self.logger.critical('Fatal error while generating category pages: %s', e, exc_info=True)
            raise RuntimeError('Failed during GIM category page generation') from e

        self.logger.debug('Plugin processing completed.')

    def _resolve_plugin_config(self, config: Optional[MadcapHtmlOutputConfig]) -> MadcapHtmlOutputConfig:
        '''
        Resolve and return the top-level plugin configuration, using default values if not provided.
        '''
        if isinstance(config, MadcapHtmlOutputConfig):
            self.logger.debug('Validated top-level plugin config provided')
            return config
        self.logger.warning('Plugin config missing or invalid; using defaults.')
        return MadcapHtmlOutputConfig()

    def _validate_category_plugin_config(
        self,
        raw_config: Optional[Dict],
        category: str
    ) -> Optional[MadcapHtmlOutputPluginConfig]:
        '''
        Validate the plugin configuration for a specific category or entity. Log and skip on validation failure.
        '''
        try:
            return MadcapHtmlOutputPluginConfig(**raw_config or {})
        except ValidationError as e:
            self.logger.error(
                'Validation failed for plugin config in category/entity [%s]: %s',
                category, e.errors()
            )
            return None

    def _initialize_jinja_environment(self, template_dir: Path | None = None) -> None:
        '''
        Set up the Jinja2 template environment using the plugin's bundled template directory,
        and register any custom filters used in the templates.

        Args:
            template_dir: Path to the Jinja2 template directory. When None, defaults to
                the html_templates/ directory bundled with this plugin.
        '''
        if template_dir is None:
            template_dir = Path(__file__).parent / 'html_templates'
        self.logger.debug('Using template directory [%s]', template_dir)

        env = Environment(
            loader=FileSystemLoader(searchpath=str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Register custom filters
        env.filters['markdown'] = self._render_markdown
        env.filters['regex_replace'] = self._regex_replace_filter
        env.filters['indent_lists'] = self._indent_list_items

        self._env = env

    def _load_template(self, template_name: str, category: str) -> Optional[Template]:
        '''
        Load and return the Jinja2 template for a given category. Log and return None on failure.
        '''
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound:
            self.logger.error('Template not found [%s] for category [%s]', template_name, category)
            return None
        except TemplateSyntaxError as e:
            self.logger.error('Syntax error in [%s] line %s: %s', template_name, e.lineno, e.message)
            return None
        except TemplateError as e:
            self.logger.error('Template error while loading [%s]: %s', template_name, e)
            return None
        else:
            self.logger.debug('Using HTML template [%s] for category [%s]', template_name, category)
            return template

    def _render_template(
        self,
        template: Template,
        category: str,
        category_data: Dict,
        config: Dict,
        extra_context: Optional[Dict] = None
    ) -> Optional[str]:
        '''
        Render the provided Jinja2 template using context variables.
        Additional variables may be injected via `extra_context`.
        '''
        try:
            context = {
                'category': category,
                'category_data': category_data,
                'config': config
            }
            if extra_context:
                context.update(extra_context)

            return template.render(**context)

        except Exception as e:
            self.logger.error(
                'Failed to render template for entry type [%s]: %s',
                category, e
            )
            return None

    def _indent_list_items(self, html: str, indent_width: int = 4) -> str:
        '''
        Indent <li> elements inside <ul> or <ol> blocks for pretty HTML output.
        Only affects whitespace between tags; does not change semantics.
        This is intended only for use on text that has been rendered from
        markdown to HTML, which produces flat lists.
        '''
        if not html:
            return html

        indent = ' ' * indent_width
        # Add indentation before each <li> tag that follows a newline
        html = re.sub(r'(?<=\n)<li>', f'{indent}<li>', html)
        # Optionally indent closing </ul> and </ol> tags for symmetry
        #html = re.sub(r'(?<=\n)</(ul|ol)>', f'{indent}</\\1>', html)
        return html

    def _prepare_markdown_for_rendering(self, text: str) -> str:
        '''
        Replace single newlines with a space but keep double newlines intact.
        '''
        text = text.strip()
        text = text.replace('\r\n', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)  # collapse >2 blank lines
        text = re.sub(r'\n+$', '', text) # trim trailing newlines

        # Two or more spaces at the end of a line are rendered as <br>. Trim these since they
        # can break up the flow of the pages.
        #text = re.sub(r'  +\n',' ', text)

        return text

    def _render_markdown(self, text: str) -> str:
        """
        Convert a Markdown string into HTML, applying inline code formatting.

        Strip any outer `<p>` tags for inline use.

        Args:
            text (str): Markdown-formatted input.

        Returns:
            str: HTML-rendered version of the input.
        """
        text_cleaned = self._prepare_markdown_for_rendering(text)

        html = md.markdown(
            text_cleaned,
            extensions=["extra", InlineCodeClassExtension(), 'sane_lists'],
            output_format="html"
        )

        # Clean empty whitespace padding /p tag
        html = re.sub(r'[\n\s]+</p>', '</p>', html)

        # format break tags. Per the HTML 5 spec (Nov 2025) "void elements" like <br>, <hr>, etc.
        # do not need the end of tag solidus but Flare complains about it. There should not be any
        # <br> tags rendered by the markdown engine but this will correct any that have been added
        # intentionally.
        html = re.sub(r'<br>', '<br />', html)

        return html

    def _build_output_path(self, section: str, section_cfg: dict) -> str:
        '''
        Determine a safe output path by inspecting the MadCap section configuration and
        verifying the string is safe. If the MadCap section configuration does not contain
        a directory name for "html_output_subdir" or it is not a valid path the function
        will sanitize the section name and use that instead.

        Args:
            section: The section name
            section_cfg: The current section configuration

        Returns:
            The sanitized path location.
        '''
        self.logger.debug('Determining safe output subdirectory')
        html_output_subdir = section_cfg.get('html_output_subdir')
        if html_output_subdir is None:
            html_output_subdir = sanitize_string(section)
            self.logger.debug(
                'The subdirectory value for html_output_subdir is not set, using [%s]',
                html_output_subdir
            )
        else:
            if check_string(html_output_subdir):
                self.logger.debug('Writing top-level pages to %s', html_output_subdir)
            else:
                self.logger.warning(
                    'Invalid html_output_subdir [%s] in section [%s] config. Using section as subdir.',
                    html_output_subdir, section
                )
                html_output_subdir = sanitize_string(section)

        return html_output_subdir

    def _generate_top_level_pages(
        self,
        gim_config: Dict,
        output_dir: Path
    ) -> None:
        '''
        Generate top-level pages such as GIM or field schema summaries using configured templates.
        '''
        self.logger.debug('Generating top-level pages using parent output_dir %s', output_dir)

        config_output_plugin = gim_config.get('config_output_plugin', {})
        plugin_config_outer = config_output_plugin.get('plugin', {})
        plugin_top_config = plugin_config_outer.get(self.plugin_name, {})

        for section in ['gim', 'field_schema']:
            self.logger.debug('Processing top-level pages for section %s', section)
            section_cfg = plugin_top_config.get(section, {})

            if not section_cfg:
                self.logger.warning('No plugin configuration found for section %s', section)
                continue

            template_name = section_cfg.get('template')
            if not template_name:
                self.logger.warning('No template specified for top-level section [%s]', section)
                continue

            template = self._load_template(template_name, section)
            if not template:
                self.logger.warning('Unable to load teplate for section %s, skipping', section)
                continue

            self.logger.debug('Top-level page template loaded for section %s', section)
            section_data = gim_config.get(section, {})
            sorted_section_data = {k: section_data[k] for k in sorted(section_data)}

            # Determine sanitized subdir name
            html_output_subdir = self._build_output_path(section, section_cfg)

            self.logger.debug('Using the output subdirectory %s for top-level pages', html_output_subdir)
            html = self._render_template(
                template,
                section,
                {},  # no category_data for top-level pages
                gim_config.get('config', {}),
                extra_context={
                    'categories': sorted_section_data,
                    'html_output_subdir': html_output_subdir,
                    'section_cfg': section_cfg
                }
            )

            if html is None:
                continue

            postprocessor = DocumentPostprocessor()

            # Build the path to the output file destination
            output_filename = section_cfg.get('output_filename', f'{section}.html')
            html_output_subdir = self._build_output_path(section, section_cfg)
            section_output_dir = output_dir / Path ( html_output_subdir )

            try:
                self.logger.debug('Checking path %s', section_output_dir)
                Path(section_output_dir).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                self.logger.error(
                    'Unable to create directory %s, error %s',
                    section_output_dir, e
                )
                raise RuntimeError(
                    f'Failed to create directory {section_output_dir}'
                ) from e

            output_file = section_output_dir / output_filename

            try:
                write_file(output_file, postprocessor.clean(html))
            except OSError as e:
                self.logger.error('Unable to write [%s] due to write error %s', output_file, e)
                continue

    def _generate_category_pages(
        self,
        gim_config: Dict,
        output_dir: Path
    ) -> None:
        '''
        Generate category-specific HTML files based on GIM configuration and templates.
        Output is written to the configured or default 'gim' subdirectory.
        '''
        config_output_plugin = gim_config.get('config_output_plugin', {})
        plugin_outer_config = config_output_plugin.get('plugin', {})
        top_level_cfg = plugin_outer_config.get(self.plugin_name, {})
        section_cfg = top_level_cfg.get('gim', {})
        html_output_subdir = sanitize_string(section_cfg.get('html_output_subdir', 'gim'))
        gim_output_dir = output_dir / html_output_subdir

        try:
            gim_output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info('Writing category pages to %s', gim_output_dir)
        except OSError as e:
            self.logger.critical(
                'Unable to create HTML output directory %s: %s',
                html_output_subdir, e
            )
            raise RuntimeError(
                f'Failed to create output directory [{gim_output_dir}]'
            ) from e

        for category, category_data in gim_config.get('gim', {}).items():
            raw_config = (
                category_data
                .get('meta', {})
                .get('plugin_config', {})
                .get(self.plugin_name, {})
            )

            self.logger.debug('Generatin page for GIM category [%s]', category)

            validated_config = self._validate_category_plugin_config(raw_config, category)
            if not validated_config:
                self.logger.warning(
                    'Invalid config detected for GIM category[%s], skipping',
                    category
                )
                continue

            self.logger.debug('Valid config loaded for GIM category [%s]', category)

            template = self._load_template(validated_config.category_template_filename, category)
            if not template:
                self.logger.warning(
                    'Unable to load template for GIM category [%s], skipping',
                    category
                )
                continue

            # Build the columns that wil be used by the Jinja template to generate
            # subcategory tables for documentation.
            subcat_rows = self._build_subcat_tables(category_data)

            # Build a list of required/recommended/optional fields for the different
            # subcategories and append it to the category data dictionary.
            for subcat_code, subcat in category_data.get('subcategories',{}).items():
                subcat['merged_fields'] = self._merge_field_lists(category_data, subcat_code)

            category_data = self._build_category_data_with_columns(category_data, subcat_rows)

            html = self._render_template(template, category, category_data, gim_config.get('config', {}))
            if html is None:
                continue

            output_file = gim_output_dir / f'{category}.html'

            postprocessor = DocumentPostprocessor()

            try:
                write_file(output_file, postprocessor.clean(html))
            except OSError as e:
                self.logger.error('Unable to write [%s] due to write error %s', output_file, e)
                continue

    def _merge_field_lists(self, category: dict, subcat_code: dict) -> dict[str, list[str]]:
        '''
        This will build a dictionary object with keys that correspond to the field
        status (required, recommended, optional) which contain those fields in a list
        of string values. GIM configuration can define required fields at both the
        category and subcategory level, this function takes the category data and the
        subcategory code to process and builds the field lists by inspecting both the
        parent category and the given subcategory field configuration.

        Args:
            category: Dictionary object containing all category
                configuration data.
            subcat_code: Two-character subcategory code to build
                the list of fields for.

        Returns:
            dict
        '''
        self.logger.debug(
            'Determining required/recommended/optional fields for subcategory %s',
            subcat_code
            )
        merged = {}
        for level in ('required', 'recommended', 'optional'):
            cat_fields = category.get(f'{level}_fields', [])
            subcat_fields = category.get('subcategories', {}).get(subcat_code, {}).get(f'{level}_fields', [])
            merged[level] = sorted(set(cat_fields + subcat_fields))

        return merged

    def _build_category_data_with_columns(
        self,
        category_json: dict,
        table_data: dict
    ) -> dict:
        '''
        Merge table column data into the top-level structure under 'table_rows',
        with each key matching a subcategory code.

        Args:
            category_json: The base category dictionary (already parsed from JSON).
            table_data: A dict mapping subcategory codes to lists of column metadata.

        Returns:
            A new dict with 'table_rows' added at the top level.
        '''
        # Copy the base to avoid mutating the original
        result = category_json.copy()

        for code, columns in table_data.items():
            if code in category_json.get('subcategories', {}):
                # Add the table_rows key if it does not exist
                if not result['subcategories'][code].get('table_rows'):
                    result['subcategories'][code]['table_rows'] = []

                result['subcategories'][code]['table_rows'] = columns
            else:
                # Warn if there was a code mismatch but this should not
                # be possible since the table data was derived from the
                # category dict.
                self.logger.warning(
                    'Table data exists for code %s but this code was '
                    ' not found in the category JSON',
                    code
                    )

        return result

    def _build_subcat_tables(
        self,
        category_config: Dict
    ) -> Dict[str, list[Dict]]:
        '''
        Build the rows that will be used when generating the subcategory tables.

        Args:
            category_config: Dict

        Returns:
            Dict
        '''
        cat_name = category_config.get('name', '**NOT FOUND**')
        cat_code = category_config.get('code', None)
        gim_class = category_config.get('class', '')
        result = {}

        self.logger.debug('Found category %s code %s', cat_name, cat_code)

        for subcat_code, subcat_data in category_config.get('subcategories', {}).items():
            subcat_lines = []
            self.logger.debug('Processing subcategory %s code %s', subcat_data['name'], subcat_code)
            subcat_name = cat_name + '.' + subcat_data['name']
            for event_code, event_data in subcat_data.get('event_type_codes', {}).items():
                self.logger.debug('Found Event %s code %s', event_data['name'], event_code)
                type_code = cat_code + subcat_code + event_code
                subcat_lines.append(
                    {
                        'gim_event_type_code': type_code,
                        'gim_event_class': gim_class,
                        'gim_event_category': cat_name,
                        'gim_event_subcategory': subcat_name,
                        'gim_event_type': event_data['name'],
                        'description': event_data['description']
                    }
                )

            result[subcat_code] = subcat_lines

        return result

    def _generate_field_schema_entity_pages(
        self,
        gim_config: Dict,
        output_dir: Path,
        plugin_config: MadcapHtmlOutputConfig
    ) -> None:
        '''
        Generate entity-specific HTML files based on field_schema configuration and templates.
        Output is written to the configured or default 'field_schema' subdirectory.

        For each "top" entity, composes its attached sub-fields (via applies_to
        on "sub" entities, using gim_schema.sub_fields.expand_sub_fields) into
        a "Sub-fields" table plus the list of sub-entities they came from, so
        the rendered page can link back to each sub-entity's own page. "sub"
        entities carry their applies_to list through unchanged, for rendering
        an "Applies to" list on their own page.

        Entities are rendered independently: one with invalid per-entity
        plugin config, a template that fails to load, a render failure, or a
        write failure is skipped (logged), without aborting the rest.

        Args:
            gim_config: The full loaded GIM config tree.
            output_dir: Base output directory; entity pages are written under
                its 'field_schema' (or configured) subdirectory.
            plugin_config: Validated global plugin config, providing default
                field and sub-field table column orders.
        '''
        config_output_plugin = gim_config.get('config_output_plugin', {})
        plugin_config_outer = config_output_plugin.get('plugin', {})
        top_level_cfg = plugin_config_outer.get(self.plugin_name, {})
        section_cfg = top_level_cfg.get('field_schema', {})
        html_output_subdir = sanitize_string(section_cfg.get('html_output_subdir', 'field_schema'))
        schema_output_dir = output_dir / html_output_subdir
        schema_output_dir.mkdir(parents=True, exist_ok=True)

        subfields_by_parent = expand_sub_fields(gim_config.get('field_schema', {}))

        for entity_name, entity_data in gim_config.get('field_schema', {}).items():
            raw_config = (
                entity_data
                .get('meta', {})
                .get('plugin_config', {})
                .get(self.plugin_name, {})
            )

            validated_config = self._validate_category_plugin_config(raw_config, entity_name)
            if not validated_config:
                continue

            template_name = validated_config.entity_template_filename
            template = self._load_template(template_name, entity_name)
            if not template:
                continue

            column_order = (
                validated_config.field_column_order or
                plugin_config.default_field_columns
            )
            subfield_column_order = (
                validated_config.subfield_column_order or
                plugin_config.default_subfield_columns
            )

            # Since the data used to build tables is being modified we have to remap
            # some keys. Below is a list of key names and updated key names stored in
            # key value pairs.
            column_key_map = {
                'field_suffix': 'field'
            }

            column_keys = [column_key_map.get(col, col) for col in column_order]
            subfield_column_keys = [column_key_map.get(col, col) for col in subfield_column_order]

            self.logger.debug(
                'Rendering entity [%s] with column order [%s]',
                entity_name, column_order, column_keys
            )

            # The fields lists are not usable in their raw form, and must be transformed
            # before being used to generate the documentation HTML. The raw schema data
            # does not store the field name, but instead stores the property suffixes
            # that are applied to the entity name to derive the field name. The format
            # is {ENTITY_NAME} + _ + {FIELD_SUFFIX}, except for "reserved" entities,
            # whose field_suffix values are already the literal field name.
            schema_table_rows = self._build_schema_table_lines(
                entity_name, entity_data.get('entity_type'), entity_data.get('fields', [])
            )
            entity_subfield_rows = subfields_by_parent.get(entity_name, [])
            schema_data = entity_data.copy()
            schema_data['table_rows'] = schema_table_rows
            schema_data['subfield_groups'] = self._group_subfield_rows_by_source(entity_subfield_rows)

            html = self._render_template(
                template,
                entity_name,
                schema_data,
                gim_config.get('config', {}),
                extra_context={
                    'field_column_order': column_keys,
                    'subfield_column_order': subfield_column_keys
                }
            )
            if html is None:
                continue

            output_file = schema_output_dir / f'{entity_name}.html'

            postprocessor = DocumentPostprocessor()

            try:
                write_file(output_file, postprocessor.clean(html))
            except OSError as e:
                self.logger.error(
                    'Unable to write field schema entity [%s] page [%s] due to write error [%s]',
                    entity_name,
                    output_file,
                    e
                )
                continue

            self.logger.debug('Wrote field schema entity [%s] page [%s]', entity_name, output_file)

    def _group_subfield_rows_by_source(self, subfield_rows: list[SubFieldRow]) -> list[dict]:
        '''
        Group composed sub-field rows by their source sub-entity, so each
        source entity's fields can be rendered as its own dropdown table on
        the parent entity's page, rather than one long flat table.

        Args:
            subfield_rows: Composed sub-field rows for one parent entity, as
                produced by gim_schema.sub_fields.expand_sub_fields.

        Returns:
            list of {'source_entity': str, 'rows': list[SubFieldRow]} dicts,
            sorted by source_entity name, each group's rows sorted by field
            name.
        '''
        grouped: dict[str, list[SubFieldRow]] = {}
        for row in subfield_rows:
            grouped.setdefault(row['source_entity'], []).append(row)

        return [
            {
                'source_entity': source_entity,
                'rows': sorted(rows, key=lambda row: row['field'])
            }
            for source_entity, rows in sorted(grouped.items())
        ]

    def _build_schema_table_lines(self, entity_name, entity_type, fields) -> list[dict]:
        '''
        Transforms the base data into a list of rows that can be used when
        generating the field schema page

        Args:
            entity_name: str
            entity_type: str, one of "top", "sub", or "reserved". When "reserved",
                field_suffix values are already the literal field name and are not
                prefixed with the entity name.
            fields: list

        Returns:
            list of dicts representing schema table rows, sorted alphabetically by field name
        '''
        schema_entity_lines = []
        for line in fields:
            if not isinstance(line, dict):
                self.logger.warning('Skipping invalid schema line in [%s]: not a dict: %s', entity_name, line)
                continue

            if not line.get('field_suffix'):
                self.logger.warning('Skipping schema line in [%s]: missing field_suffix: %s', entity_name, line)
                continue

            if entity_type == 'reserved':
                field_name = line['field_suffix']
            else:
                field_name = f"{entity_name}_{line['field_suffix']}"
            schema_entity_lines.append(
                {
                    'field': field_name,
                    'field_type': line['field_type'],
                    'description': line['description'],
                    'example_values': line['example_values']
                }
            )

        return sorted(schema_entity_lines, key=lambda row: row['field'])

    def _regex_replace_filter(self, value: str, pattern: str, repl: str) -> str:
        '''
        Custom Jinja2 filter to apply a regular expression substitution.


        Args:
            value: The input string.
            pattern: The regex pattern to search for.
            repl: The replacement string.

        Returns:
            Modified string with substitutions applied.
        '''
        if not isinstance(value, str):
            value = str(value or '')
        return re.sub(pattern, repl, value)
