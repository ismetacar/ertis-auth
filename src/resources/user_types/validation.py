import re

import fastjsonschema

from src.utils.errors import ErtisError

SCHEMA_NAME_PATTERN = "^[A-Za-z0-9_]{3,100}$"

CREATE_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'additionalProperties': True,
    'properties': {
        'name': {
            'type': 'string',
            'pattern': SCHEMA_NAME_PATTERN
        },
        'schema': {
            "type": "object",
            "properties": {
                "properties": {
                    "name": "schema properties",
                    "type": "object",
                    "minProperties": 1
                }
            }
        }
    },
    'required': ['name', 'schema']
}

UPDATE_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'additionalProperties': True,
    'properties': {
        'name': {
            'type': 'string',
            'pattern': SCHEMA_NAME_PATTERN
        },
        'properties': {
            "type": "object",
            "properties": {
                "properties": {
                    "type": "object",
                    "minProperties": 1
                }
            }
        }
    },
    'required': []
}

#: import requests
#: response = requests.get('http://json-schema.org/schema#')
#: VALID_KEYWORDS = list(response.json().get('properties').keys())
VALID_KEYWORDS = [
    'if',
    '$id',
    'not',
    '$ref',
    'then',
    'else',
    'type',
    'enum',
    'allOf',
    'title',
    'anyOf',
    'oneOf',
    'const',
    'items',
    'format',
    '$schema',
    'maximum',
    'default',
    'minimum',
    'pattern',
    'maxItems',
    'examples',
    'contains',
    'minItems',
    'minLength',
    '$comment',
    'readOnly',
    'required',
    'maxLength',
    'definitions',
    'multipleOf',
    'properties',
    'description',
    'uniqueItems',
    'dependencies',
    'minProperties',
    'propertyNames',
    'maxProperties',
    'additionalItems',
    'contentEncoding',
    'exclusiveMaximum',
    'exclusiveMinimum',
    'contentMediaType',
    'patternProperties',
    'additionalProperties'
]

BASIC_TYPES = [
    "string",
    "number",
    "integer",
    "boolean",
    "null",
    "object"
]

KEYWORDS_BASED_ON_TYPES = {
    "string": [
        "enum",
        "const",
        "format",
        "pattern",
        "maxLength",
        "minLength",
        "description"
    ],
    "number": [
        "enum",
        "const",
        "maximum",
        "minimum",
        "description"
    ],
    "integer": [
        "enum",
        "const",
        "maximum",
        "minimum",
        "description"
    ],
    "boolean": [
        "enum",
        "const",
        "description"
    ],
    "null": [
        "description"
    ],
    "object": [
        "properties",
        "required"
    ]
}


def ensure_keys_of_schema_properties_is_in_valid_keywords(properties):
    for key, val in properties.items():
        if key not in VALID_KEYWORDS:
            raise ErtisError(
                err_code="errors.invalidKeyword",
                err_msg="Invalid keyword",
                status_code=400,
                context={
                    "given_keyword": key,
                    "valid_keywords": VALID_KEYWORDS
                }
            )

        elif key == 'properties':

            if type(val) != dict:
                raise ErtisError(
                    err_code="errors.invalidKeyword",
                    err_msg="Properties must be a dictionary",
                    status_code=400,
                    context={
                        "given_properties": val
                    }
                )

            for _key, _val in val.items():
                ensure_keys_of_schema_properties_is_in_valid_keywords(_val)


def ensure_required_fields_are_defined(schema):
    required_properties = schema.get('required', [])
    defined_property_names = list(schema.get('properties', {}).keys())

    for property_name in required_properties:
        if property_name in defined_property_names:
            continue

        raise ErtisError(
            err_code="errors.requiredPropertiesMustBeDefined",
            err_msg="Required properties must be defined.",
            status_code=400,
            context={
                "non_defined_property": property_name,
                "defined_required_properties": required_properties
            }
        )


def check_property_type(property_name, keywords):
    _type = keywords.get('type')

    if not _type:
        raise ErtisError(
            err_code="errors.propertyTypeMustBeGiven",
            err_msg="Property type must be given.",
            status_code=400,
            context={
                "property_name": property_name,
                "property": keywords,
                "primitive_types": BASIC_TYPES
            }
        )

    if _type not in BASIC_TYPES:
        raise ErtisError(
            err_code="errors.propertyTypeMustBePrimitive",
            err_msg="Property type must be primitive.",
            status_code=400,
            context={
                "property_name": property_name,
                "property": keywords,
                "primitive_types": BASIC_TYPES
            }
        )


PROPERTY_NAME_PATTERN = '^[A-Za-z0-9-_]{1,30}$'
PROPERTY_NAME_REGEX = re.compile(PROPERTY_NAME_PATTERN)


def check_property_name(property_name):
    if not PROPERTY_NAME_REGEX.match(property_name):
        raise ErtisError(
            err_code="errors.invalidPropertyName",
            err_msg="Property name should match: " + PROPERTY_NAME_PATTERN,
            status_code=400,
            context={
                "property_name": property_name
            }
        )


def check_keywords_by_type(schema):
    properties = schema.get('properties', {})
    for property_name, keywords in properties.items():

        check_property_name(property_name)
        check_property_type(property_name, keywords)
        _type = keywords['type']

        valid_keywords = KEYWORDS_BASED_ON_TYPES[_type]
        for keyword, value in keywords.items():
            if keyword == 'type':
                continue

            if keyword not in valid_keywords:
                raise ErtisError(
                    err_code="errors.invalidKeywordForPropertyType",
                    err_msg="Given <{}> keyword is not allowed for this property type.".format(keyword),
                    status_code=400,
                    context={
                        "property_name": property_name,
                        "property": keywords,
                        "valid_keywords_for_{}_type".format(_type): valid_keywords
                    }
                )


FORMAT_REGEXES = fastjsonschema.CodeGeneratorDraft07.FORMAT_REGEXS
_FORMAT_REGEXES = list(FORMAT_REGEXES)


def check_value_of_format_keyword(schema):
    for property_name, keywords in schema.get('properties', {}).items():
        property_type = keywords.get('type')
        if property_type != 'string':
            continue

        _format = keywords.get('format')
        if not _format:
            continue

        if _format not in _FORMAT_REGEXES:
            raise ErtisError(
                err_code="errors.invalidStringFormat",
                err_msg="Invalid string format.",
                status_code=400,
                context={
                    "property_name": property_name,
                    "property": keywords,
                    "allowed_string_formats": _FORMAT_REGEXES
                }
            )


def validate(resource):
    schema = resource.get('schema')

    if not schema:
        raise ErtisError(
            err_code="errors.resourceMustContainSchema",
            err_msg="Resource must contain schema.",
            status_code=400,
            context={
                "given_resource": resource
            }
        )

    ensure_keys_of_schema_properties_is_in_valid_keywords(schema)
    ensure_required_fields_are_defined(schema)
    check_keywords_by_type(schema)
    check_value_of_format_keyword(schema)

    return resource
