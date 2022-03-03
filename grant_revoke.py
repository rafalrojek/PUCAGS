#!/usr/bin/env python

import datetime
import os
import yaml
import sys
import psycopg
import string
import random
import hvac
from psycopg import sql

characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")

def generate_random_password():
	length = 8
	random.shuffle(characters)
	password = []
	for i in range(length): password.append(random.choice(characters))
	random.shuffle(password)
	return "".join(password)

def check_user_valid (valid_str):
    if valid_str == 'infinity': return True
    valid_sub_str=valid_str.split("-")
    valid_date=datetime.datetime(int(valid_sub_str[0]),int(valid_sub_str[1]),int(valid_sub_str[2]))
    return valid_date > datetime.datetime.now()

def save_password_in_vault (username,password):
    print("Save "+username+" password to vault")
    client = hvac.Client(url=os.environ.get('VAULT_HOST'))

    response = client.auth.jwt.jwt_login(
        jwt=os.environ['CI_JOB_JWT'],
        role=os.environ.get('CI_VAULT_ROLE')
    )
    client.token = response['auth']['client_token']
    if client.is_authenticated():
        client.secrets.kv.v2.create_or_update_secret(
            path=username+"/"+os.environ.get('PGHOST'),
            secret=dict(postgres_password=password),
            mount_point=os.environ.get('VAULT_MOUNTPOINT')
        )

def user_not_exists(conn, username):
    print("Checing if user "+username+" exist")
    query = sql.SQL("SELECT 1 FROM pg_roles WHERE rolname='{}'".format(username))
    cur = conn.execute(query)
    return cur.fetchone() is None

def create_user (conn, username):
    print("Create user "+username)
    password = generate_random_password()
    conn.execute(sql.SQL("CREATE ROLE \"{username}\" WITH LOGIN PASSWORD '{password}'".format(
        username=username,
        password=password)))
    save_password_in_vault(username, password)

def user_not_have_password(conn, username):
    print("Checking if "+username+" have valid password")
    query = sql.SQL("SELECT rolpassword FROM pg_authid WHERE rolname='{}'".format(username))
    cur = conn.execute(query)
    (password,)=cur.fetchone()
    return password is None

def restart_password(conn,username):
    print("Reset password for user "+username)
    password = generate_random_password()
    conn.execute(sql.SQL("ALTER USER \"{username}\" WITH PASSWORD '{password}'".format(
        username=username,
        password=password)))
    save_password_in_vault(username, password)

def set_valid_until(conn, username, valid):
    print("Set absolute time after which the "+username+" password is no longer valid")
    conn.execute(sql.SQL("ALTER USER \"{username}\" WITH VALID UNTIL '{valid}'".format(
        username=username,
        valid=valid)))


def grant (db_name, db_values, user):
    if (db_values is not None) and ('mode' in db_values):
        if db_values.get('mode') == 'rw': access='ALL'
        elif db_values.get('mode') == 'ro': access='SELECT'
        else: access=db_values.get('mode')
    else: access='SELECT'

    with psycopg.connect("dbname="+db_name) as conn:
        query=sql.SQL("GRANT CONNECT ON DATABASE \"{db_name}\" TO \"{user}\"".format(
            db_name=db_name,
            user=user))
        conn.execute(query)
        print(query)
        schemas=['public']
        if (db_values is not None) and ("schemas" in db_values): schemas=db_values.get("schemas")
        for schema in schemas:
            query=sql.SQL("GRANT {access} ON ALL TABLES IN SCHEMA \"{schema}\" TO \"{user}\"".format(
                access=access,
                schema=schema,
                user=user))
            conn.execute(query)
            print(query)
        conn.commit()

def revoke (db_name, db_values, user):
    with psycopg.connect("dbname="+db_name) as conn:
        query=sql.SQL("REVOKE CONNECT ON DATABASE \"{db_name}\" FROM \"{user}\"".format(
                    db_name=db_name,
                    user=user))
        conn.execute(query)
        print(query)
        schemas=['public']
        if (db_values is not None) and ("schemas" in db_values): schemas=db_values.get("schemas")
        for schema in schemas:
            query=sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA \"{schema}\" FROM \"{user}\"".format(
                schema=schema,
                user=user))
            conn.execute(query)
            print(query)
        conn.commit()

def delete_user (username):
    with psycopg.connect("dbname=postgres") as conn:
        if (user_not_exists(conn,user_key)):
            print("Delete user "+username)
            conn.execute(sql.SQL("DROP OWNED BY \"{}\"".format(username)))
            conn.execute(sql.SQL("DROP ROLE IF EXISTS \"{}\"".format(username)))
        conn.commit()

input_file=sys.argv[1]
with open(input_file, "r") as stream:
    for user_key, user_value in yaml.safe_load(stream).items():
        if (user_value is not None) and ("valid" in user_value) and check_user_valid(user_value.get("valid")):
            with psycopg.connect("dbname=postgres") as conn:
                if (user_not_exists(conn,user_key)): create_user(conn,user_key)
                if (user_not_have_password(conn,user_key) or (user_value is not None) and ("restart-password" in user_value)):
                    restart_password(conn,user_key)
                if ((user_value is not None) and ("valid" in user_value)):
                    set_valid_until(conn, user_key, user_value.get("valid"))
                conn.commit()

            if ((user_value is not None) and ("grant" in user_value)):
                for db_key,db_value in user_value.get("grant").items(): grant(db_key, db_value, user_key)
            if ((user_value is not None) and ("revoke" in user_value)):
                for db_key,db_value in user_value.get("revoke").items(): revoke(db_key, db_value, user_key)
        else: delete_user(user_key)
