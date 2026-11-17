"""Plugin generating a per-event-type, per-field GIM field-mapping CSV."""

import csv
import fnmatch
import io
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from pydantic import BaseModel

from base_output import OutputPlugin
from gim_schema.sub_fields import expand_sub_fields
from utils.file import write_file

# Strictest first: lower rank means stricter, and is used both to sort CSV
# rows (required rows before recommended/optional) and to detect a
# subcategory illegally loosening a category-level requirement.
STATUS_RANK = {status: rank for rank, status in enumerate(("required", "recommended", "optional"))}


class FieldMetadata(TypedDict):
    """Field metadata joined from a field_schema entry."""

    field_type: str
    description: str
    example_values: str


CSV_HEADER = [
    "gim_event_type_code",
    "gim_event_class",
    "gim_event_category",
    "gim_event_subcategory",
    "gim_event_type",
    "Field Status",
    "Field Name",
    "Field Description",
    "Field Data Type",
    "Field Example",
]


class FieldMappingCSVOutputConfig(BaseModel):
    """Global configuration for FieldMappingCSVOutput."""

    output_filename: str = "gim_field_mapping.csv"
    enabled: bool = True
    unchecked_fields: list[str] = []


class FieldMappingCSVOutput(OutputPlugin[FieldMappingCSVOutputConfig]):  # type: ignore[no-untyped-call]
    """Generate a per-event-type, per-field GIM field-mapping CSV.

    Cross-references every GIM event type against the fields that populate
    it, joined against field_schema metadata.
    """

    enabled_by_default = True
    config_schema = FieldMappingCSVOutputConfig

    def __init__(self) -> None:
        """Initialize the plugin and its logger."""
        super().__init__()  # type: ignore[no-untyped-call]
        plugin_name = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        self.logger = logging.getLogger(plugin_name)

    def generate(
        self,
        gim_config: dict[str, Any],
        output_dir: Path,
        plugin_config: FieldMappingCSVOutputConfig | None = None,
    ) -> None:
        """Generate the field-mapping CSV output file.

        Args:
            gim_config: The full loaded GIM config tree.
            output_dir: Directory to write the output file to.
            plugin_config: Validated instance of this plugin's global config.

        Raises:
            ValueError: If gim_config is missing required data, or a category
                references a field with no field_schema match and no
                unchecked_fields exemption.
            OSError: If the output file cannot be written.
        """
        self.logger.debug("Plugin initialized, generating Field Mapping CSV output")

        if isinstance(plugin_config, FieldMappingCSVOutputConfig):
            self.logger.info("Validated plugin config provided")
        else:
            self.logger.warning("Plugin config is missing or invalid; using default values.")
            plugin_config = FieldMappingCSVOutputConfig()

        output_file = output_dir / plugin_config.output_filename

        field_schema_map = self._build_field_schema_map(gim_config)
        unchecked_fields = set(plugin_config.unchecked_fields)

        if "gim" not in gim_config or not isinstance(gim_config["gim"], dict):
            error_msg = 'Missing or invalid top-level "gim" key in gim_config; expected dictionary.'
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        rows = []
        for category_name, category in gim_config["gim"].items():
            rows.extend(
                self._build_category_rows(category_name, category, field_schema_map, unchecked_fields)
            )

        rows.sort(key=lambda row: (row[0], STATUS_RANK[row[5]], row[6]))

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

        write_file(output_file, buffer.getvalue())

        self.logger.info("Saved CSV to file %s", output_file)
        self.logger.debug("Plugin processing completed.")

    def _build_field_schema_map(self, gim_config: dict[str, Any]) -> dict[str, FieldMetadata]:
        """Flatten field_schema entities into a lookup keyed by full field name.

        "top" entities contribute ``{entity_name}_{field_suffix}`` names.
        "reserved" entities contribute their literal ``field_suffix`` as the
        field name (unprefixed). "sub" entities do not contribute their own
        bare names directly; instead, their fields are composed onto every
        parent entity named in their ``applies_to`` list (e.g. ``hash``'s
        fields become ``file_hash_md5``, ``process_hash_md5``, and so on),
        via expand_sub_fields.

        Args:
            gim_config: The full loaded GIM config tree.

        Returns:
            Mapping of full field name to field metadata (``field_type``,
            ``description``, ``example_values``).

        Raises:
            ValueError: If the top-level "field_schema" key is missing or
                invalid, or the same field is defined more than once.
        """
        if "field_schema" not in gim_config or not isinstance(gim_config["field_schema"], dict):
            error_msg = 'Missing or invalid top-level "field_schema" key in gim_config; expected dictionary.'
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        field_schema: dict[str, Any] = gim_config["field_schema"]
        field_schema_map: dict[str, FieldMetadata] = {}

        for entity_name, entity_data in field_schema.items():
            entity_type = entity_data.get("entity_type")
            if entity_type == "sub":
                continue
            for field in entity_data.get("fields", []):
                field_name = (
                    field["field_suffix"]
                    if entity_type == "reserved"
                    else f"{entity_name}_{field['field_suffix']}"
                )
                self._register_field_schema_entry(field_schema_map, field_name, field)

        for composed_rows in expand_sub_fields(field_schema).values():
            for row in composed_rows:
                self._register_field_schema_entry(field_schema_map, row["field"], row)

        return field_schema_map

    def _register_field_schema_entry(
        self,
        field_schema_map: dict[str, FieldMetadata],
        field_name: str,
        field: Mapping[str, Any],
    ) -> None:
        """Add one field's metadata to field_schema_map, rejecting duplicate names.

        Args:
            field_schema_map: The lookup being built; mutated in place.
            field_name: The full field name to register.
            field: A field_schema field entry or composed sub-field row (either
                a plain dict or a SubFieldRow TypedDict), providing field_type,
                description, and example_values.

        Raises:
            ValueError: If field_name is already present in field_schema_map.
        """
        if field_name in field_schema_map:
            error_msg = f'Field "{field_name}" is defined more than once in field_schema.'
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        field_schema_map[field_name] = {
            "field_type": field["field_type"],
            "description": field["description"],
            "example_values": field.get("example_values") or "",
        }

    def _build_category_rows(
        self,
        category_name: str,
        category: dict[str, Any],
        field_schema_map: dict[str, FieldMetadata],
        unchecked_fields: set[str],
    ) -> list[list[str]]:
        """Build all CSV rows for a single GIM category.

        Args:
            category_name: The category's key in gim_config["gim"].
            category: The category's data dictionary.
            field_schema_map: Flattened field_schema lookup from _build_field_schema_map.
            unchecked_fields: Field names exempt from the field_schema-match requirement.

        Returns:
            List of CSV row value lists.

        Raises:
            ValueError: If a subcategory has no event_type_codes, a field is
                listed in more than one tier, a subcategory loosens a
                category-level requirement, a field has no field_schema match
                and no unchecked_fields exemption, a wildcard field pattern is
                used at "required" status, or a wildcard field pattern matches
                no field_schema entries.
        """
        cat_code = category["code"]
        display_name = category["name"]
        category_field_status = self._build_field_status_map(category, f'category "{category_name}"')

        rows: list[list[str]] = []
        for subcat_code, subcat in category["subcategories"].items():
            rows.extend(
                self._build_subcategory_rows(
                    category_name,
                    display_name,
                    cat_code,
                    subcat_code,
                    subcat,
                    category_field_status,
                    field_schema_map,
                    unchecked_fields,
                )
            )

        return rows

    def _build_subcategory_rows(
        self,
        category_name: str,
        display_name: str,
        cat_code: str,
        subcat_code: str,
        subcat: dict[str, Any],
        category_field_status: dict[str, str],
        field_schema_map: dict[str, FieldMetadata],
        unchecked_fields: set[str],
    ) -> list[list[str]]:
        """Build all CSV rows for a single subcategory's event types.

        Each field entry is resolved via _resolve_field_names before its row(s)
        are built: a literal field name produces exactly one row per event
        type, while a wildcard pattern (e.g. "file_hash_*") expands to one row
        per matching field_schema entry.

        Args:
            category_name: The category's key in gim_config["gim"].
            display_name: The category's display name.
            cat_code: The category's 2-digit GIM code.
            subcat_code: The subcategory's 2-digit GIM code.
            subcat: The subcategory's data dictionary.
            category_field_status: Field name to status map for the category.
            field_schema_map: Flattened field_schema lookup from _build_field_schema_map.
            unchecked_fields: Field names exempt from the field_schema-match requirement.

        Returns:
            List of CSV row value lists, one per (event type, resolved field
            name) pair.

        Raises:
            ValueError: If the subcategory has no event_type_codes, a field is
                listed in more than one tier, the subcategory loosens a
                category-level requirement, a field has no field_schema match
                and no unchecked_fields exemption, a wildcard field pattern is
                used at "required" status, or a wildcard field pattern matches
                no field_schema entries.
        """
        subcat_name = subcat["name"]
        full_subcat_name = f"{display_name}.{subcat_name}"
        entry_class = subcat.get("class", "")

        if not subcat.get("event_type_codes"):
            error_msg = f'Subcategory "{full_subcat_name}" is missing event_type_codes or has no entries.'
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        subcat_field_status = self._build_field_status_map(subcat, f'subcategory "{full_subcat_name}"')
        field_rows = self._merge_field_status(
            category_field_status, subcat_field_status, category_name, full_subcat_name
        )

        rows: list[list[str]] = []
        for type_code, event_type_info in subcat["event_type_codes"].items():
            event_type_code = f"{cat_code}{subcat_code}{type_code}"
            event_type_name = event_type_info["name"]

            for field_name, status in field_rows:
                for resolved_field_name in self._resolve_field_names(
                    field_name, status, field_schema_map, full_subcat_name
                ):
                    rows.append(
                        self._build_row(
                            event_type_code,
                            entry_class,
                            display_name,
                            full_subcat_name,
                            event_type_name,
                            status,
                            resolved_field_name,
                            field_schema_map,
                            unchecked_fields,
                        )
                    )

        return rows

    def _resolve_field_names(
        self,
        field_name: str,
        status: str,
        field_schema_map: dict[str, FieldMetadata],
        full_subcat_name: str,
    ) -> list[str]:
        """Expand a wildcard field name into its concrete field_schema matches.

        A literal field name (no "*") resolves to itself. A wildcard pattern
        (e.g. "file_hash_*") is expanded via fnmatch against field_schema_map's
        keys, per the sdm-build skill's rule that sub-field group wildcards are
        permitted only for "recommended"/"optional" fields, never "required".

        Args:
            field_name: A literal field name or an fnmatch-style wildcard
                pattern.
            status: The field's tier ("required"/"recommended"/"optional")
                for this row.
            field_schema_map: Flattened field_schema lookup from
                _build_field_schema_map.
            full_subcat_name: Fully qualified subcategory name, for error
                messages.

        Returns:
            List of one or more concrete field names to emit rows for.

        Raises:
            ValueError: If field_name is a wildcard used at "required" status,
                or a wildcard that matches no field_schema entries.
        """
        if "*" not in field_name:
            return [field_name]

        if status == "required":
            error_msg = (
                f'Field "{field_name}" referenced by subcategory "{full_subcat_name}" '
                'is a wildcard pattern, which is only allowed for "recommended" or '
                '"optional" fields, never "required".'
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        matches = sorted(fnmatch.filter(field_schema_map.keys(), field_name))
        if not matches:
            error_msg = (
                f'Wildcard field "{field_name}" referenced by subcategory '
                f'"{full_subcat_name}" matched no field_schema entries.'
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        return matches

    def _build_row(
        self,
        event_type_code: str,
        entry_class: str,
        display_name: str,
        full_subcat_name: str,
        event_type_name: str,
        status: str,
        field_name: str,
        field_schema_map: dict[str, FieldMetadata],
        unchecked_fields: set[str],
    ) -> list[str]:
        """Build a single CSV row for one (event type, field) pair.

        Args:
            event_type_code: The 6-digit GIM event type code.
            entry_class: The subcategory's class, or empty string if unset.
            display_name: The category's display name.
            full_subcat_name: Fully qualified subcategory name.
            event_type_name: The event type's display name.
            status: One of "required"/"recommended"/"optional".
            field_name: The full field name.
            field_schema_map: Flattened field_schema lookup from _build_field_schema_map.
            unchecked_fields: Field names exempt from the field_schema-match requirement.

        Returns:
            A single CSV row as a list of column values.

        Raises:
            ValueError: If field_name has no field_schema match and is not in
                unchecked_fields.
        """
        metadata = field_schema_map.get(field_name)
        if metadata is None:
            if field_name in unchecked_fields:
                metadata = {"description": "", "field_type": "", "example_values": ""}
            else:
                error_msg = (
                    f'Field "{field_name}" referenced by subcategory '
                    f'"{full_subcat_name}" has no matching field_schema entry.'
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        return [
            event_type_code,
            entry_class,
            display_name,
            full_subcat_name,
            event_type_name,
            status,
            field_name,
            metadata["description"],
            metadata["field_type"],
            metadata["example_values"],
        ]

    def _build_field_status_map(self, entry: dict[str, Any], context: str) -> dict[str, str]:
        """Build a field-name to status map from an entry's tier field lists.

        Args:
            entry: A category or subcategory dictionary with required_fields/
                recommended_fields/optional_fields keys.
            context: Human-readable description of the entry, for error messages.

        Returns:
            Mapping of field name to one of "required"/"recommended"/"optional".

        Raises:
            ValueError: If the same field name appears in more than one tier.
        """
        field_status: dict[str, str] = {}
        for status in ("required", "recommended", "optional"):
            for field_name in entry.get(f"{status}_fields", []) or []:
                if field_name in field_status:
                    error_msg = (
                        f'Field "{field_name}" is listed in more than one tier '
                        f"({field_status[field_name]} and {status}) for {context}."
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                field_status[field_name] = status

        return field_status

    def _merge_field_status(
        self,
        category_field_status: dict[str, str],
        subcat_field_status: dict[str, str],
        category_name: str,
        full_subcat_name: str,
    ) -> list[tuple[str, str]]:
        """Merge category- and subcategory-level field status maps.

        Args:
            category_field_status: Field name to status map for the category.
            subcat_field_status: Field name to status map for the subcategory.
            category_name: Category key, for error messages.
            full_subcat_name: Fully qualified subcategory name, for error messages.

        Returns:
            List of (field_name, status) pairs to emit as rows.

        Raises:
            ValueError: If the subcategory status is looser than the category status
                for the same field.
        """
        field_rows: list[tuple[str, str]] = []
        all_field_names = set(category_field_status) | set(subcat_field_status)

        for field_name in all_field_names:
            has_cat = field_name in category_field_status
            has_sub = field_name in subcat_field_status

            if has_cat and has_sub:
                cat_status = category_field_status[field_name]
                sub_status = subcat_field_status[field_name]
                cat_rank = STATUS_RANK[cat_status]
                sub_rank = STATUS_RANK[sub_status]

                if sub_rank > cat_rank:
                    error_msg = (
                        f'Field "{field_name}" is "{cat_status}" for category '
                        f'"{category_name}" but only "{sub_status}" for subcategory '
                        f'"{full_subcat_name}" - a subcategory cannot loosen a '
                        "category-level requirement."
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                elif sub_rank == cat_rank:
                    field_rows.append((field_name, cat_status))
                else:
                    field_rows.append((field_name, cat_status))
                    field_rows.append((field_name, sub_status))
            elif has_cat:
                field_rows.append((field_name, category_field_status[field_name]))
            else:
                field_rows.append((field_name, subcat_field_status[field_name]))

        return field_rows
