# Postgres Priviliges Docker Image

## Parameters

To run the script, one parameter is required which defines the location of the `user-list` file.

## Requried env vars

Script uses `psycopg` python library, which uses all variables from [psql](https://www.postgresql.org/docs/9.3/libpq-envars.html).
Ex:

- `PGHOST` - hostname of postgres instance
- `PGUSER` - username for postgres
- `PGPASSWORD` - password for user in posrgres

Other variables:

- `VALUT_HOST` - defines address of Hashicorp Vault instance
- `CI_JOB_JWT` - JWT token from gitlab-ci to authenticate to Hashicorp Vault [more info](https://docs.gitlab.com/ee/ci/secrets/index.html)
- `CI_VAULT_ROLE` - Vault role which script should use
- `VAULT_MOUNTPOINT` - Vault moint point where passwords should be saved

## Parameters in user-list

- `reset-password` - force changing password
- `valid` - create user with `VALID UNTL`. Also after this time script will remove this user
- `grant` - define databases which user should be granted
  - `schemas` - defines shemas which user should be granted. By default `[public]`
  - `mode` - defines `ro` (read only) or `rw` (read write) access. Also you can define access using [postgres names](https://www.postgresql.org/docs/9.0/sql-grant.html)
- `revoke` - define databases which user should be revoked

## Example `user-list.yaml`

```yaml
testUser:
  reset-password:
  valid: '2022-02-25'
  grant:
    db1:
      schemas: [public, schema1, schema2]
      mode: rw
  revoke:
    db2:
```
