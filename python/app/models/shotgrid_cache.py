from __future__ import annotations

import json

import sgtk

from .context import Context


class ShotGridCache:
    sg_cache: dict
    fields: dict[str, list[str]]

    def __init__(self, settings):
        app = sgtk.platform.current_bundle()
        self.connection = app.shotgun
        self.logger = app.logger
        self.context = app.context

        self.settings = settings

        self.sg_cache = {}
        self.fields = {}

    def load(self):
        self.logger.info("Loading ShotGrid cache...")
        project_id = self.context.project["id"]
        filters = [
            [
                "id",
                "is",
                project_id,
            ]
        ]

        self.find_raw("Project", filters)

        self.find_raw(
            self.settings.footage_format_entity,
            [["project", "is", self.context.project]],
        )

        filters = [
            [
                "project",
                "is",
                {"type": "Project", "id": project_id},
            ],
            [
                self.settings.version_status_field,
                "is",
                self.settings.version_delivery_status,
            ],
        ]

        versions = self.find_raw(
            "Version",
            filters,
        )
        self.logger.info("Found %s versions", len(versions))

        shot_ids = {version["entity"]["id"] for version in versions}

        for shot_id in shot_ids:
            self.find_raw(
                "Shot",
                [["id", "is", shot_id]],
            )
        self.logger.info("Found %s shots", len(shot_ids))

        for version in versions:
            publishes = version.get("published_files", [])

            if len(publishes) == 0:
                continue

            filters = [
                ["id", "is", publishes[0]["id"]],
            ]

            self.find_raw(
                "PublishedFile",
                filters,
            )

    def process(self):
        for entity_type, data in self.sg_cache.items():
            entities = data.get("raw_entities", [])

            # Process entity overrides
            processed_entities = self._process_entity_overrides(
                entity_type, entities
            )

            self._nested_set(
                self.sg_cache, [entity_type, "entities"], processed_entities
            )
        self.logger.info("Processed all cached ShotGrid data.")

    def find_raw(self, entity_type: str, filters: list) -> list[dict] | None:
        if entity_type in self.fields:
            fields = self.fields[entity_type]
        else:
            fields = list(
                self.connection.schema_field_read(entity_type).keys()
            )
            self.fields[entity_type] = fields

        entities = self.connection.find(entity_type, filters, fields)

        if entities is None:
            return None

        raw_entities = self.sg_cache.get(entity_type, {}).get(
            "raw_entities", []
        )
        merged = {d["id"]: d for d in raw_entities + entities}
        raw_entities = list(merged.values())

        self._nested_set(
            self.sg_cache, [entity_type, "raw_entities"], raw_entities
        )

        return entities

    def find(
        self, entity_type: str, filters: list, ignore_cache: bool = False
    ) -> list[dict] | None:
        query = json.dumps(filters)
        cached_ids = (
            self.sg_cache.get(entity_type, {})
            .get("query", {})
            .get(query, None)
        )
        if cached_ids is not None and not ignore_cache:
            return [
                entity
                for entity in self.sg_cache[entity_type]["entities"]
                if entity["id"] in cached_ids
            ]

        entities = self.find_raw(entity_type, filters)

        if entities is None:
            return None

        # Process entity overrides
        entities = self._process_entity_overrides(entity_type, entities)

        processed_entities = self.sg_cache.get(entity_type, {}).get(
            "entities", []
        )
        merged = {d["id"]: d for d in processed_entities + entities}
        processed_entities = list(merged.values())

        self._nested_set(
            self.sg_cache, [entity_type, "entities"], processed_entities
        )

        self.logger.info("Found %s %ss", len(entities), entity_type)
        return entities

    def find_one(self, entity_type: str, filters: list):
        entities = self.find(entity_type, filters)

        if entities is not None and len(entities):
            return entities[0]

        return None

    def get_raw(self, entity_type: str):
        return self.sg_cache.get(entity_type, {}).get("raw_entities", [])

    def get(self, entity_type: str):
        return self.sg_cache.get(entity_type, {}).get("entities", [])

    def _process_entity_overrides(
        self, entity_type: str, entities: dict | list
    ) -> dict | list:
        """
        Apply the version overrides from the configuration to ShotGrid loaded data

        Args:
            entity_type: The type of entity to look for
            entities: A dict or list of dicts
        """
        return_type = type(entities)
        if isinstance(entities, dict):
            entities = [entities]

        overrides = self.settings.get_version_overrides(entity_type)

        if len(overrides) == 0:
            if return_type is dict:
                return entities[0]
            return entities

        for i, entity in enumerate(entities):
            self.logger.info(
                "Applying %s overrides to a %s.", len(overrides), entity_type
            )
            for override in overrides:
                context = Context(cache=self, entity=entity)
                entities[i] = override.process(entity, context)

        if return_type is dict:
            return entities[0]
        return entities

    @staticmethod
    def _nested_set(dic, keys, value):
        for key in keys[:-1]:
            dic = dic.setdefault(key, {})
        dic[keys[-1]] = value
