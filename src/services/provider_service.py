import copy
import datetime

from bson import ObjectId
from slugify import slugify

from src.resources.generic import query
from src.resources.providers.resource import prepare_properties, dot_to_json, map_values_by_mapping, find_provider, \
    pop_non_updatable_fields, update_provider_with_body, remove_provider
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import maybe_object_id


class ProviderService(object):
    def __init__(self, db, user_type_service, user_service, event_service):
        self.db = db
        self.user_type_service = user_type_service
        self.user_service = user_service
        self.event_service = event_service

    async def get_provider_by_slug(self, slug, membership_id):
        exists_provider = await self.db.providers.find_one({
            'slug': slug,
            'membership_id': membership_id
        })

        if not exists_provider:
            raise ErtisError(
                err_msg="Provider not found by given slug: <{}>".format(slug),
                err_code="errors.providerNotFound",
                status_code=404
            )

        return exists_provider

    async def check_user(self, user):
        return await self.db.users.find_one({
            'email': user['email'],
            'membership_id': user['membership_id']
        })

    async def update_user(self, exists_user, exists_provider, token, provided_user):
        providers = exists_user.get('providers', [])

        if not providers:
            providers.append({
                'provider': exists_provider['slug'],
                'token': token,
                'user_id': provided_user['user_id']
            })

        else:
            for provider in providers:
                if provider['slug'] != exists_provider['slug']:
                    continue
                provider.update({
                    'provider_slug': exists_provider['slug'],
                    'provider_type': exists_provider['type'],
                    'token': token,
                    'user_id': provided_user['user_id']
                })

        await self.db.users.update_one({
            '_id': maybe_object_id(exists_user['_id']),
            'membership_id': exists_user['membership_id']
        }, {
            '$set': {
                'providers': providers
            }
        })

        exists_user['providers'] = providers
        return exists_user

    async def create_user(self, user, exists_provider, token):
        user_type = await self.user_type_service.get_user_type(user['membership_id'])
        schema = user_type.get('schema', {})
        properties = schema.get('properties', {})
        prepared_properties = prepare_properties(properties)
        mapping = exists_provider.get('mapping', {})
        mapping = dot_to_json(mapping)
        mapped_fields = map_values_by_mapping(mapping, prepared_properties, user)

        user.update(mapped_fields)
        user['providers'] = [{
            'provider': exists_provider['slug'],
            'token': token,
            'user_id': user['user_id']
        }]

        user.pop('user_id', None)
        user.pop('name', None)
        user.pop('picture', None)
        user.pop('locale', None)

        created_user = await self.user_service.create_user(
            user, user['membership_id'],
            {'name': exists_provider['default_creator_name'], 'membership_id': user['membership_id']}, self.user_type_service, self.event_service, creator='ERTIS')
        return created_user

    async def create_provider(self, resource, utilizer):
        resource['membership_id'] = utilizer['membership_id']
        resource['_id'] = ObjectId()
        resource['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': utilizer.get('username', utilizer.get('name'))
        }

        resource['slug'] = slugify(resource['name'])

        default_role = resource.get('default_role')
        exists_role = await self.db.roles.find_one({
            "slug": default_role,
            "membership_id": utilizer['membership_id']
        })

        if not exists_role:
            raise ErtisError(
                err_code="errors.roleNotFound",
                err_msg="Role not found by given slug: <{}>".format(default_role),
                status_code=400
            )

        exist_provider = await self.db.providers.find_one({
            'slug': resource['slug'],
            'membership_id': utilizer['membership_id']
        })

        if exist_provider:
            raise ErtisError(
                err_msg="Provider already exists in db with given generated slug: <{}>".format(resource['slug']),
                err_code="errors.resourceAlreadyExists",
                status_code=409
            )

        await self.db.providers.insert_one(resource)
        await self.event_service.on_event((Event(**{
            'document': resource,
            'prior': {},
            'utilizer': utilizer,
            'type': 'ProviderCreatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        return resource

    async def get_provider(self, resource_id, user):
        return await find_provider(self.db, user['membership_id'], resource_id)

    async def update_provider(self, provider_id, data, utilizer, event_service):
        resource = await find_provider(self.db, utilizer['membership_id'], provider_id)

        _resource = copy.deepcopy(resource)

        provided_body = pop_non_updatable_fields(data)
        resource.update(provided_body)
        if resource == _resource:
            raise ErtisError(
                err_msg="Identical document error",
                err_code="errors.identicalDocument",
                status_code=409
            )

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_body['sys'] = resource['sys']
        updated_provider = await update_provider_with_body(self.db, provider_id, utilizer['membership_id'], provided_body)

        _resource['_id'] = str(_resource['_id'])
        updated_provider['_id'] = str(updated_provider['_id'])

        await event_service.on_event((Event(**{
            'document': updated_provider,
            'prior': _resource,
            'utilizer': utilizer,
            'type': 'ProviderUpdatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        return updated_provider

    async def delete_provider(self, provider_id, utilizer, event_service):
        provider = await find_provider(self.db, utilizer['membership_id'], provider_id)
        await remove_provider(self.db, utilizer['membership_id'], provider_id)

        provider['_id'] = str(provider['_id'])
        await event_service.on_event((Event(**{
            'document': {},
            'prior': provider,
            'utilizer': utilizer,
            'type': 'ProviderDeletedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

    async def query_providers(self, membership_id, where, select, limit, skip, sort):
        return await query(self.db, membership_id, where, select, limit, skip, sort, 'providers')
