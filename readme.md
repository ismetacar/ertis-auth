# Ertis Auth
v2.0.0

Ertis auth is a next generation and generic auth service.

You can manage your users, applications, roles and more.

## Tokens
There are two types of token. Basic and Bearer tokens. 

Bearer tokens are based on [JWT](http://jwt.io).

Basic tokens generating by application id and secret.

## Resources
User types, users, applications, roles. 

**User Types:**
- Manage your user model dynamically.
- Set as required fields you want.
- All primitive types are supported.  

**Users:**
- Users, generating with default user fields (samples as below) and defined fields on user type.
- Users can get a token and access to me and other api endpoints.
- Users can create and modify other resources by role.
 
**Applications:**
- Applications can manage other resources like users by role. 
- Server side request optimization is benefit.

**Roles:**
- Define roles easily with role based access control. (Samples as below)
- Apply role to user and applications.

**Events**
- Get all action records as json from rest api.
- Get detail of an event. 

**Active Tokens:**
- Get all active tokens by user.
- Revoke all of them, as you wish.

## Rest API

All api endpoints developed by rest and http standards.


 | Endpoint Path                                                      |       Allowed Methods         |
 |:-------------------------------------------------------------------|-------------------------------|
 | /api/v1/healthcheck                                                |              GET              |
 | /api/v1/generate-token                                             |              POST             |
 | /api/v1/refresh-token                                              |              POST             |
 | /api/v1/verify-token                                               |              POST             |
 | /api/v1/revoke-token                                               |              POST             |
 | /api/v1/reset-password                                             |              POST             |
 | /api/v1/set-password                                               |              POST             |
 | /api/v1/change-password                                            |              POST             |
 | /api/v1/me                                                         |              GET              |
 | /api/v1/memberships/<membership_id>/user-types                     |              POST             |
 | /api/v1/memberships/<membership_id>/get-user-type                  |              GET              |
 | /api/v1/memberships/<membership_id>/user-types/<user_type_id>      |              GET              |
 | /api/v1/memberships/<membership_id>/user-types/<user_type_id>      |              PUT,GET          |
 | /api/v1/memberships/<membership_id>/users                          |              POST             |
 | /api/v1/memberships/<membership_id>/users/<user_id>                |              GET              |
 | /api/v1/memberships/<membership_id>/users/<user_id>                |              PUT,GET          |
 | /api/v1/memberships/<membership_id>/users/<user_id>                |              PUT,GET,DELETE   |
 | /api/v1/memberships/<membership_id>/users/_query                   |              POST             |
 | /api/v1/memberships/<membership_id>/applications                   |              POST             |
 | /api/v1/memberships/<membership_id>/applications/<application_id>  |              GET              |
 | /api/v1/memberships/<membership_id>/applications/<application_id>  |              PUT,GET          |
 | /api/v1/memberships/<membership_id>/applications/<application_id>  |              PUT,GET,DELETE   |
 | /api/v1/memberships/<membership_id>/applications/_query            |              POST             |
 | /api/v1/memberships/<membership_id>/roles                          |              POST             |
 | /api/v1/memberships/<membership_id>/roles/<role_id>                |              GET              |
 | /api/v1/memberships/<membership_id>/roles/<role_id>                |              PUT,GET          |
 | /api/v1/memberships/<membership_id>/roles/<role_id>                |              PUT,GET,DELETE   |
 | /api/v1/memberships/<membership_id>/roles/_query                   |              POST             |
 | /api/v1/memberships/<membership_id>/events/<event_id>              |              GET              |
 | /api/v1/memberships/<membership_id>/events/_query                  |              POST             |
 | /api/v1/api-map                                                    |              GET              |
 | /api/v1/get-app-version                                            |              GET              |
 | /api/v1/memberships/<membership_id>/providers                      |              POST             |
 | /api/v1/memberships/<membership_id>/providers/<provider_id>        |              GET              |
 | /api/v1/memberships/<membership_id>/providers/<provider_id>        |              GET,PUT          |
 | /api/v1/memberships/<membership_id>/providers/<provider_id>        |              GET,PUT,DELETE   |
 | /api/v1/memberships/<membership_id>/providers/_query               |              POST             |
 | /api/v1/sign-in/<provider_slug>                                    |              GET              |
 
## Dockerized App
- Working with mongodb.
- Just docker-compose up.
- Docker compose with mongo and ertis auth.
- Setup db first -> migrate db easily. 
>[Go to setup step](https://pypi.org/project/ertis-auth-migrate/)
> (Ertis Auth Migrate pypi package)

### Up
```bash
$ docker run -p 8888:8888 -d --env-file .env ertis_auth
```

Note: All values in the configuration file can be overridden by environment variables. 
Environment variables must be defined with the AUTH_ prefix -i.e see .env file- on when they are defined.

 > Ertis auth have a public docker [image](https://hub.docker.com/repository/docker/ismetacar/ertis_auth/general) on docker hub.
## API Documentation
- Strong api documentation with samples
> [Postman Collection](https://www.getpostman.com/collections/c0a5139f97737444948f)
> [Postman Documentation](https://documenter.getpostman.com/view/1905307/TW6xp8cY)

## Tests and continuous delivery 
- All automated unit and integration tests.
- Just call `$ pytest test.py` on your pipeline.

